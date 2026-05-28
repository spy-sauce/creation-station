# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
SSE Event Stream — real-time agent status streaming.

GET /events/stream?channel=agent.status.discovery
GET /events/stream?channel=agent.status.application

Streams Redis pub/sub events to the frontend via Server-Sent Events.
Contract: HYPHA-API-STREAMING.md + NUTRIENTS.md § API_CONTRACTS (iter-4 additions)

SSE format:
  - data: {json}\n\n for each message
  - :ping\n\n every 15s for connection keepalive
  - event: slow_client\ndata: {"dropped": N}\n\n on backpressure

Channel allowlist:
  - agent.status.discovery
  - agent.status.application
"""

from __future__ import annotations

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


# ─── SSE Generator ────────────────────────────────────────────────────────────


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
    # Validate channel against allowlist
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

    return StreamingResponse(
        sse_event_generator(
            redis_client=redis_client,
            channel=channel,
            user_id=str(current_user.id),
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
