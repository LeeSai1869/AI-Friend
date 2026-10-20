from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from section_1_central_mind.mind.inventory import Inventory


def write_manifest(
    folder: Path,
    *,
    name: str,
    kind: str | None = None,
) -> None:
    folder.mkdir(parents=True, exist_ok=True)

    lines = [
        "ORGAN = {",
        f"    'name': {name!r},",
    ]

    if kind is not None:
        lines.append(f"    'kind': {kind!r},")

    lines.extend([
        "    'scope': 'outside_guards',",
        "    'capabilities': [],",
        "    'keywords': [],",
        "    'entry_module': '',",
        "    'entry_attr': 'ORGAN',",
        "}",
    ])

    (folder / "__manifest__.py").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


class InventoryIdentitySecurityTests(unittest.TestCase):

    def test_duplicate_component_name_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            write_manifest(
                root / "section_5_domains" / "alpha",
                name="shared_identity",
            )
            write_manifest(
                root / "section_8_tools" / "beta",
                name="shared_identity",
            )

            with self.assertRaises(ValueError):
                Inventory(root).discover()

    def test_manifest_cannot_override_trusted_component_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            write_manifest(
                root / "section_8_tools" / "pretender",
                name="pretender",
                kind="domain",
            )

            inventory = Inventory(root).discover()
            info = inventory.get("pretender")

            self.assertIsNotNone(info)
            self.assertEqual(info.kind, "tool")
            self.assertEqual(
                info.path.resolve(),
                (root / "section_8_tools" / "pretender").resolve(),
            )

    def test_domain_kind_comes_from_domain_discovery_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            write_manifest(
                root / "section_5_domains" / "worker",
                name="worker",
                kind="tool",
            )

            inventory = Inventory(root).discover()
            info = inventory.get("worker")

            self.assertIsNotNone(info)
            self.assertEqual(info.kind, "domain")

    def test_blank_component_name_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            write_manifest(
                root / "section_7_models" / "blank",
                name="   ",
            )

            with self.assertRaises(ValueError):
                Inventory(root).discover()


if __name__ == "__main__":
    unittest.main()
