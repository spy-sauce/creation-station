# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Entry point for running synthetics as a module.

Usage:
    python -m backend.synthetics run --suite=scoring

This module enables the CLI to be invoked via `python -m backend.synthetics`.
"""

import sys
from backend.synthetics.cli import main

if __name__ == "__main__":
    sys.exit(main())
