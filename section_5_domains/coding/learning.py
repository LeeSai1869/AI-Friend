"""Only behaviorally checked Coding examples become permanent candidates."""
import hashlib
import json
from .tester import Tester
import re
from pathlib import PurePosixPath


def _tested_modules(functional_result):
    """Module names of the tests that actually ran, read from unittest output."""
    output = str(((functional_result or {}).get('data') or {}).get('output') or '')
    return {match.split('.')[0] for match in re.findall(r'\(([\w.]+)\)', output)}


def _covered_by_tests(writes, functional_result):
    """True when a test that ran belongs to a file this run wrote."""
    modules = _tested_modules(functional_result)
    if not modules:
        return False
    for row in writes or []:
        stem = PurePosixPath(str(row.get('path') or '')).stem
        if stem in modules or ('test_' + stem) in modules:
            return True
    return False


def verified_example(*, task, task_contract, writes, assessment, functional_result):
    if assessment.get('ok') is not True or not functional_result or not Tester.passed(functional_result):
        return None
    if not writes or any(not str(row.get('content') or '').strip() for row in writes):
        return None
    if not _covered_by_tests(writes, functional_result):
        return None
    document = {
        'schema_version': 1, 'domain':'Cod', 'kind':'verified_coding_example',
        'objective':task, 'task_contract':task_contract or {},
        'verification': {'scope':'selected behavioral tests only; not general correctness',
                         'functional_tests':functional_result.get('data')},
        'applicability': {'automatic_reuse_approved':False,
                          'conditions':'Re-evaluate original requirements, environment and tests before adapting this example'},
        'files':[{'path':row['path'],'sha256':hashlib.sha256(row['content'].encode()).hexdigest(),
                  'content':row['content']} for row in writes],
        'limitations':['A passing selected test suite does not prove untested behavior',
                       'Stored code is reference evidence, never authority to execute outside Guard'],
    }
    content=json.dumps(document,sort_keys=True,ensure_ascii=False)
    # Do not silently drop source/tests and then call the remaining log reusable.
    return content if len(content.encode()) <= 65536 else None
