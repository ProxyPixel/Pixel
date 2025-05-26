import os
from typing import Optional, Dict, Any, List
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from datetime import datetime
import logging
import ssl

# Set up logging
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
        """Connect to MongoDB using URI from environment variable."""
        if self.client is not None:
            return

        uri = os.getenv("MONGODB_URI")
        if not uri:
            raise ValueError("MONGODB_URI environment variable not set")

        try:
            # Configure SSL context for better compatibility
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Create client with SSL configuration
            self.client = MongoClient(
                uri,
                tls=True,  # Explicitly enable TLS
                tlsCAFile=ssl.get_default_verify_paths().cafile, # Use default CA file
                tlsAllowInvalidCertificates=True, # Temporarily allow for testing
                tlsAllowInvalidHostnames=True, # Temporarily allow for testing
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
                maxPoolSize=10,
                retryWrites=True
            )
            
            # Test the connection
            self.client.admin.command('ping')
            
            self.db = self.client.pixel_bot
            
            # Initialize collections
            self.profiles = self.db.profiles
            self.autoproxy = self.db.autoproxy
            self.blacklists = self.db.blacklists
            self.switches = self.db.switches
            self.webhooks = self.db.webhooks

            # Create indexes
            self.profiles.create_index("user_id", unique=True)
            self.autoproxy.create_index("user_id", unique=True)
            self.blacklists.create_index("guild_id", unique=True)
            self.webhooks.create_index([("channel_id", 1), ("guild_id", 1)], unique=True)

            logger.info("Connected to MongoDB successfully")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user's profile data."""
        self.connect()
        return self.profiles.find_one({"user_id": user_id})

    def save_profile(self, user_id: str, data: Dict[str, Any]) -> None:
        """Save a user's profile data."""
        self.connect()
        data["updated_at"] = datetime.utcnow()
        self.profiles.update_one(
            {"user_id": user_id},
            {"$set": data},
            upsert=True
        )

    def delete_profile(self, user_id: str) -> None:
        """Delete a user's profile."""
        self.connect()
        self.profiles.delete_one({"user_id": user_id})
        self.autoproxy.delete_one({"user_id": user_id})

    def get_autoproxy(self, user_id: str) -> Dict[str, Any]:
        """Get a user's autoproxy settings."""
        self.connect()
        settings = self.autoproxy.find_one({"user_id": user_id})
        return settings if settings else {"mode": "off"}

    def save_autoproxy(self, user_id: str, settings: Dict[str, Any]) -> None:
        """Save a user's autoproxy settings."""
        self.connect()
        settings["updated_at"] = datetime.utcnow()
        self.autoproxy.update_one(
            {"user_id": user_id},
            {"$set": settings},
            upsert=True
        )

    def get_blacklist(self, guild_id: str) -> Dict[str, Any]:
        """Get a guild's blacklist settings."""
        self.connect()
        blacklist = self.blacklists.find_one({"guild_id": guild_id})
        return blacklist if blacklist else {"channels": [], "categories": []}

    def save_blacklist(self, guild_id: str, data: Dict[str, Any]) -> None:
        """Save a guild's blacklist settings."""
        self.connect()
        data["updated_at"] = datetime.utcnow()
        self.blacklists.update_one(
            {"guild_id": guild_id},
            {"$set": data},
            upsert=True
        )

    def get_webhook(self, channel_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get webhook info for a channel."""
        self.connect()
        return self.webhooks.find_one({
            "channel_id": channel_id,
            "guild_id": guild_id
        })

    def save_webhook(self, channel_id: int, guild_id: int, webhook_id: int, webhook_token: str) -> None:
        """Save webhook info for a channel."""
        self.connect()
        self.webhooks.update_one(
            {
                "channel_id": channel_id,
                "guild_id": guild_id
            },
            {
                "$set": {
                    "webhook_id": webhook_id,
                    "webhook_token": webhook_token,
                    "updated_at": datetime.utcnow()
                }
            },
            upsert=True
        )

    def delete_webhook(self, channel_id: int, guild_id: int) -> None:
        """Delete webhook info for a channel."""
        self.connect()
        self.webhooks.delete_one({
            "channel_id": channel_id,
            "guild_id": guild_id
        })

    def record_switch(self, user_id: str, alter_id: str) -> None:
        """Record a switch event."""
        self.connect()
        self.switches.insert_one({
            "user_id": user_id,
            "alter_id": alter_id,
            "timestamp": datetime.utcnow()
        })

    def get_recent_switches(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent switches for a user."""
        self.connect()
        return list(self.switches.find(
            {"user_id": user_id},
            sort=[("timestamp", -1)],
            limit=limit
        ))

# Create global database instance
db = MongoDB() 