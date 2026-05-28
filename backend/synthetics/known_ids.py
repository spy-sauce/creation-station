# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Canonical synthetic candidate UUIDs.

Computed once via uuid.uuid5(uuid.NAMESPACE_DNS, "synthetic-<slug>") and
frozen as constants. The seeder produces these exact values deterministically;
this module is the membership oracle for detection.

Contract: NUTRIENTS.md § I.1 (as amended by iter-6).

Why constants instead of computing at import: the seeder MUST produce these
exact UUIDs, and analysis code MUST detect exactly this set. Drift between
compute paths would silently break detection. Constants close the gap.
"""

from uuid import UUID

SYNTHETIC_CANDIDATE_IDS: dict[str, UUID] = {
    "synthetic-jr-engineer": UUID("3c7eab85-c380-584b-a128-43bba592f163"),
    "synthetic-senior-ml":   UUID("24fd155e-d431-5dd1-9a59-ee9b70c535a6"),
    "synthetic-mid-product": UUID("fb752ea7-1682-5cb8-84b9-b6402e8675a6"),
}

SYNTHETIC_CANDIDATE_ID_SET: frozenset[UUID] = frozenset(SYNTHETIC_CANDIDATE_IDS.values())


def is_synthetic(candidate_id: UUID | str) -> bool:
    """Return True iff candidate_id is one of the 3 known synthetic UUIDs."""
    if isinstance(candidate_id, str):
        candidate_id = UUID(candidate_id)
    return candidate_id in SYNTHETIC_CANDIDATE_ID_SET
