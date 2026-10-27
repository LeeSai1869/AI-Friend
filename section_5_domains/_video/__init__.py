"""Video domain (placeholder for MVP)."""
from ..base import Domain


class VideoDomain(Domain):
    name = "video"

    def capabilities(self):
        return ["placeholder"]

    def execute(self, **kwargs):
        return {
            "success": True,
            "output": "Video domain is not implemented yet.",
            "artifacts": [],
        }