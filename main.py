import os
import discord
import threading
import importlib
import sys
import traceback
import logging
import uuid
from dotenv import load_dotenv
from discord.ext import commands, tasks
from flask import Flask
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pixel.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('pixel')

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
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host="0.0.0.0", port=port)

# Set up Discord bot with necessary intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.reactions = True
intents.members = True

class PixelBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.start_time = datetime.utcnow()
        self.instance_id = str(uuid.uuid4())[:8]
        self.status_options = [
            "Managing systems",
            "Proxying messages",
            "Organizing folders",
            "Handling proxies",
            "!pixelhelp for all commands",
            "Connecting systems",
            "Serving multiple servers"
        ]
        self.current_status = 0
        self._loaded_cogs = set()
        
    async def setup_hook(self):
        """This is called when the bot starts, before logging in."""
        await self.load_extensions()
        
    async def load_extensions(self):
        """Load all extensions from the cogs directory."""
        for directory in ["cogs"]:
            try:
                if not os.path.exists(directory):
                    os.makedirs(directory)
                    
                files = [f for f in os.listdir(directory) 
                        if f.endswith('.py') and not f.startswith('__')]
                
                logger.info(f"🔎 Scanning folder: {directory} → {files}")
                
                for filename in files:
                    ext = f"{directory}.{filename[:-3]}"
                    if ext not in self._loaded_cogs:
                        try:
                            await self.load_extension(ext)
                            self._loaded_cogs.add(ext)
                            logger.info(f"✅ Loaded extension: {ext}")
                        except Exception as e:
                            logger.error(f"❌ Failed to load {ext}: {str(e)}")
                            traceback.print_exception(type(e), e, e.__traceback__)
            except Exception as e:
                logger.error(f"❌ Error loading from {directory}: {str(e)}")

    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info('------')
        logger.info(f'Logged in as {self.user.name} | {self.user.id}')
        logger.info(f'Bot instance {self.instance_id} is ready!')
        logger.info(f'Command prefix: {self.command_prefix}')
        logger.info('------')
        logger.info('Registered commands:')
        for command in self.commands:
            logger.info(f'- {command.name}')
        logger.info('------')
        
        # Start status rotation
        if not self.rotate_status.is_running():
            self.rotate_status.start()

    @tasks.loop(minutes=2.0)
    async def rotate_status(self):
        """Rotate through different status messages."""
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=self.status_options[self.current_status]
        )
        await self.change_presence(activity=activity)
        self.current_status = (self.current_status + 1) % len(self.status_options)

    async def on_command_error(self, ctx, error):
        """Global error handler for commands."""
        if isinstance(error, commands.CommandNotFound):
            command_name = ctx.message.content.split()[0][len(self.command_prefix):]
            logger.warning(f"Command not found: {command_name}")
            logger.info(f"Available commands: {[c.name for c in self.commands]}")
            return
            
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command.")
            return
            
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.send("❌ This command can't be used in private messages.")
            return
            
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
            return
            
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument: {str(error)}")
            return
            
        # Log unexpected errors
        logger.error(f'Error in command {ctx.command}: {str(error)}')
        traceback.print_exception(type(error), error, error.__traceback__)
        
        # Notify user
        await ctx.send("❌ An unexpected error occurred. Please try again later.")

    async def on_guild_join(self, guild):
        """Called when the bot joins a guild."""
        logger.info(f'Joined guild: {guild.name} (ID: {guild.id})')
        
        # Try to send welcome message
        try:
            # Find the first channel we can send messages in
            channel = next((
                channel for channel in guild.text_channels
                if channel.permissions_for(guild.me).send_messages
            ), None)
            
            if channel:
                embed = discord.Embed(
                    title="👋 Thanks for adding PIXEL!",
                    description=(
                        "PIXEL is a bot designed to help systems with DID/OSDD "
                        "manage their alters and system information.\n\n"
                        "Use `!pixelhelp` to see available commands."
                    ),
                    color=0x8A2BE2
                )
                embed.add_field(
                    name="🔧 Quick Setup",
                    value=(
                        "1. Create your system with `!create_system <name>`\n"
                        "2. Add alters with `!create <name> <pronouns>`\n"
                        "3. Set up proxies with `!proxy set <name> <tags>`"
                    ),
                    inline=False
                )
                embed.add_field(
                    name="📚 Documentation",
                    value="For detailed help and examples, visit our [documentation](https://github.com/yourusername/pixel-bot)",
                    inline=False
                )
                await channel.send(embed=embed)
        except Exception as e:
            logger.error(f'Error sending welcome message to {guild.name}: {str(e)}')

    async def on_guild_remove(self, guild):
        """Called when the bot is removed from a guild."""
        logger.info(f'Left guild: {guild.name} (ID: {guild.id})')

# Create bot instance
bot = PixelBot()

if __name__ == "__main__":
    # Start the Flask web server in a separate thread
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Get token
    token = None
    for var in ("DISCORD_TOKEN", "BOT_TOKEN", "NEW_BOT_TOKEN"):
        token = os.getenv(var)
        if token:
            break

    if token:
        logger.info("✅ Discord bot token loaded successfully")
        bot.run(token)
    else:
        logger.error("❌ ERROR: Discord bot token not found")
        sys.exit(1)
