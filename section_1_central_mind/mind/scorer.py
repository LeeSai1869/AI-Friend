"""Central Mind temporary experience recorder.

Historical name: Scorer.

V1 no longer treats Scorer as a second permanent-memory database.

Its responsibility is a bounded in-process window of compact operational
experience used by appraisal/debugging. Permanent reusable intelligence
belongs to Section 3 through Learner -> Memory Service.

The public ``record`` method retains compatibility with older injected
test doubles/call shapes while never delegating scoring authority to an organ.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from typing import Any, Dict, List, Optional
import json
import time


class EvidenceContractError(ValueError):
    pass


class Scorer:
    MAX_EVENTS = 256

    def __init__(self, project_root=None, max_events: int = MAX_EVENTS):
        self.project_root = project_root
        self.max_events = max(1, int(max_events))
        self._events = deque(maxlen=self.max_events)

    def record(
        self,
        organ=None,
        event=None,
        **fields,
    ) -> Dict[str, Any]:
        """Record one compact temporary experience.

        Supported call shapes:

        New canonical form:
            record(event="cognitive_result", objective="...")

        Legacy compatibility form:
            record(organ, {"event": "handled", ...})

        Mapping-only form:
            record({"event": "handled", ...})

        The organ is used only as an identity hint. Scorer never delegates
        scoring authority back to the component.
        """
        payload: Dict[str, Any] = {}

        # Mapping-only compatibility:
        # record({"event": "...", ...})
        if isinstance(organ, dict) and event is None:
            payload.update(organ)
            organ = None

        # Legacy second positional mapping:
        # record(real_organ, {"event": "...", ...})
        elif isinstance(event, dict):
            payload.update(event)

        # Canonical keyword event:
        # record(event="cognitive_result", ...)
        elif isinstance(event, str):
            if not event.strip():
                raise EvidenceContractError(
                    "event name must be non-empty"
                )
            payload["event"] = event.strip()

        elif event is not None:
            raise EvidenceContractError(
                "event must be a string event name or mapping"
            )

        payload.update(fields)

        if organ is not None and "originating_component" not in payload:
            name = getattr(organ, "name", None)
            if isinstance(name, str) and name:
                payload["originating_component"] = name

        payload.setdefault("event", "runtime_experience")
        payload.setdefault("ts", time.time())

        # Compatibility conversion only. Outcome remains distinct from
        # verification in all new cognitive calls.
        if "outcome" not in payload and isinstance(payload.get("ok"), bool):
            payload["outcome"] = "success" if payload["ok"] else "failure"

        self._validate_json(payload)
        compact = deepcopy(payload)
        self._events.append(compact)
        return deepcopy(compact)

    def recent(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        rows = list(self._events)
        if limit is not None:
            rows = rows[-max(0, int(limit)):]
        return deepcopy(rows)

    def read_records(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        # Compatibility alias for the earlier prototype API.
        return self.recent(limit=limit)

    @staticmethod
    def _validate_json(payload: Dict[str, Any]) -> None:
        try:
            json.dumps(payload, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise EvidenceContractError(
                f"experience payload is not JSON-safe: {exc}"
            ) from exc
