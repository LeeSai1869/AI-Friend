import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "section_1_central_mind"))

ROOT = Path(__file__).resolve().parent.parent / "section_1_central_mind"

def test_module_absent():
    assert not (ROOT / "mind" / "tool_loop.py").exists()

def test_no_imports():
    for p in ROOT.rglob("*.py"):
        if "__pycache__" in p.parts: continue
        assert "tool_loop" not in p.read_text(encoding="utf-8", errors="replace"), str(p)
