# Copyright 2026 VibeSpace LLC
# Licensed under the Apache License, Version 2.0

"""
Auto-seed the first admin user on startup.

Creates Sean Young (Space Cowboy #9) as the default admin if no users exist.
This lets you skip manual account creation during MVP development.
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import AsyncSessionLocal
from backend.models.auth import User
from backend.logging_config import logger


SEED_EMAIL = "spy@seanyoung.biz"
SEED_NAME = "Sean Young"


async def seed_admin_user() -> None:
    """Create the default admin user if the users table is empty."""
    async with AsyncSessionLocal() as session:
        # Only seed if no users exist at all
        result = await session.execute(select(func.count()).select_from(User))
        user_count = result.scalar_one()

        if user_count > 0:
            logger.info("seed.skip", reason="users already exist", count=user_count)
            return

        admin = User(
            email=SEED_EMAIL,
            name=SEED_NAME,
            is_active=True,
            is_onboarded=False,  # Will go through onboarding to upload resume
        )
        session.add(admin)
        await session.commit()

        logger.info(
            "seed.admin_created",
            email=SEED_EMAIL,
            name=SEED_NAME,
            user_id=str(admin.id),
        )
