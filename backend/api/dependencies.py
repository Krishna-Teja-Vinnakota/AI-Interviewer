"""Shared dependencies for API routes."""
from core.database import get_database


async def get_db():
    """Dependency to get database instance."""
    return get_database()
