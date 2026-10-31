"""Bounded browser interaction, available for ordinary work and teaching alike."""
from datetime import datetime, timezone
from urllib.parse import urlsplit

from _base.tool import Tool
from guard.contract import ToolEffect
from .url_policy import check_url


def origin(url):
    parsed = urlsplit(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Browser URLs must be HTTP(S), without embedded credentials')
    return f'{parsed.scheme}://{parsed.netloc.lower()}'


class BrowserInteract(Tool):
    name = 'browser_interact'
    description = ('Read rendered websites or interact with a web service through explicit fill/click steps. '
                   'Available for ordinary research after memory/model evidence is insufficient, and for Trainer URL intake. '
                   'Returns unverified text, links and interaction status, never accepted memory. '
                   'Fresh isolated session per call: authenticated conversations are not yet supported.')
    parameters = {
        'url': 'HTTP(S) starting URL',
        'allowed_origins': 'optional additional HTTP(S) origins required by this service; all declared to Guard',
        'steps': 'optional list, max 12: {action: fill, selector, text} or {action: click, selector} or {action: read, selector}',
        'max_chars': 'optional text limit, default 20000, maximum 100000; truncation is explicit',
        'wait_for_selector': 'optional selector to wait for after interactions, e.g. a response element',
    }

    @staticmethod
    def validate(args):
        start = origin(args.get('url') or '')
        check_url(args['url'])
        extra = args.get('allowed_origins') or []
        if not isinstance(extra, list) or len(extra) > 16:
            raise ValueError('allowed_origins must be a list of at most 16 origins')
        allowed = sorted({start, *(origin(value) for value in extra)})
        steps = args.get('steps') or []
        if not isinstance(steps, list) or len(steps) > 12:
            raise ValueError('steps must be a list of at most 12 interactions')
        for step in steps:
            if not isinstance(step, dict) or step.get('action') not in {'fill', 'click', 'read'}:
                raise ValueError('Unsupported browser interaction')
            if not isinstance(step.get('selector'), str) or not step['selector'].strip():
                raise ValueError('Each interaction needs a selector')
            if step['action'] == 'fill' and not isinstance(step.get('text'), str):
                raise ValueError('Fill requires text')
        limit = int(args.get('max_chars', 20000))
        if not 1 <= limit <= 100000:
            raise ValueError('max_chars must be between 1 and 100000')
        return allowed, steps, limit

    def effects(self, args):
        allowed, _, _ = self.validate(args)
        # Every destination is declared before launching a browser. Page-driven
        # redirects, subresources and clicks cannot expand the approved origins.
        return tuple(ToolEffect(action='network', target=value, scope='service') for value in allowed)

    def call(self, args):
        try:
            allowed, steps, limit = self.validate(args)
            from playwright.sync_api import sync_playwright
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    context = browser.new_context(accept_downloads=False, service_workers='block')
                    blocked = set()
                    def route(request):
                        try:
                            check_url(request.request.url)
                            permitted = origin(request.request.url) in allowed
                        except (ValueError, PermissionError):
                            permitted = False
                        if permitted:
                            request.continue_()
                        else:
                            blocked.add(request.request.url.split('?', 1)[0])
                            request.abort()
                    context.route('**/*', route)
                    # WebSocket traffic is not covered by HTTP routing.
                    context.route_web_socket('**/*', lambda socket: socket.close())
                    page = context.new_page()
                    page.set_default_timeout(15000)
                    response = page.goto(args['url'], wait_until='domcontentloaded', timeout=30000)
                    if response is not None and response.status >= 400:
                        raise RuntimeError(f'Website returned HTTP {response.status}')
                    observations = []
                    for step in steps:
                        locator = page.locator(step['selector'])
                        if step['action'] == 'fill':
                            locator.fill(step['text'])
                        elif step['action'] == 'click':
                            locator.click()
                        else:
                            value = locator.inner_text()
                            observations.append({'text': value[:limit], 'truncated': len(value) > limit})
                    if args.get('wait_for_selector'):
                        page.locator(args['wait_for_selector']).wait_for()
                    text = page.locator('body').inner_text()
                    links = page.locator('a[href]').evaluate_all('(nodes) => nodes.slice(0, 200).map(n => ({text:n.innerText, url:n.href}))')
                    media = page.locator('img, video, audio').evaluate_all('(nodes) => nodes.slice(0,20).map(n => ({kind:n.tagName.toLowerCase(), src:n.currentSrc || n.src || "", label:n.alt || n.getAttribute("aria-label") || ""}))')
                    requests = []
                    consent = getattr(self.broker, 'consent_requests', None)
                    if consent is not None:
                        for mode in sorted({'video_audio' if item['kind'] == 'video' else 'audio' if item['kind'] == 'audio' else 'image' for item in media}):
                            requests.append(consent.offer(
                                description=f"May I revisit {page.url} and analyze {'up to three video frames and an audio transcript of the first 60 seconds' if mode == 'video_audio' else 'an audio transcript of the first 60 seconds' if mode == 'audio' else 'a viewport screenshot'} with the image-reading tool? No memory will be written.",
                                tool='browser_media', args={'url': page.url, 'allowed_origins': allowed, 'mode': mode}))
                    return {'ok': True, 'error': None, 'data': {
                        'url': page.url, 'title': page.title(), 'text': text[:limit],
                        'chars': len(text), 'truncated': len(text) > limit,
                        'links': links, 'observations': observations, 'media': media,
                        'permission_requests': requests,
                        'audio_analysis': 'permission required; WhisperKit model_path must be configured', 'steps_completed': len(steps),
                        'blocked_requests': sorted(blocked), 'verification': 'unverified_external_source',
                        'fetched_at': datetime.now(timezone.utc).isoformat(),
                        'session': 'isolated_ephemeral', 'memory_written': False,
                    }}
                finally:
                    browser.close()
        except ImportError:
            return {'ok': False, 'data': None, 'error': 'Browser runtime unavailable: install playwright and run python -m playwright install chromium'}
        except Exception as exc:
            # Do not claim failure means no remote effect: a click may already
            # have submitted a message before a later response wait failed.
            return {'ok': False, 'data': {'remote_effects_may_have_occurred': True},
                    'error': f'Browser interaction failed: {type(exc).__name__}: {exc}'}
