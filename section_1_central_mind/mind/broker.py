"""The Tool Broker — the mind's tool interface.

Loads tools from section_8_tools/ at startup.
The mind calls tools by name. The broker routes.
The broker contains no tool logic. It only discovers, budgets, logs.

Adding a tool is adding a folder in section_8_tools/.
The broker discovers it. The mind never changes.
"""
from __future__ import annotations

import importlib
import importlib.util
import sys
import time

from guard.contract import (
    GuardComponent,
    GuardPrincipal,
    GuardRequest,
)
from guard.effects import EffectClassifier
from guard.resources import ResourceClassifier
from pathlib import Path
from typing import Any, Dict, List


class BoundToolBroker:
    """Restricted immutable view over one ToolBroker.

    A bound view carries trusted requester identity supplied by Central Mind.
    It does not expose the underlying broker, Guard, principal, registries,
    budget controls, or another binding operation.

    The view is intentionally tiny:
      - call()
      - available()

    Tool component identity is appended later by the master ToolBroker from
    its trusted operation-owner registry.
    """

    __slots__ = (
        "__broker",
        "__component_chain",
        "__workspace_root",
    )

    def __init__(
        self,
        broker,
        component_chain: tuple[GuardComponent, ...],
        workspace_root: Path | None = None,
    ):
        if not isinstance(component_chain, tuple):
            raise ValueError(
                "component_chain must be a tuple"
            )

        if not component_chain:
            raise ValueError(
                "bound broker requires a non-empty component chain"
            )

        for component in component_chain:
            if not isinstance(component, GuardComponent):
                raise ValueError(
                    "component_chain members must be GuardComponent"
                )

        object.__setattr__(self, "_BoundToolBroker__broker", broker)
        object.__setattr__(
            self,
            "_BoundToolBroker__component_chain",
            tuple(component_chain),
        )
        object.__setattr__(
            self,
            "_BoundToolBroker__workspace_root",
            (
                Path(workspace_root).resolve()
                if workspace_root is not None
                else None
            ),
        )

    @property
    def component_chain(self) -> tuple[GuardComponent, ...]:
        return self.__component_chain

    def call(
        self,
        tool_name: str,
        args: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self.__broker._call_bound(
            tool_name,
            args,
            requester_chain=self.__component_chain,
            workspace_root=self.__workspace_root,
        )

    def available(self) -> List[Dict[str, Any]]:
        return self.__broker.available()

    def with_workspace(
        self,
        workspace_root: Path,
    ) -> "BoundToolBroker":
        """Return an immutable view scoped to one filesystem workspace.

        This changes resource reach only.  It does not change principal,
        component identity, capabilities, Guard policy, or tool ownership.
        """
        root = Path(workspace_root).resolve()

        if not root.exists() or not root.is_dir():
            raise ValueError(
                f"workspace root is not a directory: {root}"
            )

        return BoundToolBroker(
            self.__broker,
            self.__component_chain,
            workspace_root=root,
        )

    def __setattr__(self, name, value):
        raise AttributeError(
            "BoundToolBroker is immutable"
        )


class ToolBroker:

    def __init__(
        self,
        workspace_root: Path,
        tools_dir: Path,
        budget: int = 20,
        logger=None,
        guard=None,
        principal: GuardPrincipal | None = None,
        inventory=None,
    ):
        self.workspace_root = Path(workspace_root).resolve()
        self.tools_dir = Path(tools_dir).resolve()
        self.budget = budget
        self.logger = logger or (lambda msg: None)

        # Trusted execution context.
        #
        # The Broker never constructs a human principal from tool-call
        # arguments, model output, role strings, or manifest content.
        self.guard = guard
        self.principal = principal
        self.inventory = inventory

        # Trusted effect-classification boundary.
        #
        # Resource ownership comes only from authoritative Inventory.
        # Inventory supplies the authoritative resource/effect
        # classification boundary. Bound guarded execution fails closed
        # when classification is unavailable.
        self.resource_classifier = None
        self.effect_classifier = None

        if self.inventory is not None:
            self.resource_classifier = ResourceClassifier(
                self.workspace_root,
                self.inventory,
            )
            self.effect_classifier = EffectClassifier(
                self.resource_classifier
            )

        # Guarded mode exists only when BOTH trusted objects are present.
        # Supplying only one is a configuration error and fails closed.
        if (self.guard is None) != (self.principal is None):
            raise ValueError(
                "guard and principal must be supplied together"
            )

        self.tools: Dict[str, Any] = {}

        # Trusted security requirements discovered from manifests.
        #
        # These are registration-time facts. Tool-call arguments and
        # model output never populate or override this registry.
        self.security_requirements: Dict[str, tuple[str, ...]] = {}

        # Trusted runtime operation -> registered tool component.
        #
        # When Inventory is supplied, ownership is derived from the
        # Inventory path that corresponds to the tool folder. A manifest
        # cannot grant itself another component's identity.
        self.operation_owners: Dict[str, str] = {}

        self.history: List[Dict[str, Any]] = []
        self.call_count = 0

        if str(self.tools_dir) not in sys.path:
            sys.path.insert(0, str(self.tools_dir))

        self._discover()

    def _discover(self) -> None:
        if not self.tools_dir.exists():
            self.logger(f"[broker] tools dir not found: {self.tools_dir}")
            return

        for folder in sorted(self.tools_dir.iterdir()):
            if not folder.is_dir() or folder.name.startswith("_"):
                continue
            manifest = folder / "__manifest__.py"
            if not manifest.exists():
                continue
            try:
                spec = importlib.util.spec_from_file_location(
                    f"toolpkg_{folder.name}_manifest", manifest
                )
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                organ = getattr(mod, "ORGAN", None)
                if not isinstance(organ, dict):
                    continue
            except Exception as e:
                self.logger(f"[broker] manifest failed for {folder.name}: {e}")
                continue

            entry_module = organ.get("entry_module")
            entry_attr = organ.get("entry_attr", "TOOLS")

            component_name = folder.name

            if self.inventory is not None:
                matching = []

                for info in self.inventory.all():
                    try:
                        info_path = Path(info.path).resolve()
                    except Exception:
                        continue

                    if (
                        getattr(info, "kind", None) == "tool"
                        and info_path == folder.resolve()
                    ):
                        matching.append(info)

                if len(matching) != 1:
                    self.logger(
                        "[broker] tool folder has no unique trusted "
                        f"Inventory identity: {folder}"
                    )
                    continue

                component_name = str(matching[0].name)

            security = organ.get("security", {})
            if security is None:
                security = {}

            if not isinstance(security, dict):
                self.logger(
                    f"[broker] invalid security manifest for {folder.name}"
                )
                continue

            requires_map = security.get("requires", {})
            if requires_map is None:
                requires_map = {}

            if not isinstance(requires_map, dict):
                self.logger(
                    f"[broker] invalid security.requires for {folder.name}"
                )
                continue

            normalized_requires = {}
            security_invalid = False

            for registered_name, required in requires_map.items():
                if (
                    not isinstance(registered_name, str)
                    or not registered_name.strip()
                ):
                    security_invalid = True
                    break

                if not isinstance(required, (list, tuple)):
                    security_invalid = True
                    break

                normalized = []

                for capability in required:
                    if (
                        not isinstance(capability, str)
                        or not capability.strip()
                    ):
                        security_invalid = True
                        break

                    normalized.append(
                        capability.strip().lower()
                    )

                if security_invalid:
                    break

                normalized_requires[
                    registered_name.strip()
                ] = tuple(normalized)

            if security_invalid:
                self.logger(
                    f"[broker] invalid security requirements for {folder.name}"
                )
                continue

            if not entry_module:
                continue

            try:
                engine = importlib.import_module(entry_module)
            except Exception as e:
                self.logger(f"[broker] import failed for {entry_module}: {e}")
                continue

            tool_classes = getattr(engine, entry_attr, None)
            if not tool_classes:
                continue

            # Track exactly which runtime names THIS manifest exports.
            #
            # self.tools contains registrations from earlier manifests too,
            # so it must never be used to prove that a security declaration
            # belongs to the manifest currently being processed.
            manifest_registered_names = set()

            for ToolClass in tool_classes:
                try:
                    instance = ToolClass(self.workspace_root, self)

                    tool_name = instance.name

                    if (
                        not isinstance(tool_name, str)
                        or not tool_name.strip()
                    ):
                        raise ValueError(
                            "tool instance has no valid name"
                        )

                    tool_name = tool_name.strip()

                    if tool_name in self.tools:
                        raise ValueError(
                            f"duplicate tool name: {tool_name}"
                        )

                    # A manifest may declare requirements only for tools
                    # actually exported by this manifest. Binding happens
                    # here, after the runtime instance name is known.
                    required = normalized_requires.get(
                        tool_name,
                        (),
                    )

                    self.tools[tool_name] = instance
                    self.security_requirements[
                        tool_name
                    ] = tuple(required)

                    self.operation_owners[
                        tool_name
                    ] = component_name

                    manifest_registered_names.add(tool_name)

                    self.logger(
                        f"[broker] registered tool: {tool_name}"
                    )
                except Exception as e:
                    self.logger(f"[broker] failed to instantiate {ToolClass}: {e}")

            undeclared_runtime_names = (
                set(normalized_requires)
                - manifest_registered_names
            )

            if undeclared_runtime_names:
                for bad_name in sorted(undeclared_runtime_names):
                    self.logger(
                        "[broker] security requirement refers to "
                        f"unregistered tool: {bad_name}"
                    )

    def bind_component(self, info) -> BoundToolBroker:
        """Create a trusted view for one Inventory-registered component.

        This method accepts an Inventory object, not arbitrary name/kind
        strings. Its path, name, and kind must match this Broker's trusted
        Inventory exactly.
        """
        if self.inventory is None:
            raise ValueError(
                "cannot bind component without authoritative Inventory"
            )

        matches = []

        for trusted in self.inventory.all():
            if trusted is info:
                matches.append(trusted)

        if len(matches) != 1:
            raise ValueError(
                "component is not the authoritative Inventory object"
            )

        trusted = matches[0]

        if trusted.kind not in {
            "domain",
            "model",
            "tool",
        }:
            raise ValueError(
                f"unsupported bound component kind: {trusted.kind!r}"
            )

        mind = GuardComponent(
            kind="central_mind",
            name="central_mind",
        )

        component = GuardComponent(
            kind=str(trusted.kind),
            name=str(trusted.name),
        )

        return BoundToolBroker(
            self,
            (mind, component),
        )

    def bind_central_mind(self) -> BoundToolBroker:
        """Create the trusted Central Mind broker view."""
        return BoundToolBroker(
            self,
            (
                GuardComponent(
                    kind="central_mind",
                    name="central_mind",
                ),
            ),
        )

    def reset_budget(self) -> None:
        self.call_count = 0

    def available(self) -> List[Dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in self.tools.values()
        ]

    def _call_bound(
        self,
        tool_name: str,
        args: Dict[str, Any],
        *,
        requester_chain: tuple[GuardComponent, ...],
        workspace_root: Path | None = None,
    ) -> Dict[str, Any]:
        if not isinstance(requester_chain, tuple):
            raise ValueError(
                "requester_chain must be a tuple"
            )

        for component in requester_chain:
            if not isinstance(component, GuardComponent):
                raise ValueError(
                    "requester_chain members must be GuardComponent"
                )

        start = time.time()

        if tool_name not in self.tools:
            return self._finish(
                tool_name,
                args,
                start,
                False,
                None,
                f"unknown tool: {tool_name}",
            )

        # Bound identity is necessary but not sufficient authority.
        # Runtime tool execution requires the trusted Guard + principal
        # pair installed by an authenticated execution entrance.
        #
        # A guardless ToolBroker may still exist for inventory discovery,
        # registration, inspection, and binding, but it has no execution
        # authority. Deny before effect preflight, budget consumption, or
        # tool control.
        if self.guard is None or self.principal is None:
            return self._finish(
                tool_name,
                args,
                start,
                False,
                None,
                "guard denied: trusted execution context is not installed",
            )

        # Authorization happens BEFORE budget consumption and BEFORE the
        # executable tool receives control.
        if self.guard is not None:
            required = self.security_requirements.get(
                tool_name,
                (),
            )

            owner = self.operation_owners.get(tool_name)

            if not owner:
                return self._finish(
                    tool_name,
                    args,
                    start,
                    False,
                    None,
                    "guard denied: tool operation has no trusted owner",
                )

            tool_component = GuardComponent(
                kind="tool",
                name=owner,
            )

            component_chain = (
                tuple(requester_chain)
                + (tool_component,)
            )

            # Effect preflight happens before Guard authorization, budget
            # consumption, and tool execution.
            #
            # The executable tool declares its intended effects. The Broker
            # then classifies filesystem targets through trusted Inventory.
            # Any missing/malformed declaration fails closed.
            if self.effect_classifier is None:
                return self._finish(
                    tool_name,
                    args,
                    start,
                    False,
                    None,
                    (
                        "guard denied: trusted effect classification "
                        "requires authoritative Inventory"
                    ),
                )

            try:
                execution_root = (
                    Path(workspace_root).resolve()
                    if workspace_root is not None
                    else self.workspace_root
                )

                ToolClass = self.tools[tool_name].__class__
                scoped_tool = ToolClass(execution_root, self)

                scoped_classifier = ResourceClassifier(
                    self.workspace_root,
                    self.inventory,
                    workspace_root=execution_root,
                )
                scoped_effect_classifier = EffectClassifier(
                    scoped_classifier
                )

                declared_effects = scoped_tool.effects(args)
                classified_effects = (
                    scoped_effect_classifier.classify(
                        declared_effects
                    )
                )
            except Exception as exc:
                return self._finish(
                    tool_name,
                    args,
                    start,
                    False,
                    None,
                    f"guard denied: effect preflight failed: {exc}",
                )

            request = GuardRequest(
                principal=self.principal,
                component=tool_component,
                component_chain=component_chain,
                operation=tool_name,
                resource="tool",
                target=tool_name,
                required_capabilities=tuple(required),
                effects=classified_effects,
                metadata={
                    "broker": "tool_broker",
                },
            )

            verdict = self.guard.audit_action(request)

            if (
                not isinstance(verdict, dict)
                or verdict.get("verdict") != "PASS"
            ):
                reason = (
                    verdict.get("reason")
                    if isinstance(verdict, dict)
                    else None
                ) or "Guard Layer denied tool execution."

                return self._finish(
                    tool_name,
                    args,
                    start,
                    False,
                    None,
                    f"guard denied: {reason}",
                )

        if self.call_count >= self.budget:
            return self._finish(
                tool_name,
                args,
                start,
                False,
                None,
                f"tool budget exceeded ({self.budget})",
            )

        self.call_count += 1

        try:
            execution_root = (
                Path(workspace_root).resolve()
                if workspace_root is not None
                else self.workspace_root
            )
            ToolClass = self.tools[tool_name].__class__
            execution_tool = ToolClass(execution_root, self)
            result = execution_tool.call(args)
        except Exception as e:
            result = {"ok": False, "data": None, "error": f"tool error: {e}"}

        return self._finish(tool_name, args, start,
                            result.get("ok", False),
                            result.get("data"),
                            result.get("error"))

    def _finish(self, name, args, start, ok, data, error):
        entry = {"ts": start, "tool": name, "args": args, "ok": ok,
                 "error": error, "duration_ms": int((time.time() - start) * 1000)}
        self.history.append(entry)
        self.logger(f"[broker] {name}({args}) -> {'OK' if ok else 'ERR'} ({entry['duration_ms']}ms)")
        return {"ok": ok, "data": data, "error": error,
                "meta": {"duration_ms": entry["duration_ms"], "call_index": self.call_count}}

    def recent(self, n: int = 20) -> List[Dict[str, Any]]:
        return self.history[-n:]
