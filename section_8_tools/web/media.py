"""Permission-scoped browser screenshots delegated through Broker and Guard."""
import base64
from _base.tool import Tool
from guard.contract import ToolEffect
from .browser import origin
from .url_policy import check_url


class BrowserMedia(Tool):
    name = 'browser_media'
    description = 'Analyze a page screenshot or up to three video frames only after explicit UI approval of a browser-generated permission request. No audio support or memory writes.'
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
                    samples = [None] if record['mode'] == 'image' else [0, 5, 10]
                    for timestamp in samples:
                        check_url(page.url)
                        if timestamp is None:
                            image = page.screenshot(type='png')
                        else:
                            video = page.locator('video').first
                            video.evaluate('(v,t) => { v.pause(); v.currentTime=t; }', timestamp)
                            page.wait_for_function('(t) => { const v=document.querySelector("video"); return v && v.readyState>=2 && !v.seeking && Math.abs(v.currentTime-t)<0.5; }', arg=timestamp, timeout=5000)
                            image = video.screenshot(type='png')
                        result = delegate.call('document_read', {'name':'browser-frame.png', 'data_base64':base64.b64encode(image).decode()})
                        if not result.get('ok'):
                            return {'ok':False, 'error':result.get('error'), 'data':{'frames':frames, 'memory_written':False}}
                        frames.append({'timestamp_seconds':timestamp, 'result':result.get('data')})
                finally:
                    browser.close()
            return {'ok':True, 'error':None, 'data':{'url':record['url'], 'frames':frames,
                'scope':'viewport screenshot' if record['mode']=='image' else 'visual frames at 0, 5, 10 seconds; no audio',
                'verification':'unverified_external_source', 'memory_written':False}}
        except Exception as exc:
            return {'ok':False, 'data':None, 'error':str(exc)}
