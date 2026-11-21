"""Backward-compatible settings import; use app.config for new code."""
from app.config import Settings, settings
__all__ = ["Settings", "settings"]
