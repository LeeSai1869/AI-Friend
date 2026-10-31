"""Permission-scoped browser screenshots delegated through Broker and Guard."""
import base64
from urllib.parse import urljoin
from _base.tool import Tool
from guard.contract import ToolEffect
from .browser import origin
from .url_policy import check_url


class BrowserMedia(Tool):
    name = 'browser_media'
    description = 'Analyze a page screenshot or up to three video frames with optional scoped audio transcription only after explicit UI approval of a browser-generated permission request. Audio requires a configured local WhisperKit model; no memory writes.'
    parameters = {'request_id': 'Single-use permission request approved by the authenticated human'}

    def approved(self, args, consume=False):
        record = self.broker.consent_requests.approved(args.get('request_id'), self.name, consume=consume)
        check_url(record['url'])
        return record

    def effects(self, args):
        record = self.approved(args)
        return tuple(ToolEffect(action='network', target=value, scope='service')
                     for value in record['allowed_origins'])

    def call(self, args):
        try:
            record = self.approved(args, consume=True)
            from playwright.sync_api import sync_playwright
            delegate = self.broker.bind_component(self.broker.inventory.get('web'))
            frames = []
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    context = browser.new_context(accept_downloads=False, service_workers='block')
                    def route(request):
                        try:
                            check_url(request.request.url)
                            if origin(request.request.url) not in record['allowed_origins']:
                                raise PermissionError('Undeclared origin')
                            request.continue_()
                        except (ValueError, PermissionError):
                            request.abort()
                    context.route('**/*', route)
                    context.route_web_socket('**/*', lambda socket: socket.close())
                    page = context.new_page()
                    page.set_default_timeout(15000)
                    response = page.goto(record['url'], wait_until='domcontentloaded', timeout=30000)
                    if response is not None and response.status >= 400:
                        raise RuntimeError(f'Page returned HTTP {response.status}')
                    transcript = None
                    audio_error = None
                    if record['mode'] in {'video_audio', 'audio'}:
                        try:
                            selector='video' if record['mode']=='video_audio' else 'audio'
                            media_url=page.locator(selector).first.evaluate('(v) => v.currentSrc || v.src')
                            blob=self.fetch_media(media_url, record['allowed_origins'])
                            transcript=delegate.call('audio_transcribe',{'name':'browser-media.bin',
                                'data_base64':base64.b64encode(blob).decode()})
                        except Exception as exc:
                            audio_error=str(exc)
                    samples = [None] if record['mode'] == 'image' else [] if record['mode']=='audio' else [0, 5, 10]
                    for timestamp in samples:
                        check_url(page.url)
                        if timestamp is None:
                            image = page.screenshot(type='png')
                        else:
                            video = page.locator('video').first
                            page.wait_for_function('() => { const v=document.querySelector("video"); return v && v.readyState>=2; }', timeout=15000)
                            video.evaluate('(v,t) => { v.pause(); if (Math.abs(v.currentTime-t)>0.01) v.currentTime=t; }', timestamp)
                            try:
                                page.wait_for_function('(t) => { const v=document.querySelector("video"); return v && v.readyState>=2 && !v.seeking && Math.abs(v.currentTime-t)<0.5; }', arg=timestamp, timeout=5000)
                            except Exception as exc:
                                state=video.evaluate('(v) => ({currentTime:v.currentTime,duration:v.duration,readyState:v.readyState,seeking:v.seeking,error:v.error && v.error.code})')
                                frames.append({'timestamp_seconds':timestamp,'error':f'Video frame unavailable: {state}'})
                                continue
                            image = video.screenshot(type='png')
                        result = delegate.call('document_read', {'name':'browser-frame.png', 'data_base64':base64.b64encode(image).decode()})
                        if not result.get('ok'):
                            return {'ok':False, 'error':result.get('error'), 'data':{'frames':frames, 'memory_written':False}}
                        frames.append({'timestamp_seconds':timestamp, 'result':result.get('data')})
                finally:
                    browser.close()
            return {'ok':True, 'error':None, 'data':{'url':record['url'], 'frames':frames,
                'scope':'viewport screenshot' if record['mode']=='image' else 'visual frames at 0/5/10 seconds; audio limited to first 60 seconds',
                'audio':transcript, 'audio_error':audio_error,
                'complete': all('error' not in frame for frame in frames) and not audio_error and (record['mode']=='image' or record['mode']=='video_frames' or bool(transcript and transcript.get('ok'))),
                'verification':'unverified_external_source', 'memory_written':False}}
        except Exception as exc:
            return {'ok':False, 'data':None, 'error':str(exc)}

    @staticmethod
    def fetch_media(url, allowed):
        import requests
        for _ in range(10):
            check_url(url)
            if origin(url) not in allowed:
                raise PermissionError('Media origin was not approved')
            with requests.get(url,stream=True,allow_redirects=False,timeout=20) as response:
                if response.status_code in {301,302,303,307,308}:
                    url=urljoin(url,response.headers.get('Location',''))
                    continue
                response.raise_for_status()
                content=bytearray()
                for chunk in response.iter_content(16384):
                    content.extend(chunk)
                    if len(content)>32*1024*1024:
                        raise ValueError('Browser media exceeds the 32 MiB fetch budget')
                return bytes(content)
        raise ValueError('Too many media redirects')
