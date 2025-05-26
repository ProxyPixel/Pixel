import os
from mongodb import db
from profiles import PROFILES_FILE, AUTO_PROXY_FILE
from blacklist import CATEGORY_BLACKLIST_FILE, CHANNEL_BLACKLIST_FILE

# Additional file paths
FOLDERS_FILE = os.path.join("data", "folders.json")
SWITCHES_FILE = os.path.join("data", "switches.json")

def migrate_data():
    """Migrate existing JSON data to MongoDB."""
    print("Starting data migration to MongoDB...")
    
    # Connect to MongoDB
    db.connect()
    
    # Migrate profiles
    print("Migrating profiles...")
    db.import_json_to_mongo('profiles', PROFILES_FILE)
    
    # Migrate autoproxy settings
    print("Migrating autoproxy settings...")
    db.import_json_to_mongo('autoproxy', AUTO_PROXY_FILE)
    
    # Migrate blacklists
    print("Migrating blacklists...")
    db.import_json_to_mongo('category_blacklist', CATEGORY_BLACKLIST_FILE)
    db.import_json_to_mongo('channel_blacklist', CHANNEL_BLACKLIST_FILE)
    
    # Migrate folders
    print("Migrating folders...")
    db.import_json_to_mongo('folders', FOLDERS_FILE)
    
    # Migrate switches
    print("Migrating switches...")
    db.import_json_to_mongo('switches', SWITCHES_FILE)
    
    print("Migration completed!")
    
    # Close MongoDB connection
    db.close()

if __name__ == "__main__":
    migrate_data() 