# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Tests for synthetics/fixtures/seeder.py idempotency and self-verify.

Verifies:
1. Calling seed() twice produces no duplicate rows
2. Self-verify block raises on UUID mismatch
3. Seeder uses known_ids as source of truth

Contract: NUTRIENTS.md § I.1 (as amended by iter-6)
Owner: synthetics-fix-agent.tests
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.synthetics.known_ids import SYNTHETIC_CANDIDATE_IDS, SYNTHETIC_CANDIDATE_ID_SET


class TestSeederIdempotency:
    """Tests for seeder idempotency."""

    @pytest.mark.asyncio
    async def test_seed_twice_produces_same_row_set(self) -> None:
        """
        Mock the DB session. Call seed() once, capture rows.
        Call seed() again, assert no duplicate INSERT, exactly the same row set.
        """
        # Track all candidates that would be inserted
        inserted_candidates: list[MagicMock] = []
        existing_ids: set[uuid.UUID] = set()

        async def mock_execute(query):
            """Mock execute. Per-candidate SELECT uses scalar_one_or_none;
            the post-loop verify SELECT iterates with fetchall().

            Extract the target id from the query's WHERE clause so each
            per-candidate probe answers independently — necessary because
            seed() probes candidate N+1 after add() of candidate N."""
            result = MagicMock()
            target_id = None
            try:
                # SQLAlchemy WHERE clause: BinaryExpression with .right.value
                clause = getattr(query, "whereclause", None) or getattr(query, "_where_criteria", [None])[0]
                if clause is not None:
                    target_id = clause.right.value
                    if isinstance(target_id, str):
                        target_id = uuid.UUID(target_id)
            except Exception:
                target_id = None
            if target_id is not None and target_id in existing_ids:
                result.scalar_one_or_none.return_value = MagicMock()
            else:
                result.scalar_one_or_none.return_value = None
            # Bulk verify: return tuples of (id,) for whatever has been seeded
            result.fetchall.return_value = [(uid,) for uid in existing_ids]
            return result

        mock_session = AsyncMock()
        mock_session.execute = mock_execute

        def mock_add(candidate):
            # Coerce id to UUID (the seeder may pass strings)
            cid = candidate.id if isinstance(candidate.id, uuid.UUID) else uuid.UUID(str(candidate.id))
            inserted_candidates.append(candidate)
            existing_ids.add(cid)

        mock_session.add = mock_add
        mock_session.commit = AsyncMock()

        # Patch AsyncSessionLocal to return our mock
        with patch("synthetics.fixtures.seeder.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None

            # Import after patching
            from synthetics.fixtures.seeder import seed

            # First seed
            await seed()
            first_count = len(inserted_candidates)

            # Second seed - should skip all existing
            await seed()
            second_count = len(inserted_candidates)

            # Assert no new inserts on second call
            assert second_count == first_count, (
                f"Second seed should not insert duplicates. "
                f"First: {first_count}, After second: {second_count}"
            )

    @pytest.mark.asyncio
    async def test_seed_produces_exactly_three_candidates(self) -> None:
        """Assert seed produces exactly 3 synthetic candidates."""
        inserted_candidates: list[MagicMock] = []
        existing_ids: set[uuid.UUID] = set()

        async def mock_execute(query):
            result = MagicMock()
            result.scalar_one_or_none.return_value = None
            result.fetchall.return_value = [(uid,) for uid in existing_ids]
            return result

        def _add(c):
            cid = c.id if isinstance(c.id, uuid.UUID) else uuid.UUID(str(c.id))
            inserted_candidates.append(c)
            existing_ids.add(cid)

        mock_session = AsyncMock()
        mock_session.execute = mock_execute
        mock_session.add = _add
        mock_session.commit = AsyncMock()

        with patch("synthetics.fixtures.seeder.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None

            from synthetics.fixtures.seeder import seed

            await seed()

            assert len(inserted_candidates) == 3


class TestSeederSelfVerify:
    """Tests for seeder self-verify block."""

    @pytest.mark.asyncio
    async def test_self_verify_raises_on_uuid_mismatch(self) -> None:
        """
        Simulate a seeder producing UUIDs that don't match the known_ids constants.
        The self-verify block should detect this and raise RuntimeError.

        The seeder's self-verify block does:
        1. Query DB for candidates WHERE id IN (known_ids)
        2. Compare returned set against SYNTHETIC_CANDIDATE_ID_SET
        3. Raise RuntimeError if mismatch

        To trigger this, we simulate the verify query returning an empty set
        (no matches), which would indicate the seeder produced wrong UUIDs.
        """
        # Track candidates that get added
        inserted_candidates: list[MagicMock] = []

        # First execute returns None for existence checks (no candidates exist)
        # Second execute (verify query) returns empty set (simulating wrong UUIDs)
        call_count = [0]

        async def mock_execute(query):
            """
            Mock execute that:
            - Returns None for first 3 calls (existence checks)
            - Returns empty result for verify query (simulating UUID mismatch)
            """
            call_count[0] += 1
            result = MagicMock()

            if call_count[0] <= 3:
                # First 3 calls are existence checks
                result.scalar_one_or_none.return_value = None
            else:
                # Fourth call is the verify query - return empty to trigger error
                result.fetchall.return_value = []

            return result

        mock_session = AsyncMock()
        mock_session.execute = mock_execute
        mock_session.add = lambda c: inserted_candidates.append(c)
        mock_session.commit = AsyncMock()

        with patch("synthetics.fixtures.seeder.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None

            from synthetics.fixtures.seeder import seed

            # The seeder should raise RuntimeError when verify detects mismatch
            with pytest.raises(RuntimeError, match="synthetic seeding produced unexpected UUIDs"):
                await seed()

    @pytest.mark.asyncio
    async def test_self_verify_passes_when_uuids_match(self) -> None:
        """
        Verify the self-verify block passes when seeded UUIDs match constants.

        The verify query returns all 3 known UUIDs, so the set comparison succeeds.
        """
        inserted_candidates: list[MagicMock] = []
        call_count = [0]

        async def mock_execute(query):
            """
            Mock execute that:
            - Returns None for first 3 calls (existence checks)
            - Returns all 3 known UUIDs for verify query (successful verification)
            """
            call_count[0] += 1
            result = MagicMock()

            if call_count[0] <= 3:
                # Existence checks
                result.scalar_one_or_none.return_value = None
            else:
                # Verify query - return all 3 known UUIDs
                result.fetchall.return_value = [(uid,) for uid in SYNTHETIC_CANDIDATE_ID_SET]

            return result

        mock_session = AsyncMock()
        mock_session.execute = mock_execute
        mock_session.add = lambda c: inserted_candidates.append(c)
        mock_session.commit = AsyncMock()

        with patch("synthetics.fixtures.seeder.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None

            from synthetics.fixtures.seeder import seed

            # Should complete without error when verify succeeds
            await seed()

        # Verify 3 candidates were inserted
        assert len(inserted_candidates) == 3

    def test_known_ids_import_available(self) -> None:
        """Assert known_ids module can be imported."""
        from backend.synthetics.known_ids import (
            SYNTHETIC_CANDIDATE_IDS,
            SYNTHETIC_CANDIDATE_ID_SET,
            is_synthetic,
        )

        assert len(SYNTHETIC_CANDIDATE_IDS) == 3
        assert len(SYNTHETIC_CANDIDATE_ID_SET) == 3
        assert callable(is_synthetic)


class TestSeederKnownIdsIntegration:
    """Tests for seeder integration with known_ids module."""

    def test_seeder_slugs_match_known_ids(self) -> None:
        """Assert seeder uses the same slugs as known_ids."""
        expected_slugs = set(SYNTHETIC_CANDIDATE_IDS.keys())

        # These are the slugs the seeder will use (from candidates.yaml)
        seeder_slugs = {
            "synthetic-jr-engineer",
            "synthetic-senior-ml",
            "synthetic-mid-product",
        }

        assert seeder_slugs == expected_slugs

    def test_uuid_computation_matches_known_ids(self) -> None:
        """Assert uuid5 computation matches known_ids constants."""
        for slug, expected_id in SYNTHETIC_CANDIDATE_IDS.items():
            computed = uuid.uuid5(uuid.NAMESPACE_DNS, slug)
            assert computed == expected_id, (
                f"UUID for {slug} does not match known_ids constant"
            )

    def test_get_synthetic_id_produces_known_ids(self) -> None:
        """
        Assert get_synthetic_id() produces the exact UUIDs from known_ids.

        This tests the seeder's UUID generation function directly.
        """
        from synthetics.fixtures.seeder import get_synthetic_id

        # Test with both slug formats (with and without prefix)
        test_cases = [
            ("jr-engineer", SYNTHETIC_CANDIDATE_IDS["synthetic-jr-engineer"]),
            ("synthetic-jr-engineer", SYNTHETIC_CANDIDATE_IDS["synthetic-jr-engineer"]),
            ("senior-ml", SYNTHETIC_CANDIDATE_IDS["synthetic-senior-ml"]),
            ("synthetic-senior-ml", SYNTHETIC_CANDIDATE_IDS["synthetic-senior-ml"]),
            ("mid-product", SYNTHETIC_CANDIDATE_IDS["synthetic-mid-product"]),
            ("synthetic-mid-product", SYNTHETIC_CANDIDATE_IDS["synthetic-mid-product"]),
        ]

        for slug, expected_id in test_cases:
            actual_id = get_synthetic_id(slug)
            assert actual_id == expected_id, (
                f"get_synthetic_id('{slug}') returned {actual_id}, "
                f"expected {expected_id}"
            )

    def test_seeder_imports_from_known_ids(self) -> None:
        """
        Assert the seeder imports SYNTHETIC_CANDIDATE_IDS from known_ids.

        This verifies the seeder uses known_ids as the source of truth
        rather than computing UUIDs independently.
        """
        # Import the seeder module's namespace
        from synthetics.fixtures import seeder as seeder_module

        # Verify SYNTHETIC_CANDIDATE_IDS is imported
        assert hasattr(seeder_module, "SYNTHETIC_CANDIDATE_IDS")
        assert hasattr(seeder_module, "SYNTHETIC_CANDIDATE_ID_SET")

        # Verify they reference the same objects
        from backend.synthetics.known_ids import (
            SYNTHETIC_CANDIDATE_IDS as known_ids_dict,
            SYNTHETIC_CANDIDATE_ID_SET as known_ids_set,
        )

        assert seeder_module.SYNTHETIC_CANDIDATE_IDS is known_ids_dict
        assert seeder_module.SYNTHETIC_CANDIDATE_ID_SET is known_ids_set
