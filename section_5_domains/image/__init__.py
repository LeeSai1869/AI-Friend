"""Image domain (placeholder for MVP)."""
from ..base import Domain


class ImageDomain(Domain):
    name = "image"

    def capabilities(self):
        return ["placeholder"]

    def execute(self, **kwargs):
        return {
            "success": True,
            "output": "Image domain is not implemented yet.",
            "artifacts": [],
        }