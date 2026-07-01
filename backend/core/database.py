"""MongoDB database connection and GridFS setup."""
import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from typing import Optional
from core.config import settings

logger = logging.getLogger(__name__)


class Database:
    """MongoDB database connection manager."""
    
    client: Optional[AsyncIOMotorClient] = None
    database = None
    gridfs: Optional[AsyncIOMotorGridFSBucket] = None


db = Database()


async def connect_to_mongo():
    """Connect to MongoDB and initialize GridFS."""
    try:
        db.client = AsyncIOMotorClient(settings.MONGODB_URI)
        # Get database name from URI or use default
        database_name = settings.MONGODB_DATABASE_NAME
        db.database = db.client[database_name]
        db.gridfs = AsyncIOMotorGridFSBucket(db.database)
        
        # Test connection
        await db.client.admin.command('ping')
        logger.info(f"Successfully connected to MongoDB database: {database_name}")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_mongo_connection():
    """Close MongoDB connection."""
    try:
        if db.client:
            db.client.close()
            logger.info("Disconnected from MongoDB")
    except Exception as e:
        logger.error(f"Error closing MongoDB connection: {e}")


def get_database():
    """Get database instance."""
    return db.database


def get_gridfs():
    """Get GridFS bucket instance."""
    return db.gridfs
