from typing import List
from utils.mongodb import db


def load_channel_blacklist(guild_id: str) -> List[str]:
    """Return list of blacklisted channel IDs for the given guild from MongoDB."""
    bl = db.get_blacklist(guild_id)
    return bl.get("channels", [])


def save_channel_blacklist(guild_id: str, channels: List[str]) -> None:
    """Save list of blacklisted channel IDs for the given guild to MongoDB."""
    bl = db.get_blacklist(guild_id)
    # preserve existing categories
    categories = bl.get("categories", [])
    db.save_blacklist(guild_id, {"channels": channels, "categories": categories})


def load_category_blacklist(guild_id: str) -> List[str]:
    """Return list of blacklisted category IDs for the given guild from MongoDB."""
    bl = db.get_blacklist(guild_id)
    return bl.get("categories", [])


def save_category_blacklist(guild_id: str, categories: List[str]) -> None:
    """Save list of blacklisted category IDs for the given guild to MongoDB."""
    bl = db.get_blacklist(guild_id)
    # preserve existing channels
    channels = bl.get("channels", [])
    db.save_blacklist(guild_id, {"channels": channels, "categories": categories})


# Legacy aliases for channel-based blacklist
load_blacklist = load_channel_blacklist
save_blacklist = save_channel_blacklist
