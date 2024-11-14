# backend/app/config/database.py
from pymongo import MongoClient, ASCENDING
from redis import Redis
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os

load_dotenv()

# MongoDB Configuration
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "arogo_multiling")

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# MongoDB Connection
mongodb_client = AsyncIOMotorClient(MONGODB_URL)
database = mongodb_client[DATABASE_NAME]

# Collections
consultations_collection = database.consultations
translations_cache = database.translations_cache

# Create indexes
def setup_indexes():
    """Setup database indexes"""
    try:
        # Consultations collection indexes
        consultations_collection.create_index([("consultation_id", ASCENDING)], unique=True)
        consultations_collection.create_index([("user_details.email", ASCENDING)])
        consultations_collection.create_index([("created_at", ASCENDING)])
        consultations_collection.create_index([("status", ASCENDING)])
        consultations_collection.create_index([("user_details.preferred_language", ASCENDING)])
        consultations_collection.create_index([("user_details.interface_language", ASCENDING)])
        
         # Translation cache indexes
        translations_cache.create_index([
            ("source_text", ASCENDING),
            ("source_language", ASCENDING),
            ("target_language", ASCENDING)
        ], unique=True)
        translations_cache.create_index([("created_at", ASCENDING)])

        print("Database indexes created successfully")
    except Exception as e:
        print(f"Error creating indexes: {str(e)}")

# Redis Connection
redis_client = Redis.from_url(REDIS_URL, decode_responses=True)

# Initialize indexes when the application starts
setup_indexes()