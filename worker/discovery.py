"""Backwards-compatible re-export — engine moved to demoforge.core.discovery."""
from demoforge.core.discovery import InteractionDiscovery, InteractionElement  # noqa: F401

__all__ = ["InteractionDiscovery", "InteractionElement"]
