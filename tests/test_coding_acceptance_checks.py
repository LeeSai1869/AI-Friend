import json
import subprocess
import sys
from types import SimpleNamespace
from section_5_domains.coding.execution import CodingExecution
from section_5_domains.coding.acceptance import acceptance_module


def checks():
    return [{'id':'duplicates', 'requirement_ids':['R1'], 'kind':'python_call',
             'payload':{'module':'counter', 'function':'count_entries', 'args':[['cat','cat','dog']], 'expected':3}},
            {'id':'signature','kind':'python_signature',
             'payload':{'module':'counter', 'function':'count_entries', 'signature':'(entries: list[str]) -> int'}}]


def test_wrong_word_frequency_tool_fails_immutable_behavior_checks_then_repairs_without_early_writes(tmp_path):
    (tmp_path/'counter.py').write_text('def count_entries(entries: list[str]) -> int:\n    return 0\n')
    candidates = iter(['def count_entries(entries: list[str]) -> int:\n    return len(set(entries))\n',
                       'def count_entries(entries: list[str]) -> int:\n    return len(entries)\n'])
    original = (tmp_path/'counter.py').read_text()
    attempts = []
    def call(operation, args):
        if operation == 'write_file':
            assert attempts == [False, True]
            (tmp_path/args['path']).write_text(args['content'])
            return {'ok':True}
        if operation == 'run_python_compile':
            return {'ok':True,'data':{'returncode':0}}
        # Trusted fixture for runner reporting. Production container is exercised separately.
        snapshot = tmp_path / f'snapshot-{len(attempts)}'
        snapshot.mkdir()
        for path in args['sources']:
            (snapshot/path).write_text(args['overrides'].get(path, (tmp_path/path).read_text() if (tmp_path/path).exists() else ''))
        run = subprocess.run([sys.executable,'-m','unittest','discover','-v'],cwd=snapshot,capture_output=True,text=True)
        passed = run.returncode == 0
        if args['overrides'].get('counter.py'):
            assert (tmp_path/'counter.py').read_text() == original
            attempts.append(passed)
        return {'ok':passed,'data':{'returncode':run.returncode,'tests_run':2,'passed':2 if passed else 1,
                'failures':0 if passed else 1,'errors':0,'output':run.stderr},'error':None if passed else 'assertion failed'}
    caller = SimpleNamespace(route=lambda **kwargs: json.dumps({'writes':[{'path':'counter.py','content':next(candidates)}]}))
    result = CodingExecution().run(caller=caller, broker=SimpleNamespace(call=call), prompt='Count entries, including duplicates',
        allowed_files=['counter.py'], sources=['counter.py'], acceptance_checks=checks())
    assert result['status'] == 'executed' and result['acceptance']['status'] == 'passed'
    assert attempts == [False, True]
    assert not list(tmp_path.glob('test_ai_friend*')), 'acceptance modules must not be written to the host project'


def test_planned_acceptance_checks_block_application_when_runtime_is_unavailable():
    calls = []
    def call(name, args):
        calls.append(name)
        return {'ok':False, 'error':'AI_FRIEND_TEST_IMAGE is not configured', 'data':None}
    caller=SimpleNamespace(route=lambda **kwargs: json.dumps({'writes':[{'path':'counter.py','content':'value=1'}]}))
    result=CodingExecution().run(caller=caller,broker=SimpleNamespace(call=call),prompt='task',
        allowed_files=['counter.py'], sources=['counter.py'], acceptance_checks=checks())
    assert result['status']=='needs_answers' and result['artifacts']==[]
    assert calls == ['run_python_tests']


def test_trace_cli_mismatch_fails_even_when_script_has_valid_syntax(tmp_path):
    # Reconstruct only the confirmed interface defect, not the unseen dictionary data.
    (tmp_path/'build_index.py').write_text('import argparse\np=argparse.ArgumentParser()\np.add_argument("json_file")\np.parse_args()\n')
    name, code = acceptance_module([{'id':'source-option','kind':'python_cli',
        'payload':{'script':'build_index.py','args':['--source','fixtures/sample_dictionary.json'],'expected_exit':0}}])
    (tmp_path/name).write_text(code)
    run = subprocess.run([sys.executable,'-m','unittest',name],cwd=tmp_path,capture_output=True,text=True)
    assert run.returncode != 0
    assert 'unrecognized arguments: --source' in run.stderr
    assert 'source-option' in run.stderr
