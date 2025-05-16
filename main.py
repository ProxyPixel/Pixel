import os
import discord
from discord.ext import commands
from flask import Flask
import threading

# Flask app for health checks
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

# Start Flask in a separate thread
def run_flask():
    app.run(host="0.0.0.0", port=5000)

# Initialize bot
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Load extensions (Cogs)
extensions = [
    "commands.system",
    "commands.alters",
    "commands.folders",
    "commands.admin",
    "commands.proxy",
    "events.message_events",
    "events.ready_event"
]

for ext in extensions:
    bot.load_extension(ext)

if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    bot.run(os.getenv("NEW_BOT_TOKEN"))
