"""Versioned task intent and execution receipts. These confer no authority."""
from __future__ import annotations

from copy import deepcopy
import uuid
import time


def task_contract(plan):
    task_id = getattr(plan, 'task_id', '') or uuid.uuid4().hex
    plan.task_id = task_id
    original = getattr(plan, 'original_objective', '') or plan.objective
    plan.original_objective = original
    requirements = getattr(plan, 'requirements', []) or []
    constraints = getattr(plan, 'constraints', []) or []
    if not isinstance(requirements, list) or not isinstance(constraints, list):
        raise ValueError('requirements and constraints must be lists')
    if any(not isinstance(item, str) or not item.strip() for item in requirements + constraints):
        raise ValueError('requirements and constraints must contain nonempty strings')
    requirements = list(dict.fromkeys(requirements))
    constraints = list(dict.fromkeys(constraints))
    checks = deepcopy(getattr(plan, 'acceptance_checks', []) or [])
    if not isinstance(checks, list) or any(not isinstance(item, dict) for item in checks):
        raise ValueError('acceptance_checks must be a list of objects')
    known_ids = {f'R{i + 1}' for i in range(len(requirements))}
    for check in checks:
        refs = check.get('requirement_ids', [])
        if not isinstance(refs, list) or any(ref not in known_ids for ref in refs):
            raise ValueError('acceptance checks must reference existing requirement identities')
    contract = {'schema_version': 1, 'task_id': task_id, 'original_objective': original,
            'requirements': [{'id': f'R{i + 1}', 'description': item} for i, item in enumerate(requirements)],
            'constraints': constraints, 'acceptance_checks': checks}
    validate_task_contract(contract)
    return contract


def validate_task_contract(contract):
    if not isinstance(contract, dict) or contract.get('schema_version') != 1:
        raise ValueError('unsupported task contract version')
    for field in ('task_id', 'original_objective'):
        if not isinstance(contract.get(field), str) or not contract[field].strip():
            raise ValueError(f'task contract requires {field}')
    requirements = contract.get('requirements')
    if not isinstance(requirements, list):
        raise ValueError('task requirements must be a list')
    identities = set()
    for item in requirements:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id'] or item['id'] in identities:
            raise ValueError('task requirements require unique identities')
        if not isinstance(item.get('description'), str) or not item['description'].strip():
            raise ValueError('task requirements require descriptions')
        identities.add(item['id'])
    if not isinstance(contract.get('constraints'), list) or any(not isinstance(item, str) for item in contract['constraints']):
        raise ValueError('task constraints must be strings')
    checks = contract.get('acceptance_checks')
    if not isinstance(checks, list) or any(not isinstance(item, dict) for item in checks):
        raise ValueError('task acceptance checks must be objects')
    for check in checks:
        refs = check.get('requirement_ids', [])
        if not isinstance(refs, list) or any(not isinstance(ref, str) or ref not in identities for ref in refs):
            raise ValueError('acceptance references an unknown requirement')


def execution_receipt(response, verified, *, component, capability):
    """Keep domain evidence separate from its generated explanation."""
    applied = [deepcopy(item) for item in response.get('applied', []) if isinstance(item, dict)]
    artifacts = [item['path'] for item in applied if item.get('ok') is True and isinstance(item.get('path'), str)]
    if not applied and verified.get('ok') is True:
        artifacts = [path for path in response.get('artifacts', []) if isinstance(path, str)]
    functional = deepcopy(response.get('functional_tests'))
    return {'component': component, 'capability': capability, 'recorded_at': time.time(),
            'status': response.get('status', 'unknown'), 'operation': response.get('operation'),
            'artifacts': artifacts, 'applied': applied,
            'verification': deepcopy(response.get('verification') or verified),
            'functional_tests': functional,
            'acceptance': deepcopy(response.get('acceptance') or {}),
            'functional_unavailable': response.get('functional_unavailable')}


def attach_outcome(result, plan, step_results, *, communication):
    receipts = [deepcopy(receipt) for item in (step_results or {}).values()
                for receipt in item.get('execution_receipts', [])]
    artifacts = list(dict.fromkeys(path for item in receipts for path in item.get('artifacts', [])))
    failed = any(item.get('status') == 'error' and (not item.get('applied') or any(write.get('ok') is not True for write in item['applied'])) for item in receipts)
    execution = 'partial' if failed and artifacts else ('failed' if failed else ('completed' if receipts else 'not_started'))
    functional = [item['functional_tests'] for item in receipts if item.get('functional_tests')]
    verification = 'not_performed'
    if any((item.get('verification') or {}).get('ok') is False for item in receipts):
        verification = 'failed'
    elif functional:
        verification = 'passed' if all(item.get('ok') is True for item in functional) else 'failed'
    elif receipts:
        verification = 'insufficient'
    result = dict(result)
    result['artifacts'] = list(dict.fromkeys([*result.get('artifacts', []), *artifacts]))
    result['task_id'] = getattr(plan, 'task_id', '')
    result['outcome'] = {'schema_version': 1, 'task_id': result['task_id'],
                         'original_objective': getattr(plan, 'original_objective', '') or plan.objective,
                         'execution': {'status': execution, 'artifacts': artifacts},
                         'verification': {'status': verification, 'scope': 'selected_tests' if functional else ('domain_checks' if receipts else 'none')},
                         'communication': {'status': communication}, 'receipts': receipts,
                         'requirement_ids': [item['id'] for item in task_contract(plan)['requirements']],
                         'acceptance_check_ids': [item.get('id') for item in getattr(plan, 'acceptance_checks', [])]}
    checks = getattr(plan, 'acceptance_checks', []) or []
    passed_ids = {identity for item in receipts if (item.get('functional_tests') or {}).get('ok') is True
                  and (item.get('acceptance') or {}).get('status') == 'passed'
                  for identity in item['acceptance'].get('check_ids', [])}
    result['outcome']['requirements'] = [
        {**requirement, 'status': 'checks_passed' if any(check.get('id') in passed_ids and requirement['id'] in check.get('requirement_ids', []) for check in checks) else 'unverified'}
        for requirement in task_contract(plan)['requirements']]
    if result.get('status') != 'ok' and artifacts:
        result['output'] = deterministic_report(receipts, execution=execution, communication=communication)
    return result


def deterministic_report(receipts, *, execution='completed', communication='failed'):
    header = ('File operations completed, but the explanation could not be approved.'
              if execution == 'completed' and communication == 'failed' else
              'Some work was completed. The request did not complete successfully.')
    lines = [header]
    for receipt in receipts:
        for path in receipt.get('artifacts', []):
            lines.append('File written: ' + path)
        checks = (receipt.get('verification') or {}).get('checks') or {}
        if checks.get('python_syntax'):
            lines.append('Python syntax: ' + str(checks['python_syntax']))
        tests = receipt.get('functional_tests')
        if tests:
            data = tests.get('data') or {}
            lines.append(f"Functional tests: {data.get('tests_run', 0)} run, {data.get('passed', 0)} passed.")
        elif receipt.get('artifacts'):
            lines.append('Functional behavior has not been verified.')
    lines.append('Retrying the explanation does not repeat file operations.')
    return '\n'.join(lines)
