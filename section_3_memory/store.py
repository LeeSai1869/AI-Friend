"""The store - reads and writes entries to disk.

One file per entry. Small. Fast. Isolated.
A corrupt entry affects only itself.
"""
from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Iterator, List, Optional

from . import config
from .entry import Entry


class Store:

    def __init__(self, entries_dir: Path = None):
        self.entries_dir = Path(entries_dir or config.ENTRIES_DIR)
        self.entries_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path_for(self, mem_id: str) -> Path:
        """Resolve a strictly validated memory ID to its entry file."""
        domains = "|".join(re.escape(prefix) for prefix in config.DOMAIN_PREFIXES)
        pattern = (
            rf"{re.escape(config.ID_PREFIX)}_"
            rf"(?:{domains})_"
            rf"\d{{{config.SEQUENCE_DIGITS}}}"
        )
        if not isinstance(mem_id, str) or re.fullmatch(pattern, mem_id) is None:
            raise ValueError(f"invalid memory ID: {mem_id!r}")
        return self.entries_dir / f"{mem_id}.json"

    def write(self, entry: Entry) -> None:
        path = self._path_for(entry.id)
        tmp = path.with_suffix(".tmp")
        with self._lock:
            tmp.write_text(
                json.dumps(entry.as_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            tmp.replace(path)

    def read(self, mem_id: str) -> Optional[Entry]:
        path = self._path_for(mem_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return Entry.from_dict(data)
        except Exception:
            return None

    def exists(self, mem_id: str) -> bool:
        return self._path_for(mem_id).exists()

    def list_ids(self) -> List[str]:
        return [p.stem for p in sorted(self.entries_dir.glob("mem_*.json"))]

    def iter_entries(self) -> Iterator[Entry]:
        for mem_id in self.list_ids():
            entry = self.read(mem_id)
            if entry is not None:
                yield entry

    def count(self) -> int:
        return len(self.list_ids())
