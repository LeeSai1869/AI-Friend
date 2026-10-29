"""Serialize writers sharing a memory directory, including separate sessions."""
from contextlib import contextmanager
from pathlib import Path
import threading

_locks = {}
_guard = threading.Lock()


@contextmanager
def memory_lock(root, name):
    path = Path(root).resolve() / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with _guard:
        lock = _locks.setdefault(str(path), threading.RLock())
    with lock:
        with path.open('a+b') as handle:
            try:
                import fcntl
            except ImportError:
                raise RuntimeError('Cross-process memory locking requires a supported Unix runtime')
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
