import re
import discord
from utils.profiles import load_profiles
from typing import Optional, Dict, Any
import datetime

VALID_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg')

def is_valid_hex_color(color_code: str) -> bool:
    """Validates if a string is a proper hex color."""
    return bool(re.fullmatch(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color_code))

def is_valid_url(url: str) -> bool:
    """Validates if a string is a proper URL."""
    regex = re.compile(
        r'^(?:http|ftp)s?://' 
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' 
        r'localhost|' 
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|'  
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)' 
        r'(?::\d+)?'  
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    return re.match(regex, url) is not None

def is_valid_image_file(file_name: str) -> bool:
    return file_name.lower().endswith(VALID_IMAGE_EXTENSIONS)

def find_alter_by_name(profile: Dict[str, Any], search_name: str) -> Optional[str]:
    """Find an alter by name or alias, case-insensitive."""
    if not profile or "alters" not in profile:
        return None

    search_name = search_name.lower()
    
    # First try exact match
    for name, data in profile["alters"].items():
        if name.lower() == search_name:
            return name
        # Ensure displayname is treated as string even if None
        displayname = data.get("displayname") or ""
        if displayname.lower() == search_name:
            return name
        # Ensure aliases is a list and handle None values
        aliases = data.get("aliases") or []
        if search_name in [alias.lower() for alias in aliases if alias]:
            return name

    # Then try partial match
    for name, data in profile["alters"].items():
        if search_name in name.lower():
            return name
        # Ensure displayname is treated as string even if None
        displayname = data.get("displayname") or ""
        if search_name in displayname.lower():
            return name
        # Ensure aliases is a list and handle None values
        aliases = data.get("aliases") or []
        if any(search_name in alias.lower() for alias in aliases if alias):
            return name

    return None

def create_embed(title: str, description: str = None, color: int = 0x8A2BE2) -> discord.Embed:
    """Create a standardized embed with optional fields."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    return embed

def validate_hex_color(color: str) -> bool:
    """Validate a hex color code."""
    if not color:
        return False
    return bool(re.match(r'^#[0-9a-fA-F]{6}$', color))

def validate_url(url: str) -> bool:
    """Validate a URL."""
    if not url:
        return False
    # Basic URL validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return bool(url_pattern.match(url))

def format_timestamp(timestamp: str) -> str:
    """Format a timestamp string for display."""
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, TypeError):
        return "Unknown"

def sanitize_name(name: str) -> str:
    """Sanitize a name for use in Discord."""
    # Remove control characters and zero-width spaces
    name = re.sub(r'[\u0000-\u001F\u200B-\u200D\uFEFF]', '', name)
    # Limit length to 32 characters (Discord's limit)
    name = name[:32]
    # Ensure name isn't empty
    return name if name else "Unnamed"

def truncate_text(text: str, max_length: int = 2000) -> str:
    """Truncate text to fit Discord's limits."""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def parse_message_link(link: str) -> Optional[tuple[int, int, int]]:
    """Parse a Discord message link into (guild_id, channel_id, message_id)."""
    pattern = r'https?://(?:ptb\.|canary\.)?discord\.com/channels/(\d+)/(\d+)/(\d+)'
    match = re.match(pattern, link)
    if not match:
        return None
    return tuple(map(int, match.groups()))
