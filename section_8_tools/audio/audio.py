"""WhisperKit file transcription configured by the trainer's YAML inventory."""
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile
import yaml
from _base.tool import Tool
from guard.contract import ToolEffect


class AudioTranscribe(Tool):
    name='audio_transcribe'
    description='Transcribe an audio file with timestamps through the locally configured WhisperKit CLI/model. Does not record a microphone or write memory.'
    parameters={'path':'workspace audio file', 'name':'filename for uploaded bytes',
                'data_base64':'optional audio bytes instead of a path', 'language':'optional language code'}

    def configuration(self):
        registry=Path(__file__).resolve().parents[2]/'section_7_models/models_registry.yaml'
        data=yaml.safe_load(registry.read_text())
        config=(data.get('runtime_inventory') or {}).get('whisperkit') or {}
        cli=Path(config.get('cli') or '').expanduser()
        model=Path(config.get('model_path') or '').expanduser()
        if not config.get('model_path') or not model.is_dir():
            raise ValueError('Configure runtime_inventory.whisperkit.model_path in models_registry.yaml to your existing local WhisperKit model directory')
        if not config.get('cli') or not cli.is_file():
            raise ValueError('Configured WhisperKit executable is unavailable')
        return cli,model

    def effects(self,args):
        cli,model=self.configuration()
        effects=[ToolEffect(action='execute',target=str(cli),scope='service'),
                 ToolEffect(action='execute',target='ffmpeg',scope='service'),
                 ToolEffect(action='read',target=str(model.resolve()),scope='exact')]
        if args.get('data_base64') is None:
            effects.append(ToolEffect(action='read',target=str(self._resolve(args.get('path') or ''))))
        return tuple(effects)

    @staticmethod
    def parse_reports(directory):
        segments=[]
        seen=set()
        def visit(value):
            if isinstance(value,list):
                for item in value: visit(item)
            elif isinstance(value,dict):
                if isinstance(value.get('segments'),list):
                    for item in value['segments']:
                        if not isinstance(item,dict) or not isinstance(item.get('text'),str): continue
                        start,end=item.get('start'),item.get('end')
                        if not isinstance(start,(int,float)) or not isinstance(end,(int,float)) or start<0 or end<start:
                            continue
                        key=(start,end,item['text'])
                        if key not in seen:
                            seen.add(key);segments.append({'start':start,'end':end,'text':item['text']})
                else:
                    for child in value.values():
                        if isinstance(child,(dict,list)):visit(child)
        for path in directory.glob('*.json'):
            visit(json.loads(path.read_text()))
        return sorted(segments,key=lambda row:(row['start'],row['end']))

    def call(self,args):
        try:
            cli,model=self.configuration()
            with tempfile.TemporaryDirectory(prefix='ai-friend-audio-') as folder:
                root=Path(folder)
                reports=root/'reports';reports.mkdir()
                if args.get('data_base64') is not None:
                    blob=base64.b64decode(args['data_base64'],validate=True)
                    if len(blob)>32*1024*1024:raise ValueError('Audio exceeds the 32 MiB transcription budget')
                    source=root/('input'+Path(args.get('name') or 'audio.wav').suffix)
                    source.write_bytes(blob)
                else:
                    source=self._resolve(args.get('path') or '')
                    if not source.is_file() or source.stat().st_size>32*1024*1024:
                        raise ValueError('Audio missing or exceeds the 32 MiB transcription budget')
                import shutil
                ffmpeg=shutil.which('ffmpeg')
                if not ffmpeg:raise RuntimeError('ffmpeg is required to extract the audio track')
                wav=root/'speech.wav'
                # Untrusted playlists must not turn ffmpeg into a second URL
                # fetcher or read arbitrary host files outside the approved source.
                extracted=subprocess.run([ffmpeg,'-nostdin','-v','error','-protocol_whitelist','pipe',
                    '-i','pipe:0','-t','60','-vn','-ac','1','-ar','16000','-f','wav','pipe:1'],
                    input=source.read_bytes(),capture_output=True,timeout=90)
                if extracted.returncode!=0:raise RuntimeError('Media has no decodable audio track')
                wav.write_bytes(extracted.stdout)
                source=wav
                command=[str(cli),'transcribe','--audio-path',str(source),'--model-path',str(model),
                         '--word-timestamps','--report','--report-path',str(reports),
                         '--incremental-loading','--concurrent-worker-count','1']
                language=args.get('language')
                if language:
                    if not isinstance(language,str) or not language.isalpha() or len(language)>16:
                        raise ValueError('Invalid language code')
                    command.extend(['--language',language])
                completed=subprocess.run(command,capture_output=True,text=True,timeout=300,
                    env={**os.environ,'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'})
                if completed.returncode!=0:
                    raise RuntimeError(f'WhisperKit exited with status {completed.returncode}; check local model/tokenizer configuration')
                segments=self.parse_reports(reports)
                if not segments:
                    raise RuntimeError('WhisperKit returned no recognized timestamped segments; silence or unsupported report format')
                return {'ok':True,'error':None,'data':{'text':' '.join(row['text'] for row in segments),
                    'segments':segments,'duration_limit_seconds':60,'verification':'unverified_transcript','memory_written':False}}
        except Exception as exc:
            return {'ok':False,'data':None,'error':str(exc)}


TOOLS=[AudioTranscribe]
