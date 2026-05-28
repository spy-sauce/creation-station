# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Review Dashboard Approve Flow integration tests.

Full end-to-end tests for the application approval workflow:
  - Create application pipeline → approve → verify state transition
  - CRM event logging on approval
  - Error handling for non-existent and invalid-status pipelines

Contract:
  - HYPHA-TESTS.md § tests-agent.api.review
  - NUTRIENTS.md § API_CONTRACTS review endpoints
  - HYPHA-REVIEW-DASHBOARD.md acceptance criteria

Coverage:
  - Create application row in test database
  - PATCH approve, assert state transition to APPROVED
  - Verify crm_events row written on approval
  - 404 on non-existent pipeline
  - 422 on approving non-AWAITING_REVIEW pipeline
  - PATCH reject, assert state transition to REJECTED

NOTE: Uses mocked database operations because the ORM models use PostgreSQL-
specific types (ARRAY, JSONB) that are incompatible with SQLite testing.
"""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis.aioredis
import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.config import settings


# ─── Mock ORM Objects ────────────────────────────────────────────────────────


def create_mock_pipeline(
    pipeline_id: uuid.UUID,
    candidate_id: uuid.UUID,
    job_id: uuid.UUID,
    status: str = "AWAITING_REVIEW",
    current_step: str = "compose",
) -> MagicMock:
    """Create a mock ApplicationPipeline ORM object."""
    mock = MagicMock()
    mock.id = pipeline_id
    mock.candidate_id = candidate_id
    mock.job_id = job_id
    mock.status = status
    mock.current_step = current_step
    mock.created_at = datetime.now(timezone.utc)
    mock.updated_at = datetime.now(timezone.utc)
    mock.resume_id = None
    mock.email_id = None
    mock.approval_timestamp = None
    return mock


def create_mock_crm_event(
    pipeline_id: uuid.UUID,
    candidate_id: uuid.UUID,
    job_id: uuid.UUID,
    event_type: str,
) -> MagicMock:
    """Create a mock CRMEvent ORM object."""
    mock = MagicMock()
    mock.id = uuid.uuid4()
    mock.pipeline_id = pipeline_id
    mock.candidate_id = candidate_id
    mock.job_id = job_id
    mock.event_type = event_type
    mock.details = None
    mock.payload = {}
    mock.created_at = datetime.now(timezone.utc)
    return mock


# ─── Test App Setup ──────────────────────────────────────────────────────────


def create_test_app(mock_db_session, fake_redis) -> FastAPI:
    """
    Create a minimal test FastAPI app with the review router.

    This avoids the main app's lifespan which tries to connect to PostgreSQL.
    """
    from fastapi.middleware.cors import CORSMiddleware
    from backend.api.review import router as review_router
    from backend.database import get_db, set_redis_client

    # Import get_redis from where review.py imports it
    from backend.api.discovery import get_redis as discovery_get_redis

    @asynccontextmanager
    async def test_lifespan(app: FastAPI):
        """Minimal test lifespan that doesn't require real database."""
        set_redis_client(fake_redis)
        yield

    test_app = FastAPI(lifespan=test_lifespan)

    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include the review router at the same path as the main app
    test_app.include_router(review_router, prefix="/api/v1/review", tags=["review"])

    # Override dependencies - need to override the exact dependency used in review.py
    test_app.dependency_overrides[get_db] = lambda: mock_db_session
    test_app.dependency_overrides[discovery_get_redis] = lambda: fake_redis

    return test_app


# ─── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def pipeline_id() -> uuid.UUID:
    """Generate a test pipeline ID."""
    return uuid.uuid4()


@pytest.fixture
def candidate_id() -> uuid.UUID:
    """Generate a test candidate ID."""
    return uuid.uuid4()


@pytest.fixture
def job_id() -> uuid.UUID:
    """Generate a test job ID."""
    return uuid.uuid4()


@pytest.fixture
def fake_redis():
    """Create a fake Redis client for testing."""
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


@pytest.fixture
def valid_jwt() -> str:
    """Generate a valid JWT for testing."""
    user_id = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "email": "reviewer@example.com",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=1),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


