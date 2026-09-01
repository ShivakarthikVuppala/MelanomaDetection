"""
MongoDB database connection and utility functions.
"""
import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

# Global client instance
client = None
db = None

def get_db():
    """Get the MongoDB database instance."""
    global client, db
    if db is None:
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            logger.warning("MONGO_URI not found in environment variables.")
            return None
            
        try:
            client = AsyncIOMotorClient(mongo_uri, serverSelectionTimeoutMS=5000)
            # Default database name if none specified in URI is 'melanoma_db'
            db = client.get_database("melanoma_db")
            logger.info("Successfully connected to MongoDB.")
        except Exception as e:
            logger.error(f"Could not connect to MongoDB: {e}")
            client = None
            db = None
    return db

async def ping_db():
    """Check database connection."""
    database = get_db()
    if database is not None:
        try:
            await database.command("ping")
            return True
        except Exception:
            return False
    return False
