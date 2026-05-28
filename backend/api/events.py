# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
SSE Event Stream — real-time agent status streaming.

GET /events/stream?channel=agent.status.discovery
GET /events/stream?channel=agent.status.application

Streams Redis pub/sub events to the frontend via Server-Sent Events.
Contract: HYPHA-API-STREAMING.md + NUTRIENTS.md § API_CONTRACTS (iter-4 additions)

SSE format:
  - data: {json}\\n\\n for each message
  - :ping\\n\\n every 15s for connection keepalive
  - event: slow_client\\ndata: {"dropped": N}\\n\\n on backpressure

Channel allowlist:
  - agent.status.discovery
  - agent.status.application

Exports:
  - router: FastAPI APIRouter with /stream endpoint
  - SSESubscriber: Redis pub/sub subscriber class with channel allowlist
  - ALLOWED_CHANNELS: Frozenset of allowed channel names
"""

from __future__ import annotations

__all__ = [
    "router",
    "SSESubscriber",
    "ALLOWED_CHANNELS",
    "HEARTBEAT_INTERVAL_SECONDS",
    "MAX_QUEUE_SIZE",
]

import asyncio
from typing import AsyncGenerator

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.api.auth import get_current_user
from backend.database import get_redis
from backend.models.auth import User
from backend.observability.events import PubSubChannel

logger = structlog.get_logger(__name__)

router = APIRouter()

# ─── Constants ────────────────────────────────────────────────────────────────

# Allowed SSE channels (frozen contract from NUTRIENTS.md)
ALLOWED_CHANNELS: frozenset[str] = frozenset({
    PubSubChannel.DISCOVERY.value,    # agent.status.discovery
    PubSubChannel.APPLICATION.value,  # agent.status.application
})

# Heartbeat interval in seconds
HEARTBEAT_INTERVAL_SECONDS: float = 15.0

# Backpressure threshold — drop oldest messages if queue exceeds this
MAX_QUEUE_SIZE: int = 100


# ─── SSE Subscriber ───────────────────────────────────────────────────────────


class SSESubscriber:
    """
    Redis pub/sub subscriber with channel allowlist for SSE streaming.

    This class encapsulates the Redis subscription lifecycle:
      - Validates channels against the frozen allowlist
      - Subscribes to the Redis pub/sub channel
      - Buffers messages in an async queue with backpressure handling
      - Provides an async generator for SSE frame emission

    Contract: NUTRIENTS.md § C. Symbol Ownership Matrix (iter-4 additions)

    Attributes:
        redis_client: Async Redis client for pub/sub operations
        channel: Validated Redis channel to subscribe to
        user_id: Authenticated user ID for logging context
        queue: Internal message buffer with backpressure handling
        dropped_count: Counter for messages dropped due to slow client

    Example:
        >>> subscriber = SSESubscriber(redis_client, "agent.status.discovery", user_id)
        >>> async for frame in subscriber.stream():
        ...     yield frame
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        channel: str,
        user_id: str,
    ) -> None:
        """
        Initialize an SSE subscriber for a Redis pub/sub channel.

        Args:
            redis_client: Async Redis client for pub/sub subscription
            channel: Redis channel to subscribe to (must be in ALLOWED_CHANNELS)
            user_id: Authenticated user ID (for logging context)

        Raises:
            ValueError: If channel is not in the allowlist
        """
        if channel not in ALLOWED_CHANNELS:
            allowed_list = ", ".join(sorted(ALLOWED_CHANNELS))
            raise ValueError(f"Invalid channel. Allowed: {allowed_list}")

        self.redis_client = redis_client
        self.channel = channel
        self.user_id = user_id
        self._pubsub: aioredis.client.PubSub | None = None
        self._message_queue: asyncio.Queue[str] = asyncio.Queue()
        self._dropped_count: int = 0
        self._reader_task: asyncio.Task | None = None

    async def _reader(self) -> None:
        """
        Background task that reads from Redis pub/sub and pushes to queue.

        Handles backpressure by dropping oldest messages when queue is full.
        This prevents memory exhaustion when clients fall behind.
        """
        try:
            self._pubsub = self.redis_client.pubsub()
            await self._pubsub.subscribe(self.channel)

            async for message in self._pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]

                    # Backpressure: drop oldest messages if queue is full
                    while self._message_queue.qsize() >= MAX_QUEUE_SIZE:
                        try:
                            self._message_queue.get_nowait()
                            self._dropped_count += 1
                        except asyncio.QueueEmpty:
                            break

                    await self._message_queue.put(data)

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(
                "sse.subscriber_reader_error",
                channel=self.channel,
                user_id=self.user_id,
                error=str(exc),
            )

    async def stream(self) -> AsyncGenerator[str, None]:
        """
        Async generator that yields SSE frames from the subscription.

        Yields:
            SSE-formatted strings:
              - data: {json}\\n\\n for each message
              - :ping\\n\\n every 15s for keepalive
              - event: slow_client\\ndata: {"dropped": N}\\n\\n on backpressure

        The generator handles cleanup on cancellation or error, ensuring
        the Redis subscription is properly closed.
        """
        logger.info(
            "sse.subscriber_started",
            channel=self.channel,
            user_id=self.user_id,
        )

        # Start the background reader
        self._reader_task = asyncio.create_task(self._reader())

        try:
            while True:
                try:
                    # Wait for message with timeout (for heartbeat)
                    message = await asyncio.wait_for(
                        self._message_queue.get(),
                        timeout=HEARTBEAT_INTERVAL_SECONDS,
                    )

                    # Emit slow_client warning if messages were dropped
                    if self._dropped_count > 0:
                        yield f"event: slow_client\ndata: {{\"dropped\": {self._dropped_count}}}\n\n"
                        logger.warning(
                            "sse.slow_client",
                            channel=self.channel,
                            user_id=self.user_id,
                            dropped=self._dropped_count,
                        )
                        self._dropped_count = 0

                    # Emit the actual message
                    yield f"data: {message}\n\n"

                except asyncio.TimeoutError:
                    # No message within heartbeat interval — send keepalive
                    yield ":ping\n\n"

        except asyncio.CancelledError:
            logger.info(
                "sse.subscriber_cancelled",
                channel=self.channel,
                user_id=self.user_id,
            )
        except Exception as exc:
            logger.error(
                "sse.subscriber_error",
                channel=self.channel,
                user_id=self.user_id,
                error=str(exc),
            )
        finally:
            await self._cleanup()

    async def _cleanup(self) -> None:
        """Clean up resources: cancel reader task and close subscription."""
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass

        if self._pubsub:
            try:
                await self._pubsub.unsubscribe(self.channel)
                await self._pubsub.close()
            except Exception as exc:
                logger.warning(
                    "sse.subscriber_cleanup_error",
                    channel=self.channel,
                    error=str(exc),
                )

        logger.info(
            "sse.subscriber_closed",
            channel=self.channel,
            user_id=self.user_id,
        )