@pytest.fixture
def mock_db_session():
    """Create a mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def test_app(mock_db_session, fake_redis) -> FastAPI:
    """Create a test FastAPI app with mocked dependencies."""
    return create_test_app(mock_db_session, fake_redis)


@pytest.fixture
def test_client(test_app: FastAPI) -> Generator[TestClient, None, None]:
    """Create a TestClient for the app."""
    with TestClient(test_app) as client:
        yield client


# ─── Approve Endpoint Tests ───────────────────────────────────────────────────


class TestApproveApplication:
    """Test PATCH /api/v1/review/application/{pipeline_id}/approve endpoint."""

    def test_approve_awaiting_review_pipeline_succeeds(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        pipeline_id: uuid.UUID,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
    ):
        """
        Approving a pipeline in AWAITING_REVIEW status should succeed.

        Asserts:
          - Response status 200
          - Response contains pipeline_id and status='APPROVED'
        """
        # Setup: mock pipeline lookup returns a pipeline in AWAITING_REVIEW
        mock_pipeline = create_mock_pipeline(
            pipeline_id, candidate_id, job_id, status="AWAITING_REVIEW"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_pipeline
        mock_db_session.execute.return_value = mock_result

        response = test_client.patch(
            f"/api/v1/review/application/{pipeline_id}/approve"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pipeline_id"] == str(pipeline_id)
        assert data["status"] == "APPROVED"

    def test_approve_transitions_status_to_approved(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        pipeline_id: uuid.UUID,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
    ):
        """
        Approving should transition pipeline status from AWAITING_REVIEW to APPROVED.

        This test verifies the pipeline object's status is updated.
        """
        mock_pipeline = create_mock_pipeline(
            pipeline_id, candidate_id, job_id, status="AWAITING_REVIEW"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_pipeline
        mock_db_session.execute.return_value = mock_result

        response = test_client.patch(
            f"/api/v1/review/application/{pipeline_id}/approve"
        )

        assert response.status_code == 200
        # Verify the pipeline status was updated
        assert mock_pipeline.status == "APPROVED"
        # Verify commit was called
        mock_db_session.commit.assert_called()

    def test_approve_calls_crm_log(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        pipeline_id: uuid.UUID,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
    ):
        """
        Approving should log a CRM event for audit trail.

        Contract: HYPHA-TESTS.md § tests-agent.api.review
        "Asserts application_events row written" (maps to crm_events table)
        """
        mock_pipeline = create_mock_pipeline(
            pipeline_id, candidate_id, job_id, status="AWAITING_REVIEW"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_pipeline
        mock_db_session.execute.return_value = mock_result

        # Patch CRM to verify it's called
        with patch("backend.api.review.CRM") as MockCRM:
            mock_crm_instance = AsyncMock()
            MockCRM.return_value = mock_crm_instance

            response = test_client.patch(
                f"/api/v1/review/application/{pipeline_id}/approve"
            )

            assert response.status_code == 200

            # Verify CRM.log was called with correct event type
            mock_crm_instance.log.assert_called_once()
            call_args = mock_crm_instance.log.call_args
            assert call_args.args[0] == pipeline_id  # pipeline_id
            assert call_args.args[1] == candidate_id  # candidate_id
            assert call_args.args[2] == job_id  # job_id
            assert call_args.args[3] == "APPROVED_FOR_SUBMISSION"  # event_type

    def test_approve_nonexistent_pipeline_returns_404(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
    ):
        """
        Approving a non-existent pipeline should return 404.

        Contract: NUTRIENTS.md § API_CONTRACTS
        "Error responses: 404: 'Pipeline not found'"
        """
        fake_pipeline_id = uuid.uuid4()

        # Setup: mock pipeline lookup returns None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        response = test_client.patch(
            f"/api/v1/review/application/{fake_pipeline_id}/approve"
        )

        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()

    def test_approve_queued_pipeline_returns_422(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        pipeline_id: uuid.UUID,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
    ):
        """
        Approving a pipeline not in AWAITING_REVIEW status should return 422.

        Contract: NUTRIENTS.md § API_CONTRACTS
        "Error responses: 400: 'Pipeline is not awaiting review'"
        """
        # Pipeline is in QUEUED status, not AWAITING_REVIEW
        mock_pipeline = create_mock_pipeline(
            pipeline_id, candidate_id, job_id, status="QUEUED"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_pipeline
        mock_db_session.execute.return_value = mock_result

        response = test_client.patch(
            f"/api/v1/review/application/{pipeline_id}/approve"
        )

        assert response.status_code == 422
        detail = response.json().get("detail", "")
        assert "not awaiting review" in detail.lower() or "QUEUED" in detail

    def test_approve_already_approved_pipeline_returns_422(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        pipeline_id: uuid.UUID,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
    ):
        """
        Re-approving an already APPROVED pipeline should return 422.

        Idempotency check — prevents double-approvals.
        """
        mock_pipeline = create_mock_pipeline(
            pipeline_id, candidate_id, job_id, status="APPROVED"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_pipeline
        mock_db_session.execute.return_value = mock_result

        response = test_client.patch(
            f"/api/v1/review/application/{pipeline_id}/approve"
        )

        assert response.status_code == 422
        detail = response.json().get("detail", "")
        assert "APPROVED" in detail or "not awaiting review" in detail.lower()

    def test_approve_publishes_to_redis(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        fake_redis,
        pipeline_id: uuid.UUID,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
    ):
        """
        Approving should publish an event to Redis for the orchestrator.

        The approve endpoint publishes to 'application.approved' channel.
        We verify this by mocking the redis publish method.
        """
        mock_pipeline = create_mock_pipeline(
            pipeline_id, candidate_id, job_id, status="AWAITING_REVIEW"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_pipeline
        mock_db_session.execute.return_value = mock_result

        # Use a spy on the fake_redis publish method
        original_publish = fake_redis.publish
        publish_calls = []

        async def spy_publish(channel, message):
            publish_calls.append((channel, message))
            return await original_publish(channel, message)

        fake_redis.publish = spy_publish

        response = test_client.patch(
            f"/api/v1/review/application/{pipeline_id}/approve"
        )
        assert response.status_code == 200

        # Verify publish was called with correct channel
        assert len(publish_calls) == 1, "Expected exactly one publish call"
        channel, message = publish_calls[0]
        assert channel == "application.approved"

        # Verify message content
        payload = json.loads(message)
        assert payload["pipeline_id"] == str(pipeline_id)
        assert payload["candidate_id"] == str(candidate_id)


# ─── Reject Endpoint Tests ────────────────────────────────────────────────────


class TestRejectApplication:
    """Test PATCH /api/v1/review/application/{pipeline_id}/reject endpoint."""

    def test_reject_awaiting_review_pipeline_succeeds(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        pipeline_id: uuid.UUID,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
    ):
        """
        Rejecting a pipeline should succeed.

        Asserts:
          - Response status 200
          - Response contains pipeline_id and status='REJECTED'
        """
        mock_pipeline = create_mock_pipeline(
            pipeline_id, candidate_id, job_id, status="AWAITING_REVIEW"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_pipeline
        mock_db_session.execute.return_value = mock_result

        response = test_client.patch(
            f"/api/v1/review/application/{pipeline_id}/reject"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["pipeline_id"] == str(pipeline_id)
        assert data["status"] == "REJECTED"

    def test_reject_transitions_status_to_rejected(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        pipeline_id: uuid.UUID,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
    ):
        """
        Rejecting should transition pipeline status to REJECTED.
        """
        mock_pipeline = create_mock_pipeline(
            pipeline_id, candidate_id, job_id, status="AWAITING_REVIEW"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_pipeline
        mock_db_session.execute.return_value = mock_result

        response = test_client.patch(
            f"/api/v1/review/application/{pipeline_id}/reject"
        )

        assert response.status_code == 200
        assert mock_pipeline.status == "REJECTED"
        mock_db_session.commit.assert_called()

    def test_reject_calls_crm_log(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        pipeline_id: uuid.UUID,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
    ):
        """
        Rejecting should log a CRM event for audit trail.
        """
        mock_pipeline = create_mock_pipeline(
            pipeline_id, candidate_id, job_id, status="AWAITING_REVIEW"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_pipeline
        mock_db_session.execute.return_value = mock_result

        with patch("backend.api.review.CRM") as MockCRM:
            mock_crm_instance = AsyncMock()
            MockCRM.return_value = mock_crm_instance

            response = test_client.patch(
                f"/api/v1/review/application/{pipeline_id}/reject"
            )

            assert response.status_code == 200
            mock_crm_instance.log.assert_called_once()
            call_args = mock_crm_instance.log.call_args
            assert call_args.args[3] == "REJECTED"  # event_type

    def test_reject_nonexistent_pipeline_returns_404(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
    ):
        """
        Rejecting a non-existent pipeline should return 404.
        """
        fake_pipeline_id = uuid.uuid4()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        response = test_client.patch(
            f"/api/v1/review/application/{fake_pipeline_id}/reject"
        )

        assert response.status_code == 404
        assert "not found" in response.json().get("detail", "").lower()


# ─── Review Queue Tests ───────────────────────────────────────────────────────


class TestReviewQueue:
    """Test GET /api/v1/review/queue endpoint."""

    def test_queue_returns_awaiting_review_pipelines(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        pipeline_id: uuid.UUID,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
    ):
        """
        Review queue should return pipelines with status AWAITING_REVIEW.
        """
        mock_pipeline = create_mock_pipeline(
            pipeline_id, candidate_id, job_id, status="AWAITING_REVIEW"
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_pipeline]
        mock_db_session.execute.return_value = mock_result

        response = test_client.get("/api/v1/review/queue")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["pipeline_id"] == str(pipeline_id)
        assert data[0]["status"] == "AWAITING_REVIEW"

    def test_queue_returns_empty_when_no_awaiting_review(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
    ):
        """
        Review queue should return empty list when no pipelines are awaiting review.
        """
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        response = test_client.get("/api/v1/review/queue")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_queue_returns_multiple_pipelines(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
    ):
        """
        Review queue should return all pipelines awaiting review.
        """
        pipeline1 = create_mock_pipeline(
            uuid.uuid4(), candidate_id, job_id, status="AWAITING_REVIEW"
        )
        pipeline2 = create_mock_pipeline(
            uuid.uuid4(), candidate_id, job_id, status="AWAITING_REVIEW"
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [pipeline1, pipeline2]
        mock_db_session.execute.return_value = mock_result

        response = test_client.get("/api/v1/review/queue")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


# ─── Full Integration Flow Tests ──────────────────────────────────────────────


class TestFullApprovalFlow:
    """
    Integration tests for the complete approval workflow.

    Contract: HYPHA-TESTS.md
    "full integration: create application → approve → verify state transition"
    """

    def test_full_flow_approve_verify_transition(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        pipeline_id: uuid.UUID,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
    ):
        """
        Full integration test: approve → verify transition → verify CRM event.

        Steps:
          1. Mock a pipeline in AWAITING_REVIEW state
          2. POST to approve endpoint
          3. Verify pipeline status is now APPROVED
          4. Verify CRM event was logged
        """
        mock_pipeline = create_mock_pipeline(
            pipeline_id, candidate_id, job_id, status="AWAITING_REVIEW"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_pipeline
        mock_db_session.execute.return_value = mock_result

        with patch("backend.api.review.CRM") as MockCRM:
            mock_crm_instance = AsyncMock()
            MockCRM.return_value = mock_crm_instance

            response = test_client.patch(
                f"/api/v1/review/application/{pipeline_id}/approve"
            )

            # Verify response
            assert response.status_code == 200
            assert response.json()["status"] == "APPROVED"

            # Verify pipeline status was updated
            assert mock_pipeline.status == "APPROVED"

            # Verify CRM event was logged
            mock_crm_instance.log.assert_called_once()
            assert mock_crm_instance.log.call_args.args[3] == "APPROVED_FOR_SUBMISSION"

    def test_approval_is_idempotent_check(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        pipeline_id: uuid.UUID,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
    ):
        """
        Once approved, re-approval should fail with 422.

        This ensures the state machine is respected.
        """
        # First call: pipeline is AWAITING_REVIEW
        mock_pipeline = create_mock_pipeline(
            pipeline_id, candidate_id, job_id, status="AWAITING_REVIEW"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_pipeline
        mock_db_session.execute.return_value = mock_result

        with patch("backend.api.review.CRM") as MockCRM:
            MockCRM.return_value = AsyncMock()
            response1 = test_client.patch(
                f"/api/v1/review/application/{pipeline_id}/approve"
            )
            assert response1.status_code == 200
            assert response1.json()["status"] == "APPROVED"

        # After first approval, pipeline is now APPROVED
        # Second call should fail because status is APPROVED
        assert mock_pipeline.status == "APPROVED"

        # Reset mock to simulate second call with updated status
        mock_result.scalar_one_or_none.return_value = mock_pipeline

        response2 = test_client.patch(
            f"/api/v1/review/application/{pipeline_id}/approve"
        )
        assert response2.status_code == 422

    def test_reject_after_queue_check(
        self,
        test_client: TestClient,
        mock_db_session: AsyncMock,
        pipeline_id: uuid.UUID,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID,
    ):
        """
        Reject flow: pipeline appears in queue, then reject, then verify.
        """
        mock_pipeline = create_mock_pipeline(
            pipeline_id, candidate_id, job_id, status="AWAITING_REVIEW"
        )

        # First: queue returns the pipeline
        mock_queue_result = MagicMock()
        mock_queue_result.scalars.return_value.all.return_value = [mock_pipeline]

        # Then: reject lookup and reject
        mock_single_result = MagicMock()
        mock_single_result.scalar_one_or_none.return_value = mock_pipeline

        # Configure mock to return appropriate result based on call
        call_count = [0]

        def execute_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_queue_result
            return mock_single_result

        mock_db_session.execute.side_effect = execute_side_effect

        # Check queue
        queue_response = test_client.get("/api/v1/review/queue")
        assert queue_response.status_code == 200
        assert len(queue_response.json()) == 1

        # Reject
        with patch("backend.api.review.CRM") as MockCRM:
            MockCRM.return_value = AsyncMock()
            reject_response = test_client.patch(
                f"/api/v1/review/application/{pipeline_id}/reject"
            )

        assert reject_response.status_code == 200
        assert reject_response.json()["status"] == "REJECTED"
        assert mock_pipeline.status == "REJECTED"
