import os
import discord
import threading
from dotenv import load_dotenv
from discord.ext import commands
from flask import Flask

# Load environment variables from .env file
load_dotenv()

# Create Flask app for web server
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

@app.route("/discord-bot")
def discord_bot_status():
    return "Discord Bot is online!"

@app.route("/health")
def health_check():
    return "Health Check: OK", 200

def run_flask():
    app.run(host="0.0.0.0", port=5000)

# Set up Discord bot with necessary intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Load extensions from cog directories
cog_directories = [
    "cogs",
    "events"
]

for cog_dir in cog_directories:
    for filename in os.listdir(cog_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            extension = f"{cog_dir}.{filename[:-3]}"
            try:
                bot.load_extension(extension)
                print(f"✅ Loaded extension: {extension}")
            except Exception as e:
                print(f"❌ Failed to load extension {extension}: {e}")

def get_token():
 
    token = os.getenv("DISCORD_TOKEN")
    
  
    if not token:
        token = os.getenv("BOT_TOKEN")
    
    if not token:
        token = os.getenv("NEW_BOT_TOKEN")

    if not token:
        try:
            with open('.env', 'r') as file:
                for line in file:
                    if line.startswith(('DISCORD_TOKEN=', 'BOT_TOKEN=', 'NEW_BOT_TOKEN=')):
                        token = line.strip().split('=', 1)[1]
                        break
        except Exception as e:
            print(f"Error reading .env file: {e}")
    
    if token:
        token = token.strip().strip("'\"")
    
    return token

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    
    token = get_token()
    
    if token:
        print("✅ Discord bot token loaded successfully")
    else:
        print("❌ ERROR: Discord bot token not found in environment variables or .env file")
        exit(1)
    
    # Run the bot
    bot.run(token)
