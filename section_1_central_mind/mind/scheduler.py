"""Generic, process-scoped scheduler."""
from __future__ import annotations
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class _Job:
    name: str
    fn: Callable[[], Any]
    interval_seconds: float
    next_run_at: float
    consecutive_failures: int = 0
    skip_intervals: int = 0
    last_error: Optional[str] = None
    runs: int = 0


class Scheduler:
    MAX_BACKOFF_SKIPS = 4

    def __init__(
        self,
        *,
        logger: Optional[Callable[[str], None]] = None,
        tick_seconds: float = 0.5,
    ):
        if tick_seconds <= 0:
            raise ValueError("tick_seconds must be positive")
        self._logger = logger or (lambda m: None)
        self._tick_seconds = float(tick_seconds)
        self._jobs: Dict[str, _Job] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def register(self, name, fn, *, interval_seconds):
        if not callable(fn): raise TypeError("fn must be callable")
        if interval_seconds <= 0: raise ValueError("interval must be > 0")
        key = str(name or "").strip()
        if not key: raise ValueError("name required")
        with self._lock:
            self._jobs[key] = _Job(
                name=key, fn=fn,
                interval_seconds=float(interval_seconds),
                next_run_at=time.time() + float(interval_seconds),
            )

    def unregister(self, name):
        with self._lock:
            self._jobs.pop(str(name or "").strip(), None)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self, *, timeout=5.0):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def run_once(self, name):
        with self._lock:
            job = self._jobs.get(str(name or "").strip())
        if job is None:
            return None
        return self._execute(job)

    def status(self):
        with self._lock:
            return [
                {"name": j.name, "interval_seconds": j.interval_seconds,
                 "next_run_at": j.next_run_at,
                 "consecutive_failures": j.consecutive_failures,
                 "skip_intervals": j.skip_intervals,
                 "runs": j.runs, "last_error": j.last_error}
                for j in self._jobs.values()
            ]

    def _run(self):
        while not self._stop.is_set():
            now = time.time()
            with self._lock:
                jobs = list(self._jobs.values())
            for job in jobs:
                if self._stop.is_set():
                    return
                if job.next_run_at > now:
                    continue
                self._execute(job)
            time.sleep(self._tick_seconds)

    def _execute(self, job):
        job.runs += 1
        try:
            job.fn()
            job.consecutive_failures = 0
            job.skip_intervals = 0
            job.last_error = None
            ok, error = True, None
        except Exception as exc:
            job.consecutive_failures += 1
            job.last_error = str(exc)
            job.skip_intervals = min(
                self.MAX_BACKOFF_SKIPS,
                max(job.skip_intervals, job.consecutive_failures - 1))
            ok, error = False, str(exc)
            self._logger(f"[scheduler] {job.name} failed: {exc}")
        job.next_run_at = time.time() + job.interval_seconds * (1 + job.skip_intervals)
        return {"job": job.name, "ok": ok, "error": error,
                "next_run_at": job.next_run_at,
                "consecutive_failures": job.consecutive_failures,
                "skip_intervals": job.skip_intervals}
