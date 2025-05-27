# utils/mongodb.py

import os
import logging
import ssl
import certifi
from datetime import datetime
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from pymongo.database import Database
from pymongo.collection import Collection
from typing import Optional, Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MongoDB:
    def __init__(self):
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
        self.profiles: Optional[Collection] = None
        self.autoproxy: Optional[Collection] = None
        self.blacklists: Optional[Collection] = None
        self.switches: Optional[Collection] = None
        self.webhooks: Optional[Collection] = None

    def connect(self) -> None:
        """Connect to MongoDB using the URI from the environment variable."""
        if self.client is not None and self.db is not None:
            return  # already connected

        uri = os.getenv("MONGODB_URI")
        if not uri:
            logger.error("MONGODB_URI environment variable not set")
            return

        logger.info(f"OpenSSL version: {ssl.OPENSSL_VERSION}")
        logger.info(f"Connecting to MongoDB: {uri[:30]}...{uri[-20:]}")

        try:
            tls_ca = certifi.where()
            client = MongoClient(
                uri,
                server_api=ServerApi("1"),
                serverSelectionTimeoutMS=10000,
                tls=True,
                tlsCAFile=tls_ca,
                tlsAllowInvalidCertificates=True,
                tlsAllowInvalidHostnames=True
            )
            client.admin.command("ping")
            logger.info("✅ Successfully pinged MongoDB admin database.")
        except Exception as e:
            logger.error("❌ Failed to connect to MongoDB:", exc_info=True)
            return

        self.client = client
        default_db = client.get_default_database()
        db_name = default_db.name if default_db is not None else "pixeldata"
        self.db = client[db_name]
        logger.info(f"📦 Using database: '{self.db.name}'")

        # Initialize collections
        self.profiles   = self.db["profiles"]
        self.autoproxy  = self.db["autoproxy"]
        self.blacklists = self.db["blacklists"]
        self.switches   = self.db["switches"]
        self.webhooks   = self.db["webhooks"]

        # Ensure indexes
        self.profiles.create_index("user_id",   unique=True)
        self.autoproxy.create_index("user_id",  unique=True)
        self.blacklists.create_index("guild_id",unique=True)
        self.webhooks.create_index([("channel_id",1),("guild_id",1)], unique=True)
        logger.info("📌 MongoDB collections and indexes initialized.")

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        if self.db is None or self.profiles is None:
            logger.warning("Attempted to get_profile but MongoDB is not connected.")
            return None
        return self.profiles.find_one({"user_id": user_id})

    def save_profile(self, user_id: str, data: Dict[str, Any]) -> None:
        if self.db is None or self.profiles is None:
            logger.warning("Attempted to save_profile but MongoDB is not connected.")
            return
        data["updated_at"] = datetime.utcnow().isoformat()
        self.profiles.update_one(
            {"user_id": user_id},
            {"$set": data},
            upsert=True
        )

    def delete_profile(self, user_id: str) -> None:
        if self.db is None or self.profiles is None or self.autoproxy is None:
            logger.warning("Attempted to delete_profile but MongoDB is not connected.")
            return
        self.profiles.delete_one({"user_id": user_id})
        self.autoproxy.delete_one({"user_id": user_id})

    def get_autoproxy(self, key: str) -> Dict[str, Any]:
        if self.db is None or self.autoproxy is None:
            logger.warning("Attempted to get_autoproxy but MongoDB is not connected.")
            return {"enabled": False, "mode": "off"}
        doc = self.autoproxy.find_one({"user_id": key})
        return doc if doc is not None else {"enabled": False, "mode": "off"}

    def save_autoproxy(self, key: str, settings: Dict[str, Any]) -> None:
        if self.db is None or self.autoproxy is None:
            logger.warning("Attempted to save_autoproxy but MongoDB is not connected.")
            return
        settings["updated_at"] = datetime.utcnow().isoformat()
        self.autoproxy.update_one(
            {"user_id": key},
            {"$set": settings},
            upsert=True
        )

    def get_blacklist(self, guild_id: str) -> Dict[str, Any]:
        if self.db is None or self.blacklists is None:
            logger.warning("Attempted to get_blacklist but MongoDB is not connected.")
            return {"channels": [], "categories": []}
        doc = self.blacklists.find_one({"guild_id": guild_id})
        return doc if doc is not None else {"channels": [], "categories": []}

    def save_blacklist(self, guild_id: str, data: Dict[str, Any]) -> None:
        if self.db is None or self.blacklists is None:
            logger.warning("Attempted to save_blacklist but MongoDB is not connected.")
            return
        data["updated_at"] = datetime.utcnow().isoformat()
        self.blacklists.update_one(
            {"guild_id": guild_id},
            {"$set": data},
            upsert=True
        )

    def get_webhook(self, channel_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
        if self.db is None or self.webhooks is None:
            logger.warning("Attempted to get_webhook but MongoDB is not connected.")
            return None
        return self.webhooks.find_one({"channel_id": channel_id, "guild_id": guild_id})

    def save_webhook(self, channel_id: int, guild_id: int, webhook_id: int, webhook_token: str) -> None:
        if self.db is None or self.webhooks is None:
            logger.warning("Attempted to save_webhook but MongoDB is not connected.")
            return
        self.webhooks.update_one(
            {"channel_id": channel_id, "guild_id": guild_id},
            {"$set": {
                "webhook_id": webhook_id,
                "webhook_token": webhook_token,
                "updated_at": datetime.utcnow().isoformat()
            }},
            upsert=True
        )

    def delete_webhook(self, channel_id: int, guild_id: int) -> None:
        if self.db is None or self.webhooks is None:
            logger.warning("Attempted to delete_webhook but MongoDB is not connected.")
            return
        self.webhooks.delete_one({"channel_id": channel_id, "guild_id": guild_id})

    def record_switch(self, user_id: str, alter_id: str) -> None:
        if self.db is None or self.switches is None:
            logger.warning("Attempted to record_switch but MongoDB is not connected.")
            return
        self.switches.insert_one({
            "user_id": user_id,
            "alter_id": alter_id,
            "timestamp": datetime.utcnow().isoformat()
        })

    def get_recent_switches(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        if self.db is None or self.switches is None:
            logger.warning("Attempted to get_recent_switches but MongoDB is not connected.")
            return []
        return list(
            self.switches
                .find({"user_id": user_id})
                .sort("timestamp", -1)
                .limit(limit)
        )

# Global instance
db = MongoDB()
