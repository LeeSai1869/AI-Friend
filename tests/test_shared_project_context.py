from pathlib import Path
import sys


CENTRAL_MIND_DIR = Path(__file__).resolve().parents[1] / "section_1_central_mind"
sys.path.insert(0, str(CENTRAL_MIND_DIR))

import server


def test_active_project_context_is_shared_only_within_the_same_session():
    runtimes = server.SessionRuntimes(auth_service=None)
    project = {
        "name": "AI Friend V1",
        "root": "/projects/AI Friend V1",
    }

    assert runtimes.set_active_project("session-one", project) == project
    assert runtimes.get_active_project("session-one") == project
    assert runtimes.get_active_project("session-two") is None


def test_central_mind_context_overrides_client_supplied_project_context():
    runtimes = server.SessionRuntimes(auth_service=None)
    project = {
        "name": "AI Friend V1",
        "root": "/projects/AI Friend V1",
    }
    runtimes.set_active_project("session-one", project)

    context = runtimes.chat_context(
        "session-one",
        {
            "active_window": {"kind": "regular", "surface": "chat"},
            "shared_context": {"active_project": {"name": "forged"}},
        },
    )

    assert context["active_window"] == {
        "kind": "regular",
        "surface": "chat",
    }
    assert context["shared_context"] == {"active_project": project}


def test_forgetting_session_clears_its_shared_project_context():
    runtimes = server.SessionRuntimes(auth_service=None)
    runtimes.set_active_project(
        "session-one",
        {"name": "AI Friend V1", "root": "/projects/AI Friend V1"},
    )

    runtimes.forget("session-one")

    assert runtimes.get_active_project("session-one") is None
