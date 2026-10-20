"""Trading domain (placeholder for MVP)."""
from ..base import Domain


class TradingDomain(Domain):
    name = "trading"

    def capabilities(self):
        return ["placeholder"]

    def execute(self, **kwargs):
        return {
            "success": True,
            "output": "Trading domain is not implemented yet.",
            "artifacts": [],
        }   