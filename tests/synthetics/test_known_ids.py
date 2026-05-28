# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Tests for backend.synthetics.known_ids module.

Verifies the canonical synthetic candidate UUIDs are:
1. Exactly 3 in count
2. Valid UUIDv5 (version field == 5)
3. Correctly detected by is_synthetic()
4. Reproducible from the canonical slugs

Contract: NUTRIENTS.md § I.1 (as amended by iter-6)
Owner: synthetics-fix-agent.tests
"""

import uuid
from uuid import UUID

import pytest

from backend.synthetics.known_ids import (
    SYNTHETIC_CANDIDATE_ID_SET,
    SYNTHETIC_CANDIDATE_IDS,
    is_synthetic,
)


class TestSyntheticCandidateIds:
    """Tests for SYNTHETIC_CANDIDATE_IDS constant."""

    def test_exactly_three_synthetic_candidates(self) -> None:
        """Assert len(SYNTHETIC_CANDIDATE_IDS) == 3."""
        assert len(SYNTHETIC_CANDIDATE_IDS) == 3

    def test_all_uuids_are_version_5(self) -> None:
        """Assert each value is a valid UUIDv5 (version field == 5)."""
        for slug, uid in SYNTHETIC_CANDIDATE_IDS.items():
            assert uid.version == 5, f"{slug} UUID {uid} is not version 5"

    def test_id_set_matches_ids_dict(self) -> None:
        """Assert the frozenset contains exactly the dict values."""
        assert SYNTHETIC_CANDIDATE_ID_SET == frozenset(SYNTHETIC_CANDIDATE_IDS.values())
        assert len(SYNTHETIC_CANDIDATE_ID_SET) == 3


class TestIsSynthetic:
    """Tests for is_synthetic() function."""

    def test_is_synthetic_returns_true_for_known_uuids(self) -> None:
        """Assert is_synthetic(known_id) is True for each known UUID."""
        for slug, uid in SYNTHETIC_CANDIDATE_IDS.items():
            assert is_synthetic(uid) is True, f"{slug} should be synthetic"

    def test_is_synthetic_returns_false_for_random_uuid4(self) -> None:
        """Assert is_synthetic(uuid4()) is False."""
        for _ in range(10):
            random_id = uuid.uuid4()
            assert is_synthetic(random_id) is False

    def test_is_synthetic_accepts_string_input(self) -> None:
        """Assert is_synthetic works with string UUID input."""
        for slug, uid in SYNTHETIC_CANDIDATE_IDS.items():
            assert is_synthetic(str(uid)) is True, f"{slug} string should be synthetic"

    def test_is_synthetic_returns_false_for_random_uuid_string(self) -> None:
        """Assert is_synthetic returns False for random UUID strings."""
        random_id = str(uuid.uuid4())
        assert is_synthetic(random_id) is False


class TestUuidReproducibility:
    """Tests that canonical slugs reproduce the constants exactly."""

    def test_recomputing_from_slugs_reproduces_constants(self) -> None:
        """
        Assert recomputing from the canonical slugs reproduces the constants exactly.

        This is the crucial invariant — if any future seeder change breaks it,
        the test fails before the bad code ships.

        Contract: NUTRIENTS.md § I.1
        """
        for slug, expected in SYNTHETIC_CANDIDATE_IDS.items():
            computed = uuid.uuid5(uuid.NAMESPACE_DNS, slug)
            assert computed == expected, (
                f"Recomputed UUID for {slug} does not match constant.\n"
                f"Expected: {expected}\n"
                f"Computed: {computed}\n"
                f"This breaks the synthetic detection contract."
            )

    def test_slugs_have_synthetic_prefix(self) -> None:
        """Assert all slugs start with 'synthetic-'."""
        for slug in SYNTHETIC_CANDIDATE_IDS:
            assert slug.startswith("synthetic-"), f"{slug} must start with 'synthetic-'"

    def test_known_slugs_are_canonical_set(self) -> None:
        """Assert the canonical slugs are exactly the expected set."""
        expected_slugs = {
            "synthetic-jr-engineer",
            "synthetic-senior-ml",
            "synthetic-mid-product",
        }
        actual_slugs = set(SYNTHETIC_CANDIDATE_IDS.keys())
        assert actual_slugs == expected_slugs


class TestUuidDistribution:
    """Tests documenting the UUIDv5 distribution lesson from iter-6."""

    def test_synthetic_uuids_do_not_start_with_zeros(self) -> None:
        """
        Assert that none of the synthetic UUIDs start with '00000000-'.

        This test documents the iter-6 lesson: UUIDv5 SHA-1 hashes do NOT
        produce predictable prefixes. The iter-5 assumption that synthetic
        UUIDs would start with '00000000-' was factually wrong.

        The correct detection mechanism is membership in SYNTHETIC_CANDIDATE_ID_SET,
        not SQL `WHERE id::text LIKE '00000000-%'`.
        """
        for slug, uid in SYNTHETIC_CANDIDATE_IDS.items():
            uid_str = str(uid)
            assert not uid_str.startswith("00000000-"), (
                f"Iter-6 lesson: {slug} UUID {uid_str} should NOT start with "
                "'00000000-' because UUIDv5 uses SHA-1 which distributes evenly."
            )

    def test_prefix_detection_would_fail(self) -> None:
        """
        Document that SQL `LIKE '00000000-%'` returns zero matches.

        This test exists to document the iter-6 bug: the iter-5 assumption
        that synthetic UUIDs could be detected by prefix was factually wrong.
        """
        # Simulate what the broken SQL query would match
        prefix_pattern = "00000000-"
        matched = [
            uid for uid in SYNTHETIC_CANDIDATE_IDS.values()
            if str(uid).startswith(prefix_pattern)
        ]

        # Assert zero matches - this proves the broken detection
        assert len(matched) == 0, (
            "Iter-6 lesson confirmed: LIKE '00000000-%' matches zero synthetic UUIDs. "
            "Use membership in SYNTHETIC_CANDIDATE_ID_SET instead."
        )

    def test_membership_detection_works(self) -> None:
        """
        Assert that membership detection correctly identifies all synthetic UUIDs.

        This is the correct detection mechanism: check if UUID is in the known set.
        """
        for slug, uid in SYNTHETIC_CANDIDATE_IDS.items():
            assert uid in SYNTHETIC_CANDIDATE_ID_SET, (
                f"{slug} UUID {uid} should be in SYNTHETIC_CANDIDATE_ID_SET"
            )

        # Also verify is_synthetic function
        for slug, uid in SYNTHETIC_CANDIDATE_IDS.items():
            assert is_synthetic(uid), f"{slug} should be detected by is_synthetic()"

    def test_variant_field_is_correct(self) -> None:
        """
        Assert UUIDv5 variant field is RFC 4122 compliant.

        UUIDv5 should have variant bits 10x (variant 1, RFC 4122).
        The variant can be checked via uuid.variant property.
        """
        import uuid as uuid_module

        for slug, uid in SYNTHETIC_CANDIDATE_IDS.items():
            # All UUIDv5 should be RFC 4122 variant
            assert uid.variant == uuid_module.RFC_4122, (
                f"{slug} UUID {uid} has unexpected variant {uid.variant}"
            )
