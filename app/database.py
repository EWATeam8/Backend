from pymongo import MongoClient
import os


def get_database():
    try:
        mongo_uri = os.environ.get("MONGODB_URI")
        if not mongo_uri:
            raise ValueError("MONGODB_URI environment variable is not set")

        # Allow invalid certificates (NOT recommended for production)
        client = MongoClient(mongo_uri, tlsAllowInvalidCertificates=True)
        db = client.auto_parts_db
        return db
    except Exception as e:
        print(f"MongoDB connection error: {e}")
        raise


db = get_database()
