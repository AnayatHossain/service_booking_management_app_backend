import asyncio
import os
import sys
from datetime import datetime, timezone

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.core.security import hash_password

INITIAL_SERVICES = [
    {
        "name": "Full House Deep Cleaning",
        "description": "Comprehensive top-to-bottom deep sanitization for 2-3 bedroom apartments or houses. Includes kitchen degreasing, bathroom scrubbing, floor polishing, and window cleaning.",
        "category": "Home Cleaning",
        "price": 120.00,
        "duration_minutes": 180,
        "image_url": "https://images.unsplash.com/photo-1581578731548-c64695cc6952?auto=format&fit=crop&w=800&q=80",
        "is_featured": True,
        "rating": 4.9,
        "total_reviews": 128,
        "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "time_slots": ["09:00 AM", "11:00 AM", "02:00 PM", "04:00 PM"],
        "is_active": True
    },
    {
        "name": "Luxury Aromatherapy Spa & Massage",
        "description": "Relaxing full-body hot stone and aromatherapy essential oil massage designed to melt away muscle fatigue, stress, and restore physical balance.",
        "category": "Spa & Wellness",
        "price": 85.00,
        "duration_minutes": 90,
        "image_url": "https://images.unsplash.com/photo-1544161515-4ab6ce6db874?auto=format&fit=crop&w=800&q=80",
        "is_featured": True,
        "rating": 4.95,
        "total_reviews": 210,
        "available_days": ["Monday", "Wednesday", "Friday", "Saturday", "Sunday"],
        "time_slots": ["10:00 AM", "12:00 PM", "02:00 PM", "04:00 PM", "06:00 PM"],
        "is_active": True
    },
    {
        "name": "Air Conditioner Master Servicing",
        "description": "Deep chemical wash for split and inverter AC units, gas pressure check, filter restoration, and complete cooling performance optimization.",
        "category": "Appliance Repair",
        "price": 45.00,
        "duration_minutes": 60,
        "image_url": "https://images.unsplash.com/photo-1621905251189-08b45d6a269e?auto=format&fit=crop&w=800&q=80",
        "is_featured": True,
        "rating": 4.8,
        "total_reviews": 85,
        "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "time_slots": ["09:00 AM", "11:00 AM", "01:00 PM", "03:00 PM", "05:00 PM"],
        "is_active": True
    },
    {
        "name": "Executive Haircut & Beard Styling",
        "description": "Precision haircut, hot towel therapy, beard shaping, facial massage, and premium organic hair treatment by master stylists.",
        "category": "Beauty & Salon",
        "price": 35.00,
        "duration_minutes": 45,
        "image_url": "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=800&q=80",
        "is_featured": True,
        "rating": 4.85,
        "total_reviews": 164,
        "available_days": ["Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "time_slots": ["10:00 AM", "11:00 AM", "02:00 PM", "03:00 PM", "05:00 PM"],
        "is_active": True
    },
    {
        "name": "Car Wash & Ceramic Paint Detailing",
        "description": "Complete exterior foam hand wash, interior vacuuming, leather conditioning, rim polishing, and hydrophobic ceramic spray sealant application.",
        "category": "Automotive",
        "price": 75.00,
        "duration_minutes": 120,
        "image_url": "https://images.unsplash.com/photo-1601362840469-51e4d8d58785?auto=format&fit=crop&w=800&q=80",
        "is_featured": False,
        "rating": 4.75,
        "total_reviews": 92,
        "available_days": ["Monday", "Tuesday", "Thursday", "Friday", "Saturday"],
        "time_slots": ["09:00 AM", "11:30 AM", "02:00 PM", "04:30 PM"],
        "is_active": True
    },
    {
        "name": "Laptop & PC Hardware Diagnostics & Tuning",
        "description": "Complete hardware diagnostic, thermal paste re-application, dust extraction, operating system tune-up, and malware removal.",
        "category": "Tech & Electronics",
        "price": 50.00,
        "duration_minutes": 60,
        "image_url": "https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?auto=format&fit=crop&w=800&q=80",
        "is_featured": False,
        "rating": 4.7,
        "total_reviews": 54,
        "available_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        "time_slots": ["10:00 AM", "01:00 PM", "03:00 PM", "05:00 PM"],
        "is_active": True
    }
]


async def seed():
    print(f"Connecting to MongoDB at: {settings.mongodb_url.split('@')[-1]}")
    client = AsyncIOMotorClient(settings.mongodb_url)
    db = client[settings.database_name]

    # 1. Seed Services
    print("Checking services collection...")
    existing_count = await db.services.count_documents({})
    if existing_count == 0:
        print(f"Seeding {len(INITIAL_SERVICES)} initial services...")
        now = datetime.now(timezone.utc).isoformat()
        for s in INITIAL_SERVICES:
            s["created_at"] = now
            s["updated_at"] = now
        await db.services.insert_many(INITIAL_SERVICES)
        print("Services seeded successfully!")
    else:
        print(f"Found {existing_count} existing services. Updating catalog...")
        for s in INITIAL_SERVICES:
            await db.services.update_one(
                {"name": s["name"]},
                {"$set": s},
                upsert=True
            )
        print("Catalog synchronized successfully!")

    # 2. Seed Demo Test User
    demo_email = "testuser@example.com"
    existing_user = await db.users.find_one({"email": demo_email})
    if not existing_user:
        print(f"Creating demo test user: {demo_email}")
        now = datetime.now(timezone.utc).isoformat()
        demo_user = {
            "name": "Alex Johnson",
            "email": demo_email,
            "password": hash_password("password123"),
            "phone": "+1 (555) 234-5678",
            "role": "customer",
            "avatar_url": "https://api.dicebear.com/7.x/initials/svg?seed=AlexJohnson",
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }
        await db.users.insert_one(demo_user)
        print("Demo user created: testuser@example.com / password123")
    else:
        print(f"Demo user already exists: {demo_email}")

    client.close()
    print("Seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed())
