<<<<<<< HEAD
import json
import os

DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

CATEGORY_BLACKLIST_FILE = os.path.join(DATA_DIR, "category_blacklist.json")
CHANNEL_BLACKLIST_FILE = os.path.join(DATA_DIR, "channel_blacklist.json")

def load_category_blacklist():
    """Loads the category blacklist from a JSON file."""
    if not os.path.exists(CATEGORY_BLACKLIST_FILE):
        with open(CATEGORY_BLACKLIST_FILE, "w") as f:
            json.dump([], f)

    try:
        with open(CATEGORY_BLACKLIST_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ Error: category_blacklist.json is corrupted. Resetting file.")
        return []

def save_category_blacklist(data):
    """Saves the category blacklist to a JSON file."""
    with open(CATEGORY_BLACKLIST_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_channel_blacklist():
    """Loads the channel blacklist from a JSON file."""
    if not os.path.exists(CHANNEL_BLACKLIST_FILE):
        with open(CHANNEL_BLACKLIST_FILE, "w") as f:
            json.dump([], f)

    try:
        with open(CHANNEL_BLACKLIST_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ Error: channel_blacklist.json is corrupted. Resetting file.")
        return []

def save_channel_blacklist(data):
    """Saves the channel blacklist to a JSON file."""
    with open(CHANNEL_BLACKLIST_FILE, "w") as f:
        json.dump(data, f, indent=4)
||||||| empty tree
=======
import json
import os

# Directory for all data files
DATA_DIR = "data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Path definitions
CATEGORY_BLACKLIST_FILE = os.path.join(DATA_DIR, "category_blacklist.json")
CHANNEL_BLACKLIST_FILE = os.path.join(DATA_DIR, "channel_blacklist.json")

def load_category_blacklist():
    """Loads the category blacklist from a JSON file."""
    if not os.path.exists(CATEGORY_BLACKLIST_FILE):
        with open(CATEGORY_BLACKLIST_FILE, "w") as f:
            json.dump([], f)

    try:
        with open(CATEGORY_BLACKLIST_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ Error: category_blacklist.json is corrupted. Resetting file.")
        return []

def save_category_blacklist(data):
    """Saves the category blacklist to a JSON file."""
    with open(CATEGORY_BLACKLIST_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_channel_blacklist():
    """Loads the channel blacklist from a JSON file."""
    if not os.path.exists(CHANNEL_BLACKLIST_FILE):
        with open(CHANNEL_BLACKLIST_FILE, "w") as f:
            json.dump([], f)

    try:
        with open(CHANNEL_BLACKLIST_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ Error: channel_blacklist.json is corrupted. Resetting file.")
        return []

def save_channel_blacklist(data):
    """Saves the channel blacklist to a JSON file."""
    with open(CHANNEL_BLACKLIST_FILE, "w") as f:
        json.dump(data, f, indent=4)
>>>>>>> 148e586dd485e85a7336569dd4700d06a440eff4
