"""Bootstrap — add the project root and section packages to sys.path."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Add the project root FIRST. This lets `import section_3_memory`
# resolve as a proper package with relative imports inside it.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Also add each section folder so its modules can import each other.
SECTION_MODULES = [
    "section_2_constitution",
    "section_3_memory",
    "section_4_chatbox",
    "section_5_domains",
    "section_6_capabilities",
    "section_7_models",
    "section_8_tools",
    "section_9_data",
    "section_10_workspace",
]


def add_sections_to_path() -> None:
    for name in SECTION_MODULES:
        path = PROJECT_ROOT / name
        if path.exists() and str(path) not in sys.path:
            sys.path.insert(0, str(path))


add_sections_to_path()
