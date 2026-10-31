from pathlib import Path
import os
import shutil
import subprocess
import sys


def test_dev_launcher_blocks_existing_backend_and_uses_app_directory(tmp_path):
    root=tmp_path/'project with spaces'
    (root/'scripts').mkdir(parents=True)
    (root/'section_0_app/src').mkdir(parents=True)
    (root/'section_1_central_mind').mkdir()
    for path in ['section_0_app/package.json','section_0_app/src/window-chat.html','section_1_central_mind/main.py']:
        (root/path).touch()
    shutil.copyfile(Path(__file__).resolve().parents[1]/'scripts/start_dev.sh',root/'scripts/start_dev.sh')
    tools=tmp_path/'bin';tools.mkdir()
    for name,body in [('lsof','import os,sys\nsys.exit(0 if os.environ.get("TEST_BUSY") else 1)'),
                      ('npm','import os\nfrom pathlib import Path\nPath(os.environ["TEST_CWD"]).write_text(os.getcwd())')]:
        path=tools/name;path.write_text('#!'+sys.executable+'\n'+body+'\n');path.chmod(0o700)
    output=tmp_path/'cwd'
    env={**os.environ,'PATH':str(tools)+os.pathsep+os.environ['PATH'],'TEST_BUSY':'1','TEST_CWD':str(output)}
    command=['bash',str(root/'scripts/start_dev.sh')]
    busy=subprocess.run(command,cwd=tmp_path,env=env,capture_output=True,text=True)
    assert busy.returncode!=0 and not output.exists()
    assert 'already owns port 8765' in busy.stderr
    env.pop('TEST_BUSY')
    launched=subprocess.run(command,cwd=tmp_path,env=env,capture_output=True,text=True)
    assert launched.returncode==0,launched.stderr
    assert Path(output.read_text())==root/'section_0_app'
