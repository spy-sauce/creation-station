# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
DEPRECATED: Use backend.observability instead.

This module re-exports from backend.observability for backwards compatibility.
New code should import directly from backend.observability.
"""

from backend.observability.logging import configure_logging, get_logger

# Legacy export — prefer get_logger(__name__) in new code
logger = get_logger()

__all__ = ["configure_logging", "logger", "get_logger"]