# ─── SSE Generator (legacy wrapper) ───────────────────────────────────────────


async def sse_event_generator(
    redis_client: aioredis.Redis,
    channel: str,
    user_id: str,
) -> AsyncGenerator[str, None]:
    """
    Generate SSE frames from Redis pub/sub messages.

    Args:
        redis_client: Async Redis client for pub/sub subscription
        channel: Redis channel to subscribe to
        user_id: Authenticated user ID (for logging)

    Yields:
        SSE-formatted strings (data: {json}\n\n or :ping\n\n)

    Contract:
        - Each message yields: data: {json}\n\n
        - Heartbeat every 15s: :ping\n\n
        - Backpressure: if queue > 100, drop oldest and emit slow_client event
    """
    pubsub = redis_client.pubsub()
    message_queue: asyncio.Queue[str] = asyncio.Queue()
    dropped_count: int = 0

    logger.info(
        "sse.connection_started",
        channel=channel,
        user_id=user_id,
    )

    async def reader_task() -> None:
        """
        Background task that reads from Redis pub/sub and pushes to queue.

        Handles backpressure by dropping oldest messages when queue is full.
        """
        nonlocal dropped_count

        try:
            await pubsub.subscribe(channel)
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]

                    # Backpressure check
                    while message_queue.qsize() >= MAX_QUEUE_SIZE:
                        try:
                            message_queue.get_nowait()
                            dropped_count += 1
                        except asyncio.QueueEmpty:
                            break

                    await message_queue.put(data)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error(
                "sse.reader_error",
                channel=channel,
                user_id=user_id,
                error=str(exc),
            )

    # Start the background reader
    reader = asyncio.create_task(reader_task())

    try:
        while True:
            try:
                # Wait for message with timeout (for heartbeat)
                message = await asyncio.wait_for(
                    message_queue.get(),
                    timeout=HEARTBEAT_INTERVAL_SECONDS,
                )

                # Emit slow_client warning if messages were dropped
                if dropped_count > 0:
                    yield f"event: slow_client\ndata: {{\"dropped\": {dropped_count}}}\n\n"
                    logger.warning(
                        "sse.slow_client",
                        channel=channel,
                        user_id=user_id,
                        dropped=dropped_count,
                    )
                    dropped_count = 0

                # Emit the actual message
                yield f"data: {message}\n\n"

            except asyncio.TimeoutError:
                # No message within heartbeat interval — send keepalive
                yield ":ping\n\n"

    except asyncio.CancelledError:
        logger.info(
            "sse.connection_cancelled",
            channel=channel,
            user_id=user_id,
        )
    except Exception as exc:
        logger.error(
            "sse.generator_error",
            channel=channel,
            user_id=user_id,
            error=str(exc),
        )
    finally:
        # Cleanup: cancel reader and unsubscribe
        reader.cancel()
        try:
            await reader
        except asyncio.CancelledError:
            pass

        try:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
        except Exception as exc:
            logger.warning(
                "sse.cleanup_error",
                channel=channel,
                error=str(exc),
            )

        logger.info(
            "sse.connection_closed",
            channel=channel,
            user_id=user_id,
        )


