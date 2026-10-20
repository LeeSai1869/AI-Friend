import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "section_1_central_mind"))

ROOT = Path(__file__).resolve().parent.parent / "section_1_central_mind"

def test_importable():
    from mind.caller import Caller  # noqa
    from mind.router import Router  # noqa

def test_loop_instantiates():
    t = (ROOT / "mind" / "loop.py").read_text(encoding="utf-8")
    assert "Caller(" in t
