ORGAN = {
    "name": "vision",
    "kind": "tool",
    "scope": "outside_guards",
    "capabilities": [
        "image_describe",
        "image_read_text",
        "pdf_read",
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
