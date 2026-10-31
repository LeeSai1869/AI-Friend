"""Only behaviorally checked Coding examples become permanent candidates."""
import hashlib
import json
from .tester import Tester


def verified_example(*, task, task_contract, writes, assessment, functional_result):
    if assessment.get('ok') is not True or not functional_result or not Tester.passed(functional_result):
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