# ─── Endpoint ─────────────────────────────────────────────────────────────────


@router.get("/stream")
async def event_stream(
    channel: str = Query(
        ...,
        description="Redis pub/sub channel to subscribe to",
        examples=["agent.status.discovery", "agent.status.application"],
    ),
    current_user: User = Depends(get_current_user),
    redis_client: aioredis.Redis = Depends(get_redis),
) -> StreamingResponse:
    """
    Stream real-time agent status events via Server-Sent Events.

    Args:
        channel: Redis pub/sub channel to subscribe to.
            Allowed: agent.status.discovery, agent.status.application

    Returns:
        StreamingResponse with Content-Type: text/event-stream

    Raises:
        400: Invalid channel (not in allowlist)
        401: Not authenticated (missing or invalid JWT)

    Contract: NUTRIENTS.md § API_CONTRACTS → GET /events/stream
    """
    # Validate channel against allowlist (also validated in SSESubscriber)
    if channel not in ALLOWED_CHANNELS:
        allowed_list = ", ".join(sorted(ALLOWED_CHANNELS))
        raise HTTPException(
            status_code=400,
            detail=f"Invalid channel. Allowed: {allowed_list}",
        )

    logger.info(
        "sse.stream_requested",
        channel=channel,
        user_id=str(current_user.id),
    )

    # Create subscriber with channel allowlist validation
    subscriber = SSESubscriber(
        redis_client=redis_client,
        channel=channel,
        user_id=str(current_user.id),
    )

    return StreamingResponse(
        subscriber.stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
