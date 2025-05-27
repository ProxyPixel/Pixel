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
            # Already connected or initialization attempted
            if self.db is not None:
                return # Successfully connected previously
            # If db is None, connection previously failed, so we might want to retry
            # For now, let's prevent retrying if client object exists but failed
            # This matches the original logic of only trying to create MongoClient once.
            # Consider a more robust retry mechanism if needed.
            pass

        uri = os.getenv("MONGODB_URI")
        if not uri:
            logger.error("MONGODB_URI environment variable not set")
            # Raise an error or handle as appropriate for your application
            # For now, this will cause self.db and collections to remain None
            return

        try:
            logger.info(f"Attempting to connect to MongoDB with URI: {uri[:uri.find(':')+3]}...{uri[-20:]}")
            
            # Check if we're running on Render
            is_render = os.getenv("RENDER") is not None or os.getenv("RENDER_SERVICE_ID") is not None
            logger.info(f"Running on Render: {is_render}")

            # Try multiple connection configurations for better compatibility
            connection_configs = [
                # Configuration 1: Render-optimized with disabled SSL verification
                {
                    "tls": True,
                    "tlsAllowInvalidCertificates": True,
                    "tlsAllowInvalidHostnames": True,
                    "tlsInsecure": True,
                    "serverSelectionTimeoutMS": 10000,  # Shorter timeout for Render
                    "connectTimeoutMS": 10000,
                    "socketTimeoutMS": 10000,
                    "maxPoolSize": 10,  # Smaller pool for free tier
                    "retryWrites": True,
                    "retryReads": True,
                    "directConnection": False
                },
                # Configuration 2: Standard TLS with cert verification disabled (for Render)
                {
                    "tls": True,
                    "tlsAllowInvalidCertificates": True,
                    "tlsAllowInvalidHostnames": True,
                    "serverSelectionTimeoutMS": 30000,
                    "connectTimeoutMS": 30000,
                    "socketTimeoutMS": 30000,
                    "maxPoolSize": 20,
                    "retryWrites": True,
                    "retryReads": True
                },
                # Configuration 3: TLS with insecure settings for problematic environments
                {
                    "tls": True,
                    "tlsInsecure": True,
                    "serverSelectionTimeoutMS": 30000,
                    "connectTimeoutMS": 30000,
                    "socketTimeoutMS": 30000,
                    "maxPoolSize": 20,
                    "retryWrites": True,
                    "retryReads": True
                },
                # Configuration 4: Legacy SSL approach
                {
                    "ssl": True,
                    "ssl_cert_reqs": ssl.CERT_NONE,
                    "serverSelectionTimeoutMS": 30000,
                    "connectTimeoutMS": 30000,
                    "socketTimeoutMS": 30000,
                    "maxPoolSize": 20,
                    "retryWrites": True,
                    "retryReads": True
                },
                # Configuration 5: Minimal TLS for maximum compatibility
                {
                    "tls": True,
                    "tlsCAFile": None,
                    "serverSelectionTimeoutMS": 30000,
                    "connectTimeoutMS": 30000,
                    "socketTimeoutMS": 30000,
                    "maxPoolSize": 20,
                    "retryWrites": True,
                    "retryReads": True
                }
            ]

            last_error = None
            for i, config in enumerate(connection_configs, 1):
                try:
                    logger.info(f"Trying MongoDB connection configuration {i}/{len(connection_configs)}")
                    
                    # Handle legacy SSL configuration separately to avoid parameter errors
                    if config.get("ssl") and "ssl_cert_reqs" in config:
                        # Create a copy without the problematic parameter for newer PyMongo versions
                        config_copy = config.copy()
                        try:
                            self.client = MongoClient(uri, **config_copy)
                        except Exception as ssl_error:
                            # If ssl_cert_reqs fails, try without it
                            logger.warning(f"SSL cert parameter failed, trying without: {ssl_error}")
                            config_copy.pop("ssl_cert_reqs", None)
                            self.client = MongoClient(uri, **config_copy)
                    else:
                        self.client = MongoClient(uri, **config)
                    
                    # Test the connection by pinging the admin database
                    self.client.admin.command('ping')
                    logger.info("Successfully pinged MongoDB admin database.")
                    break
                    
                except Exception as e:
                    last_error = e
                    logger.warning(f"Configuration {i} failed: {str(e)}")
                    self.client = None
                    continue
            
            if self.client is None:
                raise last_error or Exception("All connection configurations failed")
            
            self.db = self.client.pixel_bot
            logger.info(f"Connected to database: {self.db.name}")
            
            # Initialize collections
            self.profiles = self.db.profiles
            self.autoproxy = self.db.autoproxy
            self.blacklists = self.db.blacklists
            self.switches = self.db.switches
            self.webhooks = self.db.webhooks
            logger.info("MongoDB collections initialized.")

            # Create indexes (idempotent operation)
            self.profiles.create_index("user_id", unique=True)
            self.autoproxy.create_index("user_id", unique=True)
            self.blacklists.create_index("guild_id", unique=True)
            self.webhooks.create_index([("channel_id", 1), ("guild_id", 1)], unique=True)
            logger.info("MongoDB indexes ensured.")

            logger.info("Successfully connected to MongoDB and initialized collections.")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB or initialize: {e}", exc_info=True)
            # Ensure client is reset if connection fails, to allow potential retries if connect() is called again
            self.client = None 
            self.db = None
            # Collections will remain None
            # Do not raise here if we want the bot to start up despite DB issues
            # The calling code (e.g., in cogs) should handle db being None

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user's profile data."""
        if self.db is None or self.profiles is None: 
            logger.warning("Attempted to get_profile but MongoDB is not connected.")
            return None
        return self.profiles.find_one({"user_id": user_id})

    def save_profile(self, user_id: str, data: Dict[str, Any]) -> None:
        """Save a user's profile data."""
        if self.db is None or self.profiles is None: 
            logger.warning("Attempted to save_profile but MongoDB is not connected.")
            return
        data["updated_at"] = datetime.utcnow()
        self.profiles.update_one(
            {"user_id": user_id},
            {"$set": data},
            upsert=True
        )

    def delete_profile(self, user_id: str) -> None:
        """Delete a user's profile."""
        if self.db is None or self.profiles is None or self.autoproxy is None: 
            logger.warning("Attempted to delete_profile but MongoDB is not connected.")
            return
        self.profiles.delete_one({"user_id": user_id})
        self.autoproxy.delete_one({"user_id": user_id})

    def get_autoproxy(self, user_id: str) -> Dict[str, Any]:
        """Get a user's autoproxy settings."""
        if self.db is None or self.autoproxy is None: 
            logger.warning("Attempted to get_autoproxy but MongoDB is not connected.")
            return {"mode": "off"} # Return default if not connected
        settings = self.autoproxy.find_one({"user_id": user_id})
        return settings if settings else {"mode": "off"}

    def save_autoproxy(self, user_id: str, settings: Dict[str, Any]) -> None:
        """Save a user's autoproxy settings."""
        if self.db is None or self.autoproxy is None: 
            logger.warning("Attempted to save_autoproxy but MongoDB is not connected.")
            return
        settings["updated_at"] = datetime.utcnow()
        self.autoproxy.update_one(
            {"user_id": user_id},
            {"$set": settings},
            upsert=True
        )

    def get_blacklist(self, guild_id: str) -> Dict[str, Any]:
        """Get a guild's blacklist settings."""
        if self.db is None or self.blacklists is None: 
            logger.warning("Attempted to get_blacklist but MongoDB is not connected.")
            return {"channels": [], "categories": []} # Return default if not connected
        blacklist = self.blacklists.find_one({"guild_id": guild_id})
        return blacklist if blacklist else {"channels": [], "categories": []}

    def save_blacklist(self, guild_id: str, data: Dict[str, Any]) -> None:
        """Save a guild's blacklist settings."""
        if self.db is None or self.blacklists is None: 
            logger.warning("Attempted to save_blacklist but MongoDB is not connected.")
            return
        data["updated_at"] = datetime.utcnow()
        self.blacklists.update_one(
            {"guild_id": guild_id},
            {"$set": data},
            upsert=True
        )

    def get_webhook(self, channel_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get webhook info for a channel."""
        if self.db is None or self.webhooks is None: 
            logger.warning("Attempted to get_webhook but MongoDB is not connected.")
            return None
        return self.webhooks.find_one({
            "channel_id": channel_id,
            "guild_id": guild_id
        })

    def save_webhook(self, channel_id: int, guild_id: int, webhook_id: int, webhook_token: str) -> None:
        """Save webhook info for a channel."""
        if self.db is None or self.webhooks is None: 
            logger.warning("Attempted to save_webhook but MongoDB is not connected.")
            return
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
        if self.db is None or self.webhooks is None: 
            logger.warning("Attempted to delete_webhook but MongoDB is not connected.")
            return
        self.webhooks.delete_one({
            "channel_id": channel_id,
            "guild_id": guild_id
        })

    def record_switch(self, user_id: str, alter_id: str) -> None:
        """Record a switch event."""
        if self.db is None or self.switches is None: 
            logger.warning("Attempted to record_switch but MongoDB is not connected.")
            return
        self.switches.insert_one({
            "user_id": user_id,
            "alter_id": alter_id,
            "timestamp": datetime.utcnow()
        })

    def get_recent_switches(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent switches for a user."""
        if self.db is None or self.switches is None: 
            logger.warning("Attempted to get_recent_switches but MongoDB is not connected.")
            return [] # Return empty list if not connected
        return list(self.switches.find(
            {"user_id": user_id},
            sort=[("timestamp", -1)],
            limit=limit
        ))

# Create global database instance
db = MongoDB() 