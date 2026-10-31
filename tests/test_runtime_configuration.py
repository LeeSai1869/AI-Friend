from section_8_tools.terminal.python_tests import runtime_image


def test_installed_and_dev_can_read_same_pinned_runtime(tmp_path,monkeypatch):
    monkeypatch.setattr('pathlib.Path.home',lambda:tmp_path)
    monkeypatch.delenv('AI_FRIEND_TEST_IMAGE',raising=False)
    assert runtime_image()==''
    config=tmp_path/'Library/Application Support/AI Friend V1/runtime/test-image-id'
    config.parent.mkdir(parents=True)
    image='sha256:'+'a'*64
    config.write_text(image+'\n')
    assert runtime_image()==image
    monkeypatch.setenv('AI_FRIEND_TEST_IMAGE','sha256:'+'b'*64)
    assert runtime_image()=='sha256:'+'b'*64
    monkeypatch.setenv('AI_FRIEND_TEST_IMAGE','')
    assert runtime_image()==''  # explicit environment override still takes precedence


def test_setup_saves_image_only_after_docker_is_ready(tmp_path):
    import os,shutil,subprocess,sys
    from pathlib import Path
    repo=tmp_path/'repo';(repo/'scripts').mkdir(parents=True)
    (repo/'.venv/bin').mkdir(parents=True)
    (repo/'.venv/bin/python').symlink_to(sys.executable)
    original=Path(__file__).resolve().parents[1]/'scripts/setup_coding_runtime.sh'
    shutil.copyfile(original,repo/'scripts/setup_coding_runtime.sh')
    image='sha256:'+'c'*64
    (repo/'scripts/build_test_image.py').write_text(f'print({image!r})\n')
    tools=tmp_path/'bin';tools.mkdir()
    docker=tools/'docker'
    docker.write_text('#!'+sys.executable+'\nimport os,sys\n'
        'if sys.argv[1]=="info" and os.environ.get("DOCKER_NOT_READY"):sys.exit(1)\n'
        f'print({image!r} if sys.argv[1]=="image" else "runtime ready")\n')
    docker.chmod(0o700)
    home=tmp_path/'home';home.mkdir()
    env={**os.environ,'HOME':str(home),'PATH':str(tools)+os.pathsep+os.environ['PATH'],'DOCKER_NOT_READY':'1'}
    command=['bash',str(repo/'scripts/setup_coding_runtime.sh')]
    config=home/'Library/Application Support/AI Friend V1/runtime/test-image-id'
    failed=subprocess.run(command,env=env,capture_output=True)
    assert failed.returncode!=0 and not config.exists()
    env.pop('DOCKER_NOT_READY')
    ready=subprocess.run(command,env=env,capture_output=True)
    assert ready.returncode==0,ready.stderr.decode()
    assert config.read_text().strip()==image
