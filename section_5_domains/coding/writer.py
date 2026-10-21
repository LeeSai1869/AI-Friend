"""Compatibility import for the canonical guarded Coding execution cycle.

There is deliberately no direct provider call or filesystem mutation here.
"""
from .execution import CodingExecution

Writer = CodingExecution
