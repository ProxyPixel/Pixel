import json
import os

# Directory for all data files
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Path definitions
PROFILES_FILE = os.path.join(DATA_DIR, "global_profiles.json")
BACKUP_FILE = os.path.join(DATA_DIR, "profiles_backup.json")
AUTO_PROXY_FILE = os.path.join(DATA_DIR, "autoproxy.json")

def load_profiles():
    """Loads all user profiles from a JSON file."""
    if not os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE, "w") as f:
            json.dump({}, f)

    try:
        with open(PROFILES_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ Error: global_profiles.json is corrupted. Resetting file.")
        return {}

def save_profiles(data):
    """Saves all user profiles to a JSON file."""
    with open(PROFILES_FILE, "w") as f:
        json.dump(data, f, indent=4)

def backup_profiles(data):
    """Saves a backup of all user profiles."""
    with open(BACKUP_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_autoproxy():
    """Loads auto proxy settings."""
    if not os.path.exists(AUTO_PROXY_FILE):
        with open(AUTO_PROXY_FILE, "w") as f:
            json.dump({}, f)

    try:
        with open(AUTO_PROXY_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ Error: autoproxy.json is corrupted. Resetting file.")
        return {}

def save_autoproxy(data):
    """Saves auto proxy settings."""
    with open(AUTO_PROXY_FILE, "w") as f:
        json.dump(data, f, indent=4)
