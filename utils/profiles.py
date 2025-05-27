from typing import Dict, Any
from utils.mongodb import db


def get_profile(user_id: str) -> Dict[str, Any]:
    """Retrieve a user's profile from MongoDB. Returns empty dict if none exists."""
    profile = db.get_profile(user_id)
    return profile if profile is not None else {}


def save_profile(user_id: str, data: Dict[str, Any]) -> None:
    """Save or update a user's profile in MongoDB."""
    db.save_profile(user_id, data)


def get_autoproxy(user_id: str) -> Dict[str, Any]:
    """Retrieve a user's autoproxy settings from MongoDB. Returns default if not set."""
    return db.get_autoproxy(user_id)


def save_autoproxy(user_id: str, settings: Dict[str, Any]) -> None:
    """Save or update a user's autoproxy settings in MongoDB."""
    db.save_autoproxy(user_id, settings)
