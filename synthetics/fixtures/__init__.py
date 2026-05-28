# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Fixtures package for synthetic monitoring.

Provides:
    - Synthetic candidate definitions (candidates.yaml)
    - JD fixtures with expected scoring bands (jobs/)
    - Idempotent seeder for database population

Usage:
    from synthetics.fixtures import seed
    await seed()  # Idempotent — safe to call on every boot
"""

from synthetics.fixtures.seeder import seed

__all__ = ["seed"]
