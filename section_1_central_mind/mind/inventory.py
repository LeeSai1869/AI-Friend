"""The Inventory.

Reads every organ's manifest at startup. Builds the list of what
exists. The mind consults this list for routing. The inventory
holds only capability references — never content.

Reader of all, writer of nothing.
"""
from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class OrganInfo:
    name: str
    kind: str
    scope: str
    capabilities: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    entry_module: str = ""
    entry_attr: str = ""
    manifest: Dict[str, Any] = field(default_factory=dict)
    path: Path = field(default_factory=Path)


class Inventory:
    """Discovers organs by scanning section folders."""

    SEARCH_DIRS = [
        ("section_5_domains", "domain"),
        ("section_7_models", "model"),
        ("section_8_tools", "tool"),
    ]

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()
        self.organs: Dict[str, OrganInfo] = {}

    # ---- public API ----------------------------------------------

    def discover(self) -> "Inventory":
        """Scan every section folder and load manifests."""
        for dirname, kind in self.SEARCH_DIRS:
            folder = self.project_root / dirname
            if not folder.exists():
                continue
            for child in sorted(folder.iterdir()):
                if not child.is_dir():
                    continue
                if child.name.startswith("_"):
                    continue
                manifest_file = child / "__manifest__.py"
                if not manifest_file.exists():
                    continue
                self._load_manifest(child, kind, manifest_file)
        return self

    def all(self) -> List[OrganInfo]:
        return list(self.organs.values())

    def get(self, name: str) -> Optional[OrganInfo]:
        return self.organs.get(name)

    def by_keyword(self, keyword: str) -> List[OrganInfo]:
        kw = keyword.lower()
        return [
            o for o in self.organs.values()
            if any(k.lower() == kw for k in o.keywords)
        ]

    def by_capability(self, cap: str) -> List[OrganInfo]:
        return [
            o for o in self.organs.values()
            if cap in o.capabilities
        ]

    def names(self) -> List[str]:
        return list(self.organs.keys())

    def capability_catalog(self) -> List[Dict[str, Any]]:
        """Return trusted, machine-readable capability descriptions.

        Manifests may optionally provide:

            capability_descriptions = {
                "capability_id": "semantic description"
            }

        Existing manifests remain valid.  When no explicit description is
        present, the stable capability identifier is converted into a small
        human-readable fallback.  The catalog is descriptive only; it grants
        no authority.
        """
        rows: List[Dict[str, Any]] = []

        for organ in self.all():
            manifest = organ.manifest or {}
            descriptions = manifest.get(
                "capability_descriptions",
                {},
            )

            if not isinstance(descriptions, dict):
                descriptions = {}

            for capability in organ.capabilities:
                cap = str(capability or "").strip()
                if not cap:
                    continue

                explicit = descriptions.get(cap)
                if isinstance(explicit, str) and explicit.strip():
                    description = explicit.strip()
                else:
                    description = cap.replace("_", " ")

                rows.append({
                    "component": organ.name,
                    "kind": organ.kind,
                    "capability": cap,
                    "description": description,
                })

        return rows

    def validate_capability(
        self,
        component: str,
        capability: str,
    ) -> bool:
        """Validate a semantic routing proposal against trusted Inventory."""
        info = self.get(str(component or "").strip())
        if info is None:
            return False

        return str(capability or "").strip() in info.capabilities

    # ---- loading -------------------------------------------------

    def _load_manifest(self, folder: Path, kind: str, manifest_file: Path) -> None:
        print(f"[inventory] scanning: {folder.name}")
        try:
            spec = importlib.util.spec_from_file_location(
                f"_manifest_{folder.name}", manifest_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            manifest = getattr(module, "ORGAN", None) or getattr(module, "DOMAIN", None)
            if not isinstance(manifest, dict):
                print(f"[inventory] {folder.name}: no ORGAN dict found")
                return
        except Exception as e:
            print(f"[inventory] {folder.name}: LOAD FAILED — {e}")
            return

        name = manifest.get("name", folder.name)
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"Invalid component name in manifest: {manifest_file}"
            )
        name = name.strip()

        if name in self.organs:
            existing = self.organs[name]
            raise ValueError(
                "Duplicate component identity "
                f"{name!r}: {existing.path} and {folder}"
            )

        self.organs[name] = OrganInfo(
            name=name,
            # Security identity comes from the trusted discovery root,
            # never from a manifest-controlled kind declaration.
            kind=kind,
            scope=manifest.get("scope", "outside_guards"),
            capabilities=list(manifest.get("capabilities", [])),
            keywords=list(manifest.get("keywords", [])),
            entry_module=manifest.get("entry_module", ""),
            entry_attr=manifest.get("entry_attr", "ORGAN"),
            manifest=manifest,
            path=folder,
        )
        print(f"[inventory] loaded: {folder.name} → name='{name}' kind='{kind}'")