"""Canonical test-suite path and module identity.

See design notes: some section-1 modules import Guard/Mind helpers by
top-level name (`from guard.contract import ...`), because bootstrap.py
places section folders on sys.path. Tests import by full package path
(`from section_1_central_mind.guard.contract import ...`). Without
intervention these produce two distinct module objects and two distinct
class identities for GuardPrincipal and its siblings; isinstance then
fails across the boundary.

This conftest.py establishes section_1_central_mind.* as the canonical
module identity and aliases the top-level names to it, so that both
import styles resolve to the same objects.
"""
import importlib
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
_SECTION1 = _PROJECT_ROOT / "section_1_central_mind"

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

for _name in (
    "section_2_constitution",
    "section_3_memory",
    "section_4_chatbox",
    "section_5_domains",
    "section_6_capabilities",
    "section_7_models",
    "section_8_tools",
    "section_9_data",
    "section_10_workspace",
):
    _p = _PROJECT_ROOT / _name
    if _p.exists() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

_ALIASES = [
    ("guard", "section_1_central_mind.guard"),
    ("guard.contract", "section_1_central_mind.guard.contract"),
    ("guard.effects", "section_1_central_mind.guard.effects"),
    ("guard.effect_policy", "section_1_central_mind.guard.effect_policy"),
    ("guard.layer", "section_1_central_mind.guard.layer"),
    ("guard.policy", "section_1_central_mind.guard.policy"),
    ("guard.production_policy", "section_1_central_mind.guard.production_policy"),
    ("guard.resources", "section_1_central_mind.guard.resources"),
    ("mind", "section_1_central_mind.mind"),
    ("mind.loop", "section_1_central_mind.mind.loop"),
    ("mind.regular_operation", "section_1_central_mind.mind.regular_operation"),
    ("mind.self_assessment", "section_1_central_mind.mind.self_assessment"),
    ("mind.feature_expansion", "section_1_central_mind.mind.feature_expansion"),
    ("mind.shared", "section_1_central_mind.mind.shared"),
    ("mind.broker", "section_1_central_mind.mind.broker"),
    ("mind.inventory", "section_1_central_mind.mind.inventory"),
    ("mind.reasoner", "section_1_central_mind.mind.reasoner"),
    ("mind.appraiser", "section_1_central_mind.mind.appraiser"),
    ("mind.learner", "section_1_central_mind.mind.learner"),
    ("mind.verifier", "section_1_central_mind.mind.verifier"),
    ("mind.resource_socket", "section_1_central_mind.mind.resource_socket"),
    ("mind.caller", "section_1_central_mind.mind.caller"),
    ("mind.router", "section_1_central_mind.mind.router"),
    ("mind.cognition", "section_1_central_mind.mind.cognition"),
    ("mind.composer", "section_1_central_mind.mind.composer"),
    ("mind.questioner", "section_1_central_mind.mind.questioner"),
    ("mind.scorer", "section_1_central_mind.mind.scorer"),
    ("mind.capability_expansion", "section_1_central_mind.mind.capability_expansion"),
    ("mind.organ", "section_1_central_mind.mind.organ"),
    ("mind.designer", "section_1_central_mind.mind.designer"),
    ("mind.proposals", "section_1_central_mind.mind.proposals"),
    ("mind.audit", "section_1_central_mind.mind.audit"),
    ("mind.scheduler", "section_1_central_mind.mind.scheduler"),
]

for _alias, _canonical in _ALIASES:
    try:
        _mod = importlib.import_module(_canonical)
    except ImportError:
        continue
    sys.modules[_alias] = _mod
