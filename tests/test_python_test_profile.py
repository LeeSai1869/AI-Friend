"""Test runner semantics separately from the optional native container runtime."""
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from section_8_tools.terminal.python_tests import RunPythonTests, _RUNNER
from section_1_central_mind.mind.inventory import Inventory
from section_1_central_mind.mind.broker import ToolBroker
from section_1_central_mind.guard.layer import GuardLayer
from section_1_central_mind.guard.contract import GuardPrincipal
from section_1_central_mind.guard.production_policy import build_production_guard_policy, build_production_effect_policy

ROOT=Path(__file__).resolve().parents[1]


def run_protocol(tmp_path, test_code):
    # Trusted fixture tests only. This validates runner reporting, not isolation.
    runner=_RUNNER.replace("pathlib.Path('/work')",f'pathlib.Path({str(tmp_path)!r})')
    packet={'files':{'answer.py':'def answer():\n    return 42\n','test_answer.py':test_code},'tests':['test_answer.py']}
    proc=subprocess.run([sys.executable,'-I','-c',runner],input=json.dumps(packet),capture_output=True,text=True,timeout=10,cwd=tmp_path)
    report=json.loads(proc.stdout.rsplit('\nAI_FRIEND_TEST_RESULT=',1)[1])
    return proc,report


@pytest.mark.parametrize('assertion,success', [('self.assertEqual(answer(),42)',True),('self.assertEqual(answer(),41)',False)])
def test_runner_reports_behavioral_assertions(tmp_path,assertion,success):
    proc,data=run_protocol(tmp_path,'import unittest\nfrom answer import answer\nclass Tests(unittest.TestCase):\n    def test_answer(self):\n        '+assertion+'\n')
    assert (proc.returncode==0)==success
    assert data['tests_run']==1 and data['passed']==int(success)
    assert data['failures']==int(not success)


@pytest.mark.parametrize('code',[
    'import unittest\n',
    'import unittest\n@unittest.skip("not available")\nclass Tests(unittest.TestCase):\n    def test_skip(self):\n        pass\n',
    'import unittest\nclass Tests(unittest.TestCase):\n    @unittest.expectedFailure\n    def test_expected(self):\n        self.fail("expected")\n',
])
def test_zero_skipped_or_expected_failure_only_is_not_success(tmp_path,code):
    proc,data=run_protocol(tmp_path,code)
    assert proc.returncode!=0 and data['passed']==0


def test_container_command_has_no_host_mounts_or_network(tmp_path,monkeypatch):
    (tmp_path/'test_answer.py').write_text('import unittest')
    commands=[]
    def run(command,**kwargs):
        commands.append(command)
        if command[1]=='logs':
            kwargs['stdout'].write(('\nAI_FRIEND_TEST_RESULT='+json.dumps({'tests_run':1,'passed':1,'failures':0,'errors':0,'skipped':0,'expected_failures':0,'unexpected_successes':0})).encode())
            kwargs['stdout'].flush()
        return SimpleNamespace(returncode=0, stdout=b"0\n", stderr=b"")
    monkeypatch.setenv('AI_FRIEND_TEST_IMAGE','python@sha256:'+'a'*64)
    monkeypatch.setattr('section_8_tools.terminal.python_tests.shutil.which',lambda name:'/usr/bin/docker')
    monkeypatch.setattr('section_8_tools.terminal.python_tests.subprocess.run',run)
    result=RunPythonTests(tmp_path,None).call({'sources':['test_answer.py'],'paths':['test_answer.py']})
    assert result['ok']
    command=commands[0]
    assert '--network=none' in command and '--cap-drop=ALL' in command
    assert '--security-opt=no-new-privileges' in command and '--pull=never' in command
    assert '--volume' not in command and '--mount' not in command and '-v' not in command
    assert '--user=65534:65534' in command
    assert commands[-1][1:3]==['rm','--force'] and commands[-1][-1].startswith('ai-friend-test-')


def test_snapshot_escape_rejected_before_any_execution(tmp_path):
    tool=RunPythonTests(tmp_path,None)
    with pytest.raises(ValueError):
        tool.effects({'sources':['../secret.py'],'paths':['../secret.py']})


def test_user_cannot_execute_functional_profile(tmp_path,monkeypatch):
    (tmp_path/'test_answer.py').write_text('import unittest')
    inventory=Inventory(ROOT).discover()
    guard=GuardLayer(ROOT,policy=build_production_guard_policy(),effect_policy=build_production_effect_policy())
    principal=GuardPrincipal(principal_id='test.user',kind='human',role='user',authenticated=True,source='auth_service')
    broker=ToolBroker(ROOT,ROOT/'section_8_tools',inventory=inventory,guard=guard,principal=principal)
    def forbidden(*args,**kwargs):
        raise AssertionError('Docker must not be invoked for unauthorized users')
    monkeypatch.setattr('subprocess.run',forbidden)
    result=broker.bind_component(inventory.get('coder')).with_workspace(tmp_path).call('run_python_tests',{
        'sources':['test_answer.py'],'paths':['test_answer.py']})
    assert not result['ok'] and 'guard denied' in result['error']


def test_actual_container_behavior_when_enabled(tmp_path):
    if os.environ.get('AI_FRIEND_RUN_CONTAINER_TESTS')!='1':
        pytest.skip('set AI_FRIEND_RUN_CONTAINER_TESTS=1 and a digest-pinned AI_FRIEND_TEST_IMAGE to validate Docker runtime')
    (tmp_path/'answer.py').write_text('def answer():\n    return 42\n')
    (tmp_path/'test_answer.py').write_text('import unittest\nfrom answer import answer\nclass Tests(unittest.TestCase):\n    def test_answer(self):\n        self.assertEqual(answer(),42)\n')
    result=RunPythonTests(tmp_path,None).call({'sources':['answer.py','test_answer.py'],'paths':['test_answer.py']})
    assert result['ok'], result
    assert result['data']['tests_run']==1 and result['data']['passed']==1


def test_pytest_functions_execute_and_assert(tmp_path):
    proc,data=run_protocol(tmp_path,'from answer import answer\ndef test_answer():\n    assert answer() == 42\n')
    assert proc.returncode==0 and data['framework']=='pytest'
    assert data['tests_run']==1 and data['passed']==1


def test_pytest_assertion_failure_is_not_success(tmp_path):
    proc,data=run_protocol(tmp_path,'from answer import answer\ndef test_answer():\n    assert answer() == 41\n')
    assert proc.returncode!=0 and data['failures']==1
