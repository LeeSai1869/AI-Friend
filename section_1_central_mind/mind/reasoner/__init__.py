"""Central Mind Reasoner public boundary.

Internal reasoning machinery may evolve behind this package while callers
continue to depend only on the stable Reasoner interface.
"""

from .head import Reasoner

__all__ = ["Reasoner"]
