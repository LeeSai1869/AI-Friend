ORGAN = {
    "name": "vision",
    "kind": "tool",
    "scope": "outside_guards",
    "capabilities": [
        "image_describe",
        "image_read_text",
        "pdf_read",
        "document_read",
        "video_read",
        "video_extract_frames",
    ],
    "security": {
        "requires": {
            "image_describe": [
                "workspace.read",
            ],
            "image_read_text": [
                "workspace.read",
            ],
            "pdf_read": [
                "workspace.read",
            ],
            "document_read": [
                "workspace.read",
            ],
            "video_read": [
                "workspace.read",
                "process.execute",
            ],
            "video_extract_frames": [
                "workspace.read",
                "workspace.write",
                "process.execute",
            ],
        },
    },
    "keywords": [],
    "entry_module": "vision.vision",
    "entry_attr": "TOOLS",
}
