import os
import logging
import ssl
import certifi
from datetime import datetime
from pymongo import MongoClient
from pymongo.server_api import ServerApi
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

        logger.info(f"OpenSSL version: {ssl.OPENSSL_VERSION}")
        logger.info(f"Connecting to MongoDB: {uri[:30]}...{uri[-20:]}")

        try:
            tls_ca = certifi.where()
            self.client = MongoClient(
                uri,
                server_api=ServerApi('1'),
                serverSelectionTimeoutMS=10000,
                tls=True,
                tlsCAFile=tls_ca,
                tlsAllowInvalidCertificates=True,
                tlsAllowInvalidHostnames=True
            )
            self.client.admin.command("ping")
            logger.info("✅ Successfully pinged MongoDB admin database.")
        except Exception as e:
            logger.error("❌ Failed to connect to MongoDB:", exc_info=True)
            return

        default_db = self.client.get_default_database()
        db_name = default_db.name if default_db else "pixeldata"
        self.db = self.client[db_name]
        logger.info(f"📦 Using database: '{self.db.name}'")

        # Collections
        self.profiles = self.db.profiles
        self.autoproxy = self.db.autoproxy
        self.blacklists = self.db.blacklists
        self.switches = self.db.switches
        self.webhooks = self.db.webhooks

        # Indexes
        self.profiles.create_index("user_id", unique=True)
        self.autoproxy.create_index("user_id", unique=True)
        self.blacklists.create_index("guild_id", unique=True)
        self.webhooks.create_index([("channel_id", 1), ("guild_id", 1)], unique=True)
        logger.info("📌 MongoDB collections and indexes initialized.")

    def get_profile(self, user_id: str):
        if not self.profiles:
            logger.warning("MongoDB not connected: get_profile")
            return None
        return self.profiles.find_one({"user_id": user_id})

    def save_profile(self, user_id: str, data: dict) -> None:
        if not self.profiles:
            logger.warning("MongoDB not connected: save_profile")
            return
        data["updated_at"] = datetime.utcnow()
        self.profiles.update_one({"user_id": user_id}, {"$set": data}, upsert=True)

    def delete_profile(self, user_id: str) -> None:
        if not self.profiles or not self.autoproxy:
            logger.warning("MongoDB not connected: delete_profile")
            return
        self.profiles.delete_one({"user_id": user_id})
        self.autoproxy.delete_one({"user_id": user_id})

    def get_autoproxy(self, user_id: str) -> dict:
        if not self.autoproxy:
            logger.warning("MongoDB not connected: get_autoproxy")
            return {"mode": "off"}
        result = self.autoproxy.find_one({"user_id": user_id})
        return result if result else {"mode": "off"}

    def save_autoproxy(self, user_id: str, settings: dict) -> None:
        if not self.autoproxy:
            logger.warning("MongoDB not connected: save_autoproxy")
            return
        settings["updated_at"] = datetime.utcnow()
        self.autoproxy.update_one({"user_id": user_id}, {"$set": settings}, upsert=True)

    def get_blacklist(self, guild_id: str) -> dict:
        if not self.blacklists:
            logger.warning("MongoDB not connected: get_blacklist")
            return {"channels": [], "categories": []}
        result = self.blacklists.find_one({"guild_id": guild_id})
        return result if result else {"channels": [], "categories": []}

    def save_blacklist(self, guild_id: str, data: dict) -> None:
        if not self.blacklists:
            logger.warning("MongoDB not connected: save_blacklist")
            return
        data["updated_at"] = datetime.utcnow()
        self.blacklists.update_one({"guild_id": guild_id}, {"$set": data}, upsert=True)

    def get_webhook(self, channel_id: int, guild_id: int):
        if not self.webhooks:
            logger.warning("MongoDB not connected: get_webhook")
            return None
        return self.webhooks.find_one({"channel_id": channel_id, "guild_id": guild_id})

    def save_webhook(self, channel_id: int, guild_id: int, webhook_id: int, webhook_token: str) -> None:
        if not self.webhooks:
            logger.warning("MongoDB not connected: save_webhook")
            return
        self.webhooks.update_one(
            {"channel_id": channel_id, "guild_id": guild_id},
            {"$set": {
                "webhook_id": webhook_id,
                "webhook_token": webhook_token,
                "updated_at": datetime.utcnow()
            }},
            upsert=True
        )

    def delete_webhook(self, channel_id: int, guild_id: int) -> None:
        if not self.webhooks:
            logger.warning("MongoDB not connected: delete_webhook")
            return
        self.webhooks.delete_one({"channel_id": channel_id, "guild_id": guild_id})

    def record_switch(self, user_id: str, alter_id: str) -> None:
        if not self.switches:
            logger.warning("MongoDB not connected: record_switch")
            return
        self.switches.insert_one({
            "user_id": user_id,
            "alter_id": alter_id,
            "timestamp": datetime.utcnow()
        })

    def get_recent_switches(self, user_id: str, limit: int = 10) -> list:
        if not self.switches:
            logger.warning("MongoDB not connected: get_recent_switches")
            return []
        return list(self.switches.find({"user_id": user_id}).sort("timestamp", -1).limit(limit))

# Global instance
db = MongoDB()
