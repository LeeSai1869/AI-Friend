from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "section_0_app" / "src"


def test_coding_window_has_a_separate_chat_surface_for_central_mind():
    html = (APP / "window-code.html").read_text(encoding="utf-8")
    shell = (
        APP / "ui" / "coding" / "shell" / "shell.js"
    ).read_text(encoding="utf-8")
    styles = (APP / "styles.css").read_text(encoding="utf-8")

    assert 'id="btn-open-folder"' in html
    assert 'id="files-tree"' in html
    assert 'id="editor"' in html
    assert 'id="coding-terminal"' in html
    assert 'class="coding-chat-panel"' in html
    assert 'id="chat-thread"' in html
    assert 'id="input"' in html
    assert "createCodingInput" in shell
    assert "createCodingConversation" in shell
    assert 'surface: "coding"' in shell
    assert "sendDomainRequest" in shell
    assert "send(text, selectedIntent" in shell
    assert 'sendDomainRequest("coder", "open_project"' in shell
    assert "280px minmax(360px, 1fr) 420px" in styles


def test_regular_chat_passes_ui_surface_without_selecting_a_domain():
    shell = (
        APP / "ui" / "chat" / "shell" / "shell.js"
    ).read_text(encoding="utf-8")
    top_bar = (
        APP / "ui" / "chat" / "top_bar" / "top_bar.js"
    ).read_text(encoding="utf-8")
    chat_html = (APP / "window-chat.html").read_text(encoding="utf-8")

    assert 'kind: "regular"' in shell
    assert 'surface: "chat"' in shell
    assert "required_component" not in shell
    assert 'msg.op === "shared_context"' in shell
    assert "setActiveProject" in top_bar
    assert 'id="active-project-context"' in chat_html


def test_chat_and_coding_account_controls_use_authenticated_role_and_logout():
    controls = (
        APP / "ui" / "shared" / "account_controls" / "account_controls.js"
    ).read_text(encoding="utf-8")
    chat_shell = (
        APP / "ui" / "chat" / "shell" / "shell.js"
    ).read_text(encoding="utf-8")
    coding_shell = (
        APP / "ui" / "coding" / "shell" / "shell.js"
    ).read_text(encoding="utf-8")
    coding_html = (APP / "window-code.html").read_text(encoding="utf-8")

    assert "getAccount" in controls
    assert "onAuthStateChange" in controls
    assert 'role === "trainer"' in controls
    assert 'logout()' in controls
    assert "createAccountControls({ onOpenIntake: openIntake })" in chat_shell
    assert "createAccountControls({ onOpenIntake: openIntake })" in coding_shell
    assert 'id="btn-settings"' in coding_html
    assert 'id="btn-trainer"' in coding_html


def test_memory_intake_ui_has_no_file_count_or_content_size_cap():
    intake = (
        APP / "ui" / "chat" / "memory_intake" / "memory_intake.js"
    ).read_text(encoding="utf-8")

    assert "512 KiB" not in intake
    assert "MAX_CONTENT_BYTES" not in intake
    assert "files.length > 50" not in intake
    assert "at most 50 files" not in intake
    assert "await file.text()" in intake
    assert 'Could not read "${name}"' in intake
    assert '"svg"' in intake
    assert "data_base64: btoa(binary)" in intake
    assert "including scanned pages" in intake
    assert 'new TextDecoder("utf-8", { fatal: true })' not in intake


def test_chat_composer_supports_attachments_clipboard_paste_and_speech_input():
    chat_html = (APP / "window-chat.html").read_text(encoding="utf-8")
    coding_html = (APP / "window-code.html").read_text(encoding="utf-8")
    input_module = (
        APP / "ui" / "chat" / "input" / "input.js"
    ).read_text(encoding="utf-8")
    chat_shell = (
        APP / "ui" / "chat" / "shell" / "shell.js"
    ).read_text(encoding="utf-8")
    coding_shell = (
        APP / "ui" / "coding" / "shell" / "shell.js"
    ).read_text(encoding="utf-8")

    for html in (chat_html, coding_html):
        assert 'id="chat-attach"' in html
        assert 'id="chat-file-picker"' in html
        assert 'id="chat-mic"' in html
    assert "event.clipboardData" in input_module
    assert 'invoke("start_speech_to_text"' in input_module
    assert 'invoke("stop_speech_to_text"' in input_module
    assert '"speech-recognition"' in input_module
    assert "attachmentNames" in chat_shell
    assert "attachments," in chat_shell
    assert "attachmentNames" in coding_shell
    assert "attachments," in coding_shell


def test_languages_read_capability_is_not_project_file_inspection():
    import importlib.util

    manifest_path = (
        ROOT / "section_5_domains" / "languages" / "__manifest__.py"
    )
    spec = importlib.util.spec_from_file_location(
        "languages_manifest_boundary_test",
        manifest_path,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    description = module.ORGAN["capability_descriptions"]["read"]
    assert "natural-language text" in description
    assert "not project" in description
    assert "workspace file inspection" in description
