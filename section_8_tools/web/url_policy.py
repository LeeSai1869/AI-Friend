"""Administrator-managed deny rules, checked independently of model output."""
import json
import os
from pathlib import Path
import posixpath
from urllib.parse import unquote, urlsplit


def policy_path():
    return Path(os.environ.get('AI_FRIEND_URL_POLICY', str(
        Path.home() / 'Library/Application Support/AI Friend V1/network_policy.json'))).expanduser()


def canonical(url):
    parsed = urlsplit(url if '://' in url else 'https://' + url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Invalid HTTP(S) policy URL')
    host = parsed.hostname.encode('idna').decode().lower().rstrip('.')
    path = parsed.path
    for _ in range(8):
        decoded = unquote(path)
        if decoded == path:
            break
        path = decoded
    path = posixpath.normpath('/' + path.lstrip('/'))
    return host, path


def check_url(url):
    host, path = canonical(url)
    policy = policy_path()
    if not policy.exists():
        return
    try:
        data = json.loads(policy.read_text())
        if data.get('version') != 1 or not isinstance(data.get('blocked'), list):
            raise ValueError('Invalid policy schema')
        for rule in data['blocked']:
            if not isinstance(rule, str) or not rule.strip():
                raise ValueError('Invalid blocked URL rule')
            target, prefix = canonical(rule.strip())
            # Bare host or root URL blocks the site and every subdomain, on
            # either HTTP scheme and all ports. URL paths block descendants.
            if (host == target or host.endswith('.' + target)) and (
                prefix == '/' or path == prefix or path.startswith(prefix.rstrip('/') + '/')
            ):
                raise PermissionError('Destination blocked by administrator URL policy')
    except PermissionError:
        raise
    except Exception as exc:
        raise PermissionError('URL policy cannot be read safely; network access denied') from exc
