import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "section_1_central_mind"))

from mind.scheduler import Scheduler


def _sched():
    return Scheduler(tick_seconds=0.02)


def test_start_stop():
    calls = []
    s = _sched()
    s.register("j", lambda: calls.append(1), interval_seconds=0.02)
    s.start()
    time.sleep(0.15)
    s.stop()
    assert len(calls) >= 1


def test_job_exception_isolated():
    def boom():
        raise RuntimeError("boom")

    s = _sched()
    s.register("j", boom, interval_seconds=0.02)
    s.start()
    time.sleep(0.15)
    s.stop()
    status = {r["name"]: r for r in s.status()}
    assert status["j"]["consecutive_failures"] >= 1
    assert status["j"]["last_error"] == "boom"


def test_run_once():
    s = _sched()
    s.register("j", lambda: None, interval_seconds=60)
    r = s.run_once("j")
    assert r["ok"] is True


def test_register_validates():
    s = _sched()
    try:
        s.register("", lambda: None, interval_seconds=1)
        assert False
    except ValueError:
        pass
    try:
        s.register("j", "not-callable", interval_seconds=1)
        assert False
    except TypeError:
        pass
    try:
        s.register("j", lambda: None, interval_seconds=0)
        assert False
    except ValueError:
        pass


def test_add_after_start():
    s = _sched()
    a, b = [], []
    s.register("a", lambda: a.append(1), interval_seconds=0.02)
    s.start()
    time.sleep(0.08)
    s.register("b", lambda: b.append(1), interval_seconds=0.02)
    time.sleep(0.15)
    s.stop()
    assert len(a) >= 1
    assert len(b) >= 1


def test_tick_seconds_validates():
    try:
        Scheduler(tick_seconds=0)
        assert False
    except ValueError:
        pass
    try:
        Scheduler(tick_seconds=-1)
        assert False
    except ValueError:
        pass
