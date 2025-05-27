"""
Updated: 2025-05-26 Still not connecting.
"""
import os
import logging
import ssl
import certifi
from datetime import datetime
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MongoDB:
    def __init__(self):
        self.client: MongoClient = None
        self.db: Database = None
        self.profiles: Collection = None
        self.autoproxy: Collection = None
        self.blacklists: Collection = None
        self.switches: Collection = None
        self.webhooks: Collection = None

    def connect(self) -> None:
        """Connect to MongoDB using the URI from the environment variable."""
        uri = os.getenv("MONGODB_URI")
        if not uri:
            logger.error("MONGODB_URI environment variable not set")
            return

        # Log OpenSSL and URI preview
        logger.info(f"OpenSSL version: {ssl.OPENSSL_VERSION}")
        logger.info(f"Connecting to MongoDB: {uri[:30]}...{uri[-20:]}")

        try:
            # Insecure fallback: trust certifi CA but allow invalid certs/hostnames
            tls_ca = certifi.where()
            client = MongoClient(
                uri,
                serverSelectionTimeoutMS=10000,
                tls=True,
                tlsCAFile=tls_ca,
                tlsAllowInvalidCertificates=True,
                tlsAllowInvalidHostnames=True
            )
            # Verify connection
            client.admin.command("ping")
            logger.info("Successfully pinged MongoDB admin database (insecure mode).")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}", exc_info=True)
            return

        # Assign client and select database
        self.client = client
        default_db = client.get_default_database()
        db_name = default_db.name if default_db else "pixeldata"
        self.db = client[db_name]
        logger.info(f"Using database: '{self.db.name}'")

        # Initialize collections
        self.profiles = self.db.profiles
        self.autoproxy = self.db.autoproxy
        self.blacklists = self.db.blacklists
        self.switches = self.db.switches
        self.webhooks = self.db.webhooks

        # Ensure indexes
        self.profiles.create_index("user_id", unique=True)
        self.autoproxy.create_index("user_id", unique=True)
        self.blacklists.create_index("guild_id", unique=True)
        self.webhooks.create_index([("channel_id", 1), ("guild_id", 1)], unique=True)
        logger.info("MongoDB collections and indexes initialized.")

    def get_profile(self, user_id: str):
        if not self.db or not self.profiles:
            logger.warning("Attempted to get_profile but MongoDB is not connected.")
            return None
        return self.profiles.find_one({"user_id": user_id})

    def save_profile(self, user_id: str, data: dict) -> None:
        if not self.db or not self.profiles:
            logger.warning("Attempted to save_profile but MongoDB is not connected.")
            return
        data["updated_at"] = datetime.utcnow()
        self.profiles.update_one({"user_id": user_id}, {"$set": data}, upsert=True)

    def delete_profile(self, user_id: str) -> None:
        if not self.db or not self.profiles:
            logger.warning("Attempted to delete_profile but MongoDB is not connected.")
            return
        self.profiles.delete_one({"user_id": user_id})
        self.autoproxy.delete_one({"user_id": user_id})

    def get_autoproxy(self, user_id: str) -> dict:
        if not self.db or not self.autoproxy:
            logger.warning("Attempted to get_autoproxy but MongoDB is not connected.")
            return {"mode": "off"}
        settings = self.autoproxy.find_one({"user_id": user_id})
        return settings if settings else {"mode": "off"}

    def save_autoproxy(self, user_id: str, settings: dict) -> None:
        if not self.db or not self.autoproxy:
            logger.warning("Attempted to save_autoproxy but MongoDB is not connected.")
            return
        settings["updated_at"] = datetime.utcnow()
        self.autoproxy.update_one({"user_id": user_id}, {"$set": settings}, upsert=True)

    def get_blacklist(self, guild_id: str) -> dict:
        if not self.db or not self.blacklists:
            logger.warning("Attempted to get_blacklist but MongoDB is not connected.")
            return {"channels": [], "categories": []}
        blacklist = self.blacklists.find_one({"guild_id": guild_id})
        return blacklist if blacklist else {"channels": [], "categories": []}

    def save_blacklist(self, guild_id: str, data: dict) -> None:
        if not self.db or not self.blacklists:
            logger.warning("Attempted to save_blacklist but MongoDB is not connected.")
            return
        data["updated_at"] = datetime.utcnow()
        self.blacklists.update_one({"guild_id": guild_id}, {"$set": data}, upsert=True)

    def get_webhook(self, channel_id: int, guild_id: int):
        if not self.db or not self.webhooks:
            logger.warning("Attempted to get_webhook but MongoDB is not connected.")
            return None
        return self.webhooks.find_one({"channel_id": channel_id, "guild_id": guild_id})

    def save_webhook(self, channel_id: int, guild_id: int, webhook_id: int, webhook_token: str) -> None:
        if not self.db or not self.webhooks:
            logger.warning("Attempted to save_webhook but MongoDB is not connected.")
            return
        self.webhooks.update_one({"channel_id": channel_id, "guild_id": guild_id},
                                 {"$set": {"webhook_id": webhook_id, "webhook_token": webhook_token, "updated_at": datetime.utcnow()}},
                                 upsert=True)

    def delete_webhook(self, channel_id: int, guild_id: int) -> None:
        if not self.db or not self.webhooks:
            logger.warning("Attempted to delete_webhook but MongoDB is not connected.")
            return
        self.webhooks.delete_one({"channel_id": channel_id, "guild_id": guild_id})

    def record_switch(self, user_id: str, alter_id: str) -> None:
        if not self.db or not self.switches:
            logger.warning("Attempted to record_switch but MongoDB is not connected.")
            return
        self.switches.insert_one({"user_id": user_id, "alter_id": alter_id, "timestamp": datetime.utcnow()})

    def get_recent_switches(self, user_id: str, limit: int = 10) -> list:
        if not self.db or not self.switches:
            logger.warning("Attempted to get_recent_switches but MongoDB is not connected.")
            return []
        return list(self.switches.find({"user_id": user_id}).sort("timestamp", -1).limit(limit))

# Instantiate global database client
db = MongoDB()
