"""The Memory section.

Standalone. Reads and writes numbered entries.
Nothing in the mind is touched.
"""
from .api import Memory
from .entry import Entry, Originator, Failure, CrossRef

__all__ = ["Memory", "Entry", "Originator", "Failure", "CrossRef"]
