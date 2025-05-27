import re
import discord
from utils.mongodb import db
from typing import Optional, Dict, Any
from datetime import datetime

VALID_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg')

# -- Validators -------------------------------------------------------------

def is_valid_hex_color(color_code: str) -> bool:
    """Validates if a string is a proper hex color."""
    return bool(re.fullmatch(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color_code))


def is_valid_url(url: str) -> bool:
    """Validates if a string is a proper URL."""
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'  # domain
        r'(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain extension
        r'localhost|'  # localhost
        r'\d{1,3}(?:\.\d{1,3}){3}|'  # IPv4
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)'  # IPv6
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    return bool(regex.match(url))


def is_valid_image_file(file_name: str) -> bool:
    """Checks if the file name has a valid image extension."""
    return file_name.lower().endswith(VALID_IMAGE_EXTENSIONS)

# -- Profile Helpers --------------------------------------------------------

def find_alter_by_name(profile: Dict[str, Any], search_name: str) -> Optional[str]:
    """Find an alter by name or alias in the given profile, case-insensitive."""
    if not profile or 'alters' not in profile:
        return None

    name_lower = search_name.lower()
    alters = profile.get('alters', {})

    # Exact match on name, displayname, or aliases
    for name, data in alters.items():
        if name.lower() == name_lower:
            return name
        displayname = data.get('displayname') or ''
        if displayname.lower() == name_lower:
            return name
        aliases = data.get('aliases') or []
        if any(alias.lower() == name_lower for alias in aliases if alias):
            return name

    # Partial match
    for name, data in alters.items():
        if name_lower in name.lower():
            return name
        displayname = data.get('displayname') or ''
        if name_lower in displayname.lower():
            return name
        aliases = data.get('aliases') or []
        if any(name_lower in alias.lower() for alias in aliases if alias):
            return name

    return None

# -- Embed & Formatting -----------------------------------------------------

def create_embed(title: str, description: str = None, color: int = 0x8A2BE2) -> discord.Embed:
    """Create a standardized Discord embed."""
    return discord.Embed(title=title, description=description, color=color)

# -- Utility Functions ------------------------------------------------------

def format_timestamp(ts_str: str) -> str:
    """Format an ISO timestamp string for display, fall back on 'Unknown'."""
    try:
        dt = datetime.fromisoformat(ts_str)
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except Exception:
        return 'Unknown'


def sanitize_name(name: str) -> str:
    """Remove control chars/zero-width spaces and limit to 32 chars."""
    clean = re.sub(r'[\u0000-\u001F\u200B-\u200D\uFEFF]', '', name)
    return clean[:32] or 'Unnamed'


def truncate_text(text: str, max_length: int = 2000) -> str:
    """Truncate text to fit Discord's message length limits."""
    return text if len(text) <= max_length else text[:max_length-3] + '...'


def parse_message_link(link: str) -> Optional[tuple[int, int, int]]:
    """Parse a Discord invite link into (guild_id, channel_id, message_id)."""
    pattern = r'https?://(?:ptb\.|canary\.)?discord\.com/channels/(\d+)/(\d+)/(\d+)'
    m = re.match(pattern, link)
    return tuple(map(int, m.groups())) if m else None
