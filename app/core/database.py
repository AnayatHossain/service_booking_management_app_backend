import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.core.config import settings

logger = logging.getLogger("service_booking.db")


class DatabaseManager:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None


db_manager = DatabaseManager()


async def connect_to_mongo():
    logger.info("Connecting to MongoDB...")
    db_manager.client = AsyncIOMotorClient(
        settings.mongodb_url,
        serverSelectionTimeoutMS=5000,
        maxPoolSize=50,
        minPoolSize=10,
    )
    db_manager.db = db_manager.client[settings.database_name]

    # Create essential indexes
    try:
        # Users indexes
        await db_manager.db.users.create_index("email", unique=True)
        
        # Appointments indexes
        await db_manager.db.appointments.create_index([("service_id", 1), ("date", 1), ("time_slot", 1)])
        await db_manager.db.appointments.create_index([("user_id", 1), ("status", 1)])
        
        # Services indexes
        await db_manager.db.services.create_index("category")
        await db_manager.db.services.create_index("is_featured")
        
        logger.info("MongoDB connected and indexes verified successfully.")
    except Exception as e:
        logger.warning(f"Index creation note (can ignore if already exists): {e}")


async def close_mongo_connection():
    logger.info("Closing MongoDB connection...")
    if db_manager.client:
        db_manager.client.close()
        logger.info("MongoDB connection closed.")


def get_database() -> AsyncIOMotorDatabase:
    if db_manager.db is None:
        logger.info("Initializing lazy MongoDB connection for serverless/Vercel environment...")
        db_manager.client = AsyncIOMotorClient(
            settings.mongodb_url,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=50,
            minPoolSize=1,
        )
        db_manager.db = db_manager.client[settings.database_name]
    return db_manager.db
