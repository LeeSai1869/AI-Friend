import json
from pathlib import Path
from types import SimpleNamespace
from section_8_tools.audio.audio import AudioTranscribe


def test_whisperkit_uses_explicit_model_and_timestamped_report(tmp_path,monkeypatch):
    tool=AudioTranscribe(tmp_path,None)
    model=tmp_path/'model';model.mkdir()
    monkeypatch.setattr(tool,'configuration',lambda:(Path('/test/whisperkit-cli'),model))
    source=tmp_path/'sample.mp4';source.write_bytes(b'fixture')
    monkeypatch.setattr('shutil.which',lambda name:'/test/ffmpeg')
    commands=[]
    def run(command,**kwargs):
        commands.append(command)
        if command[0].endswith('whisperkit-cli'):
            assert '--model-path' in command and '--model' not in command
            assert '--word-timestamps' in command
            reports=Path(command[command.index('--report-path')+1])
            (reports/'report.json').write_text(json.dumps({'segments':[{'start':0,'end':1.2,'text':'Hello'}]}))
        return SimpleNamespace(returncode=0,stdout=b'RIFF-fixture')
    monkeypatch.setattr('subprocess.run',run)
    result=tool.call({'path':'sample.mp4'})
    assert result['ok'],result
    assert result['data']['segments']==[{'start':0,'end':1.2,'text':'Hello'}]
    assert result['data']['duration_limit_seconds']==60 and result['data']['memory_written'] is False
    assert commands[0][commands[0].index('-t')+1]=='60'
    assert commands[0][commands[0].index('-protocol_whitelist')+1]=='pipe'


def test_silence_or_unrecognized_report_is_not_fabricated(tmp_path):
    assert AudioTranscribe.parse_reports(tmp_path)==[]


def test_video_frames_and_audio_share_one_approved_source(tmp_path,monkeypatch):
    import os,sys,threading,subprocess,shutil
    from functools import partial
    from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
    import pytest
    if os.environ.get('AI_FRIEND_RUN_BROWSER_TESTS')!='1':pytest.skip('Enable real browser/media integration')
    from playwright.sync_api import BrowserType
    from section_1_central_mind.mind.consent import ConsentRequests
    from section_8_tools.web.media import BrowserMedia
    launch=BrowserType.launch
    monkeypatch.setattr(BrowserType,'launch',lambda self,**kwargs:launch(self,executable_path='/usr/bin/chromium',**kwargs))
    subprocess.run([shutil.which('ffmpeg'),'-nostdin','-v','error','-f','lavfi','-i','color=c=blue:s=96x64:r=2',
        '-f','lavfi','-i','sine=frequency=440:sample_rate=16000','-t','12','-c:v','libvpx-vp9','-c:a','libopus',str(tmp_path/'clip.webm')],check=True,timeout=30)
    (tmp_path/'index.html').write_text('<html><body><video preload="auto" controls src="clip.webm"></video></body></html>')
    model=tmp_path/'model';model.mkdir()
    cli=tmp_path/'whisperkit-fixture'
    cli.write_text('#!'+sys.executable+'\nimport sys,json\nfrom pathlib import Path\np=Path(sys.argv[sys.argv.index("--report-path")+1])\n(p/"report.json").write_text(json.dumps({"segments":[{"start":0,"end":1,"text":"Fixture transcript"}]}))\n')
    cli.chmod(0o700)
    monkeypatch.setattr(AudioTranscribe,'configuration',lambda self:(cli,model))
    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/clip.webm':
                data=(tmp_path/'clip.webm').read_bytes()
                start,end=0,len(data)-1
                if self.headers.get('Range'):
                    import re
                    match=re.fullmatch(r'bytes=(\d+)-(\d*)',self.headers['Range'])
                    if match:
                        start=int(match[1]);end=int(match[2]) if match[2] else end
                    self.send_response(206)
                    self.send_header('Content-Range',f'bytes {start}-{end}/{len(data)}')
                else:
                    self.send_response(200)
                self.send_header('Content-Type','video/webm')
                self.send_header('Accept-Ranges','bytes')
                self.send_header('Content-Length',str(end-start+1))
                self.end_headers();self.wfile.write(data[start:end+1])
                return
            super().do_GET()
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(tmp_path)))
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    try:
        store=ConsentRequests();url=f'http://127.0.0.1:{server.server_port}/index.html'
        row=store.offer(description='Video and audio?',tool='browser_media',args={'url':url,
            'allowed_origins':[f'http://127.0.0.1:{server.server_port}'],'mode':'video_audio'})
        store.decide(row['request_id'],True)
        calls=[]
        def delegate(name,args):
            calls.append(name)
            if name=='audio_transcribe':return AudioTranscribe(tmp_path,None).call(args)
            return {'ok':True,'data':{'text':'Blue video frame'}}
        broker=SimpleNamespace(consent_requests=store,inventory=SimpleNamespace(get=lambda name:object()),
            bind_component=lambda info:SimpleNamespace(call=delegate))
        result=BrowserMedia(tmp_path,broker).call({'request_id':row['request_id']})
        assert result['ok'],result
        data=result['data']
        assert data['complete'] and data['audio']['ok'],data
        assert data['audio']['data']['segments'][0]['text']=='Fixture transcript'
        assert [frame['timestamp_seconds'] for frame in data['frames']]==[0,5,10]
        assert calls==['audio_transcribe','document_read','document_read','document_read']
    finally:
        server.shutdown();server.server_close();worker.join()
