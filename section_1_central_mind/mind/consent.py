"""Session-local, single-use human approval records; never trust model flags."""
import copy
import secrets
import threading
import time


class ConsentRequests:
    def __init__(self):
        self._rows = {}
        self._lock = threading.Lock()

    def offer(self, *, description, tool, args):
        with self._lock:
            now = time.time()
            self._rows = {key: row for key, row in self._rows.items() if row['expires_at'] > now}
            if len(self._rows) >= 64:
                raise RuntimeError('Too many pending permission requests')
            key = secrets.token_urlsafe(24)
            self._rows[key] = {'request_id': key, 'description': description, 'tool': tool,
                               'args': copy.deepcopy(args), 'state': 'pending', 'expires_at': now + 600}
            return copy.deepcopy(self._rows[key])

    def list(self):
        with self._lock:
            return [copy.deepcopy(row) for row in self._rows.values()
                    if row['expires_at'] > time.time() and row['state'] == 'pending']

    def decide(self, key, approved):
        if not isinstance(approved, bool):
            raise ValueError('Approval must be an explicit boolean')
        with self._lock:
            row = self._valid(key)
            if row['state'] != 'pending':
                raise PermissionError('Permission already decided')
            row['state'] = 'approved' if approved else 'denied'
            return copy.deepcopy(row)

    def _valid(self, key):
        row = self._rows.get(key)
        if row is None or row['expires_at'] <= time.time():
            raise PermissionError('Unknown or expired permission request')
        return row

    def approved(self, key, tool, *, consume=False):
        with self._lock:
            row = self._valid(key)
            if row['state'] != 'approved' or row['tool'] != tool:
                raise PermissionError('Explicit human permission is required')
            if consume:
                row['state'] = 'consumed'
            return copy.deepcopy(row['args'])
