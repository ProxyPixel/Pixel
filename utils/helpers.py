import re

def is_valid_hex_color(color_code):
    """Validates if a string is a proper hex color."""
    return bool(re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color_code))

def is_valid_url(url):
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
