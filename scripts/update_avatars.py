import asyncio
from app.core.database import db_manager, connect_to_mongo, close_mongo_connection

CUSTOMER_AVATAR = "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=400&q=80"
PROVIDER_AVATAR = "https://images.unsplash.com/photo-1560250097-0b93528c311a?auto=format&fit=crop&w=400&q=80"

async def main():
    await connect_to_mongo()
    db = db_manager.db

    # Customer
    await db.users.update_many(
        {"email": {"$ne": "provider@example.com"}},
        {"$set": {"avatar_url": CUSTOMER_AVATAR}}
    )
    # Provider
    await db.users.update_many(
        {"email": "provider@example.com"},
        {"$set": {"avatar_url": PROVIDER_AVATAR}}
    )

    users = await db.users.find().to_list(10)
    for u in users:
        print("User:", u.get("email"), "| Role:", u.get("role"), "| Avatar:", u.get("avatar_url"))

    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(main())
