"""Central Mind — entry point."""
from __future__ import annotations

import sys
from pathlib import Path

import bootstrap  # noqa: F401

from section_4_chatbox import Chatbox
from mind import CentralMind


def main() -> int:
    # Canonical project identity comes from the Central Mind source tree,
    # not from the launcher's current working directory.
    project_root = Path(__file__).resolve().parent.parent
    workspace = project_root

    chatbox = Chatbox()

    mind = CentralMind(
        project_root=project_root,
        chatbox=chatbox,
        guards=None,
    )

    print()
    print("=" * 60)
    print("                 CENTRAL MIND")
    print("=" * 60)
    print()
    print(mind.inventory_summary())
    print()
    print("Commands:")
    print("  /inventory   show the inventory")
    print("  /exit        quit")
    print()

    while True:
        try:
            user = input("You > ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not user:
            continue
        if user.lower() in {"exit", "/exit", "/quit"}:
            break
        if user == "/inventory":
            print(mind.inventory_summary())
            continue

        try:
            response = mind.process(user)
            chatbox.present(response)
        except Exception as exc:
            print(f"[mind error] {exc}")

        print()

    return 0

def _argument_value(name: str) -> str | None:
    """Return the value following a command-line option, if present."""
    try:
        index = sys.argv.index(name)
    except ValueError:
        return None

    value_index = index + 1
    if value_index >= len(sys.argv):
        raise SystemExit(f"{name} requires a value")

    return sys.argv[value_index]


def main_serve() -> int:
    """Run the mind as a WebSocket server for the app."""
    from server import run_server
    # Canonical project identity comes from the Central Mind source tree,
    # not from the launcher's current working directory.
    project_root = Path(__file__).resolve().parent.parent
    workspace = project_root

    owner_pid_text = _argument_value("--app-owner-pid")
    runtime_token = _argument_value("--app-runtime-token")

    owner_pid = None
    if owner_pid_text is not None:
        try:
            owner_pid = int(owner_pid_text)
        except ValueError as exc:
            raise SystemExit("--app-owner-pid must be an integer") from exc

        if owner_pid <= 0:
            raise SystemExit("--app-owner-pid must be positive")

    if (owner_pid is None) != (runtime_token is None):
        raise SystemExit(
            "app ownership requires both --app-owner-pid and "
            "--app-runtime-token"
        )

    # Documentation generation is an administrator/development operation.
    # Serving the application must not start a watcher that rewrites core docs.

    run_server(
        project_root,
        app_owner_pid=owner_pid,
        app_runtime_token=runtime_token,
    )
    return 0

if __name__ == "__main__":
    import sys as _sys
    if "--serve" in _sys.argv:
        _sys.exit(main_serve())
    _sys.exit(main())
