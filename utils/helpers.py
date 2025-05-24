import re
import discord
from utils.profiles import load_profiles

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

def find_alter_by_name(user_id: str, search_name: str) -> str:
    """Find an alter by name or alias. Returns the actual alter name or None."""
    profiles = load_profiles()
    
    if user_id not in profiles or "alters" not in profiles[user_id]:
        return None
    
    alters = profiles[user_id]["alters"]
    search_name_lower = search_name.lower()
    
    # First try exact name match
    for alter_name in alters:
        if alter_name.lower() == search_name_lower:
            return alter_name
    
    # Then try alias match
    for alter_name, alter_data in alters.items():
        aliases = alter_data.get("aliases", [])
        for alias in aliases:
            if alias.lower() == search_name_lower:
                return alter_name
    
    # Finally try partial match on names
    for alter_name in alters:
        if search_name_lower in alter_name.lower():
            return alter_name
    
    return None

def create_embed(title: str, description: str = None, color: int = 0x8A2BE2) -> discord.Embed:
    """Create a standard embed with consistent styling."""
    embed = discord.Embed(title=title, description=description, color=color)
    return embed
