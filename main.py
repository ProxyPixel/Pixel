import os
import discord
import threading
import importlib
import sys
import traceback
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
intents.reactions = True

# Check Discord.py version for setup compatibility
discord_version = discord.__version__
major_version = int(discord_version.split('.')[0])
print(f"Discord.py version: {discord_version}")

# Use async setup if using Discord.py 2.0+
USE_ASYNC_SETUP = major_version >= 2
print(f"Using {'async' if USE_ASYNC_SETUP else 'sync'} setup for cogs")

bot = commands.Bot(command_prefix="!", intents=intents)

# Debug event to confirm commands are registered
@bot.event
async def on_ready():
    print('------')
    print(f'Logged in as {bot.user.name} | {bot.user.id}')
    print(f'Command prefix: {bot.command_prefix}')
    print('------')
    print('Registered commands:')
    for command in bot.commands:
        print(f'- {command.name}')
    print('------')

# Debug event to see what's happening with command invocations
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.content.startswith('!pixelhelp'):
        print(f"pixelhelp command detected in message: {message.content}")
    # Pass the message to the command processor
    await bot.process_commands(message)

# Debug event to track command errors
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        command_name = ctx.message.content.split()[0][len(bot.command_prefix):]
        print(f"Command not found: {command_name}")
        print(f"Available commands: {[c.name for c in bot.commands]}")
    else:
        print(f"Error: {error}")

# Function to load extensions based on Discord.py version
async def load_extensions():
    cog_directories = ["cogs", "events"]

    for cog_dir in cog_directories:
        # Debug: list contents of each cog directory
        try:
            files = os.listdir(cog_dir)
        except FileNotFoundError:
            files = []
        print(f"🔎 Scanning folder: {cog_dir} → {files}")

        if not os.path.exists(cog_dir):
            print(f"⚠️ Directory {cog_dir} does not exist, creating it...")
            os.makedirs(cog_dir)

        for filename in files:
            if not filename.endswith(".py") or filename.startswith("__"):
                continue

            extension = f"{cog_dir}.{filename[:-3]}"
            try:
                if USE_ASYNC_SETUP:
                    await bot.load_extension(extension)
                else:
                    bot.load_extension(extension)
                print(f"✅ Loaded extension: {extension}")
            except Exception:
                print(f"❌ FAILED to load extension: {extension}")
                traceback.print_exc()

async def main():
    # Load all extensions
    await load_extensions()

    # Debug: inspect what got loaded
    print(f"▶️  Final bot.extensions: {list(bot.extensions.keys())}")
    print(f"▶️  Final bot.cogs: {list(bot.cogs.keys())}")
    print(f"▶️  Final bot.commands: {[c.name for c in bot.commands]}")

    # Get token
    token = None
    for var in ("DISCORD_TOKEN", "BOT_TOKEN", "NEW_BOT_TOKEN"):
        token = os.getenv(var)
        if token:
            break

    # If still unfound, try reading .env manually
    if not token:
        try:
            with open('.env', 'r') as f:
                for line in f:
                    for prefix in ("DISCORD_TOKEN=", "BOT_TOKEN=", "NEW_BOT_TOKEN="):
                        if line.startswith(prefix):
                            token = line.strip().split('=', 1)[1]
                            break
                    if token:
                        break
        except Exception as e:
            print(f"Error reading .env: {e}")

    if token:
        print("✅ Discord bot token loaded successfully")
    else:
        print("❌ ERROR: Discord bot token not found")
        return

    # Run the bot
    await bot.start(token)

if __name__ == "__main__":
    # Start the Flask web server in a separate thread
    threading.Thread(target=run_flask, daemon=True).start()

    if USE_ASYNC_SETUP:
        import asyncio
        asyncio.run(main())
    else:
        # For Discord.py <2.0, run sync loads then start
        for cog_dir in ["cogs", "events"]:
            if not os.path.exists(cog_dir):
                os.makedirs(cog_dir)
            for filename in os.listdir(cog_dir):
                if filename.endswith(".py") and not filename.startswith("__"):
                    ext = f"{cog_dir}.{filename[:-3]}"
                    try:
                        bot.load_extension(ext)
                        print(f"✅ Loaded extension: {ext}")
                    except Exception as e:
                        print(f"❌ FAILED to load extension {ext}: {e}")

        token = None
        for var in ("DISCORD_TOKEN", "BOT_TOKEN", "NEW_BOT_TOKEN"):
            token = os.getenv(var)
            if token:
                break

        if token:
            print("✅ Discord bot token loaded successfully")
            bot.run(token)
        else:
            print("❌ ERROR: Discord bot token not found")
            sys.exit(1)
