import discord
from discord.ext import commands
from utils.mongodb import db
from utils.helpers import find_alter_by_name, create_embed
import aiohttp
import re
import asyncio
import logging
from typing import Optional, Tuple, Dict, List
from datetime import datetime, timedelta
import io

logger = logging.getLogger(__name__)

class ProxyCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.proxy_cache = {}  # Cache proxy settings for performance
        self.autoproxy_settings = {}  # Store autoproxy user preferences

        
        self.message_map = {}  # Map proxied message IDs to original author IDs
        self._session = None  # aiohttp session
        self._webhook_cache = {}  # Cache webhooks
        self._webhook_locks = {}  # Locks per webhook
        self._lock = asyncio.Lock()  # Prevent race conditions
        self._webhook_cleanup_task = None
        self._last_webhook_cleanup = datetime.now()
        self._message_cache = {}  # Cache for message info

    async def get_session(self):
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
        
    def cog_unload(self):
        """Cleanup when cog is unloaded."""
        if self._session and not self._session.closed:
            asyncio.create_task(self._session.close())
        if self._webhook_cleanup_task:
            self._webhook_cleanup_task.cancel()

    async def initialize_cache(self):
        """Initialize cache from the database to speed up proxy matching."""
        try:
            # Connect to MongoDB
            db.connect()
            
            # Get all profiles
            cursor = db.profiles.find({})
            for user_data in cursor:
                user_id = user_data.get('user_id')
                if not user_id or user_id == "_meta":
                    continue
                    
                # Preprocess all proxy patterns for this user
                user_proxies = []
                for alter_name, alter_data in user_data.get("alters", {}).items():
                    if proxy_tag := alter_data.get("proxy"):
                        # Parse the proxy pattern
                        prefix, suffix = self.parse_proxy_pattern(proxy_tag)
                        user_proxies.append({
                            "name": alter_name,
                            "prefix": prefix,
                            "suffix": suffix,
                            "display_name": alter_data.get("displayname", alter_name),
                            "avatar": alter_data.get("proxy_avatar") or alter_data.get("avatar"),
                            "proxy_tag": proxy_tag
                        })
                
                if user_proxies:
                    self.proxy_cache[user_id] = user_proxies
                    
            # Load autoproxy settings
            cursor = db.autoproxy.find({})
            for settings in cursor:
                user_id = settings.get('user_id')
                if user_id:
                    self.autoproxy_settings[user_id] = settings

            # Start webhook cleanup task
            self._webhook_cleanup_task = asyncio.create_task(self._cleanup_webhooks_periodically())
            
            logger.info("✅ Proxy cache initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize proxy cache: {e}")
            logger.info("🔄 Proxy cog will continue without cache - features may be limited until database connection is restored")
            # Don't raise the exception - allow the cog to load without cache

    async def _cleanup_webhooks_periodically(self):
        """Periodically clean up old webhooks from cache."""
        try:
            while True:
                await asyncio.sleep(300)  # Run every 5 minutes
                now = datetime.now()
                
                # Clean up webhook cache
                for key in list(self._webhook_cache.keys()):
                    webhook = self._webhook_cache[key]
                    try:
                        await webhook.fetch()
                    except (discord.NotFound, discord.Forbidden):
                        del self._webhook_cache[key]
                        if key in self._webhook_locks:
                            del self._webhook_locks[key]
                
                self._last_webhook_cleanup = now
        except asyncio.CancelledError:
            pass

    async def create_or_get_webhook(self, channel):
        """Create or get a webhook for the channel."""
        cache_key = f"{channel.guild.id}_{channel.id}"
        
        # Check bot permissions first
        permissions = channel.permissions_for(channel.guild.me)
        if not permissions.manage_webhooks:
            logger.error(f"Missing manage_webhooks permission in {channel.name}")
            await channel.send("❌ I don't have the required permissions to proxy correctly. Please check if I have **Manage Messages** & **Manage Webhooks** permissions!")
            return None
        if not permissions.manage_messages:
            logger.error(f"Missing manage_messages permission in {channel.name}")
            await channel.send("❌ I don't have the required permissions to proxy correctly. Please check if I have **Manage Messages** & **Manage Webhooks** permissions!")
            return None
        
        # Get or create lock for this webhook
        if cache_key not in self._webhook_locks:
            self._webhook_locks[cache_key] = asyncio.Lock()
        
        # Check cache first
        if cache_key in self._webhook_cache:
            try:
                webhook = self._webhook_cache[cache_key]
                await webhook.fetch()  # Verify webhook still exists
                logger.info(f"Retrieved existing webhook for {channel.name}")
                return webhook
            except discord.NotFound:
                del self._webhook_cache[cache_key]
        
        async with self._webhook_locks[cache_key]:
            try:
                # Check database for existing webhook
                webhook_data = db.get_webhook(channel.id, channel.guild.id)
                if webhook_data:
                    try:
                        webhook = discord.Webhook.partial(
                            webhook_data["webhook_id"], 
                            webhook_data["webhook_token"], 
                            session=await self.get_session()
                        )
                        await webhook.fetch()  # Test if webhook still exists
                        self._webhook_cache[cache_key] = webhook
                        logger.info(f"Retrieved existing webhook for {channel.name}")
                        return webhook
                    except discord.NotFound:
                        # Webhook was deleted, remove from database
                        db.delete_webhook(channel.id, channel.guild.id)
                
                # Create new webhook
                webhook = await channel.create_webhook(name="PIXEL Proxy")
                
                # Store in database and cache
                db.save_webhook(channel.id, channel.guild.id, webhook.id, webhook.token)
                self._webhook_cache[cache_key] = webhook
                logger.info(f"Created new webhook for {channel.name}")
                return webhook
                
            except discord.Forbidden:
                logger.error(f"No permission to create webhook in {channel.name}")
                await channel.send("❌ I don't have the required permissions to proxy correctly. Please check if I have **Manage Messages** & **Manage Webhooks** permissions!")
                return None
            except Exception as e:
                logger.error(f"Error creating webhook for {channel.name}: {e}")
                return None

    def parse_proxy_pattern(self, proxy_pattern: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse a proxy pattern to determine prefix, suffix, or both."""
        if not proxy_pattern:
            return None, None
            
        # Match PluralKit's TEXT placeholder format
        if "TEXT" in proxy_pattern:
            parts = proxy_pattern.split("TEXT")
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
                
        # For text: format (common in other bots)
        if "text" in proxy_pattern and ":" in proxy_pattern:
            parts = proxy_pattern.split(":", 1)
            return f"{parts[0]}:", ""
            
        # Default behavior: treat as prefix if suffix not specified
        return proxy_pattern.strip(), ""

    @commands.command(name="set_proxy")
    async def set_proxy(self, ctx, alter_name: str = None, *, proxy_tag: str = None):
        """Set proxy tags for an alter."""
        
        if not alter_name or not proxy_tag:
            await ctx.send("❌ Usage: `!set_proxy <alter_name> <proxy_tag>`\nExample: `!set_proxy Alex A: TEXT` or `!set_proxy Alex TEXT :A`")
            return
            
        # Get user profile from MongoDB
        profile = db.get_profile(str(ctx.author.id))
        if not profile or "alters" not in profile:
            await ctx.send("❌ You don't have any alters set up.")
            return
            
        actual_name = find_alter_by_name(profile, alter_name)
        if not actual_name:
            await ctx.send(f"❌ Alter '{alter_name}' does not exist.")
            return

        if "text" in proxy_tag.lower() and "TEXT" not in proxy_tag:
            proxy_tag = proxy_tag.replace("text", "TEXT")
            
        profile["alters"][actual_name]["proxy"] = proxy_tag
        db.save_profile(str(ctx.author.id), profile)
        await self.initialize_cache()
        
        prefix, suffix = self.parse_proxy_pattern(proxy_tag)
        example = ""
        if prefix:
            example += f"`{prefix}`"
        example += "Your message here"
        if suffix:
            example += f"`{suffix}`"
            
        embed = create_embed(
            title="Proxy Set Successfully",
            description=f"Proxy for **{alter_name}** has been set to `{proxy_tag}`.\n\nWhen you type: {example}\nThe bot will send a message as: **{alter_name}**",
            color=profile["alters"][actual_name].get("color", 0x8A2BE2)
        )
        await ctx.send(embed=embed)

    @commands.command(name="proxy")
    async def proxy_management(self, ctx, action: str, alter_name: str = None, *, proxy_tag: str = None):
        """Manage proxy settings for alters."""
        
        if action.lower() == "set":
            # Redirect to set_proxy command
            await ctx.send("ℹ️ The `!proxy set` command has been renamed to `!set_proxy`. Please use `!set_proxy <alter_name> <proxy_tag>` instead.")
            return
            
        elif action.lower() in ["remove", "clear"]:
            if not alter_name:
                await ctx.send("❌ Usage: `!proxy remove <alter_name>`")
                return

            profile = db.get_profile(str(ctx.author.id))
            if not profile or "alters" not in profile:
                await ctx.send("❌ You don't have any alters set up.")
                return

            actual_name = find_alter_by_name(profile, alter_name)
            if not actual_name:
                await ctx.send(f"❌ Alter '{alter_name}' does not exist.")
                return

            if "proxy" in profile["alters"][actual_name]:
                del profile["alters"][actual_name]["proxy"]
                db.save_profile(str(ctx.author.id), profile)
                await self.initialize_cache()
                await ctx.send(f"✅ Proxy for '{alter_name}' has been removed.")
            else:
                await ctx.send(f"❌ Alter '{alter_name}' does not have a proxy set.")
                
        elif action.lower() == "list":
            profile = db.get_profile(str(ctx.author.id))
            if not profile or not profile.get("alters"):
                await ctx.send("❌ You don't have any alters to list proxies for.")
                return

            proxies = []
            for name, alter in profile["alters"].items():
                if "proxy" in alter:
                    display_name = alter.get("displayname", name)
                    proxies.append(f"**{display_name}**: `{alter['proxy']}`")
                    
            if proxies:
                embed = create_embed(
                    title="Your Proxy Tags",
                    description="\n".join(proxies),
                    color=0x8A2BE2
                )
                await ctx.send(embed=embed)
            else:
                await ctx.send("❌ You don't have any proxies set.")
        else:
            await ctx.send("❌ Invalid action. Use `remove` or `list`.")

    @commands.command(name="autoproxy")
    async def autoproxy_command(self, ctx, mode: str = None, *, alter_name: str = None):
        """Set autoproxy mode for this server."""
        
        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id)
        
        # Get server-specific autoproxy settings
        autoproxy_key = f"{user_id}_{guild_id}"
        autoproxy_settings = db.get_autoproxy(autoproxy_key)
        
        if not mode:
            # Show current settings
            if autoproxy_settings.get("enabled"):
                current_mode = autoproxy_settings.get("mode", "off")
                embed = discord.Embed(
                    title="🔄 Current Autoproxy Settings",
                    description=f"**Mode:** {current_mode.title()}\n**Server:** {ctx.guild.name}",
                    color=0x8A2BE2
                )
                
                if current_mode == "latch":
                    last_alter = autoproxy_settings.get("last_alter", "None")
                    embed.add_field(name="Last Alter", value=last_alter, inline=False)
                elif current_mode == "front":
                    fronter = autoproxy_settings.get("fronter", "None set")
                    embed.add_field(name="Fronter", value=fronter, inline=False)
                elif current_mode == "member":
                    member = autoproxy_settings.get("member", "None set")
                    embed.add_field(name="Member", value=member, inline=False)
                    
                embed.add_field(
                    name="Available Modes",
                    value="• `off` - Disable autoproxy\n• `latch` - Proxy as last used alter\n• `front` - Set a fronter\n• `member` - Set a specific member",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="🔄 Autoproxy Disabled",
                    description=f"Autoproxy is currently disabled in **{ctx.guild.name}**.",
                    color=0x8A2BE2
                )
                embed.add_field(
                    name="Available Modes",
                    value="• `latch` - Proxy as last used alter\n• `front` - Set a fronter\n• `member` - Set a specific member",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            return
        
        mode = mode.lower()
        
        if mode in ["off", "disable", "unlatch"]:
            # Disable autoproxy
            autoproxy_settings = {"enabled": False, "mode": "off"}
            db.save_autoproxy(autoproxy_key, autoproxy_settings)
            
            embed = discord.Embed(
                title="✅ Autoproxy Disabled",
                description=f"Autoproxy has been disabled in **{ctx.guild.name}**.",
                color=0x00FF00
            )
            await ctx.send(embed=embed)
            return
        
        # Get user profile
        profile = db.get_profile(user_id)
        if not profile or not profile.get("alters"):
            await ctx.send("❌ You don't have any alters set up.")
            return
        
        if mode == "latch":
            # Enable latch mode
            autoproxy_settings = {
                "enabled": True,
                "mode": "latch",
                "last_alter": autoproxy_settings.get("last_alter"),  # Keep existing last_alter if any
                "guild_id": guild_id
            }
            db.save_autoproxy(autoproxy_key, autoproxy_settings)
            
            embed = discord.Embed(
                title="✅ Latch Mode Enabled",
                description=f"Autoproxy will now use the last alter you manually proxied in **{ctx.guild.name}**.",
                color=0x00FF00
            )
            if autoproxy_settings.get("last_alter"):
                embed.add_field(name="Current Latch", value=autoproxy_settings["last_alter"], inline=False)
            await ctx.send(embed=embed)
            
        elif mode in ["front", "fronter"]:
            if not alter_name:
                await ctx.send("❌ Please specify an alter name for front mode.\nUsage: `!autoproxy front <alter_name>`")
                return
                
            # Find the alter
            alter_name = find_alter_by_name(profile, alter_name)
            if not alter_name:
                await ctx.send("❌ Alter not found.")
                return
            
            autoproxy_settings = {
                "enabled": True,
                "mode": "front",
                "fronter": alter_name,
                "guild_id": guild_id
            }
            db.save_autoproxy(autoproxy_key, autoproxy_settings)
            
            embed = discord.Embed(
                title="✅ Front Mode Enabled",
                description=f"All messages in **{ctx.guild.name}** will now be proxied as **{alter_name}**.",
                color=0x00FF00
            )
            await ctx.send(embed=embed)
            
        elif mode == "member":
            if not alter_name:
                await ctx.send("❌ Please specify an alter name for member mode.\nUsage: `!autoproxy member <alter_name>`")
                return
                
            # Find the alter
            alter_name = find_alter_by_name(profile, alter_name)
            if not alter_name:
                await ctx.send("❌ Alter not found.")
                return
            
            autoproxy_settings = {
                "enabled": True,
                "mode": "member",
                "member": alter_name,
                "guild_id": guild_id
            }
            db.save_autoproxy(autoproxy_key, autoproxy_settings)
            
            embed = discord.Embed(
                title="✅ Member Mode Enabled",
                description=f"All messages in **{ctx.guild.name}** will now be proxied as **{alter_name}**.",
                color=0x00FF00
            )
            await ctx.send(embed=embed)
            
        else:
            await ctx.send("❌ Invalid autoproxy mode. Use `off`, `latch`, `front`, or `member`.")

    @commands.command(name="edit_proxy")
    async def edit_proxied(self, ctx, message_link: str = None, *, new_content: str = None):
        """Edit a previously proxied message."""
        
        if not message_link or not new_content:
            await ctx.send("❌ Usage: `!edit_proxy <message_link> <new_content>`")
            return
            
        # Parse message link
        try:
            parts = message_link.split('/')
            channel_id = int(parts[-2])
            message_id = int(parts[-1])
        except (ValueError, IndexError):
            await ctx.send("❌ Invalid message link. Please right-click the message and use 'Copy Message Link'.")
            return
            
        channel = self.bot.get_channel(channel_id)
        if not channel:
            await ctx.send("❌ Cannot find the channel for this message.")
            return
            
        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            await ctx.send("❌ Cannot find the message.")
            return
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to see that message.")
            return
            
        # Verify ownership
        original_author = self.message_map.get(str(message_id))
        if not original_author or str(ctx.author.id) != original_author:
            await ctx.send("❌ You can only edit messages that you proxied.")
            return
            
        # Get the webhook
        webhook = await self.create_or_get_webhook(channel)
        if not webhook:
            await ctx.send("❌ Failed to get webhook for this channel.")
            return
            
        try:
            await webhook.edit_message(message_id, content=new_content)
            await ctx.message.add_reaction('✅')
        except discord.NotFound:
            await ctx.send("❌ Cannot edit this message. It might be too old.")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to edit this message.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {str(e)}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle incoming messages for proxying."""
        if message.author.bot or message.content.startswith(self.bot.command_prefix):
            return
            
        # Use lock to prevent race conditions
        async with self._lock:
            # Check if channel is blacklisted
            blacklist = db.get_blacklist(str(message.guild.id))
            if message.channel.id in blacklist.get("channels", []) or \
               (message.channel.category and message.channel.category.id in blacklist.get("categories", [])):
                return
                
            # Find matching proxy
            alter_data, alter_name = await self.find_matching_proxy(message)
            if not alter_data:
                return
                
            logger.info(f"Proxy match found: {alter_name} for user {message.author.id} in guild {message.guild.id}")
            
            # Get webhook
            webhook = await self.create_or_get_webhook(message.channel)
            if not webhook:
                return
                
            try:
                # Extract message content
                content = message.content
                proxy_pattern = alter_data.get("proxy")
                if proxy_pattern:
                    prefix, suffix = self.parse_proxy_pattern(proxy_pattern)
                    message_content = self._extract_message_content(content, prefix, suffix)
                    logger.info(f"Extracted content: '{message_content}' from '{content}' using pattern '{proxy_pattern}'")
                else:
                    message_content = content
                    logger.info(f"Using autoproxy, content: '{message_content}'")
                
                # Check for empty content
                if not message_content.strip() and not message.attachments:
                    logger.warning(f"Empty message content after extraction for {alter_name}")
                    return
                
                # Get system tag
                user_id = str(message.author.id)
                profile = db.get_profile(user_id)
                system_tag = ""
                if profile and profile.get("system") and profile["system"].get("tag"):
                    system_tag = f" {profile['system']['tag']}"
                
                # Build webhook username (alter name + system tag)
                display_name = alter_data.get("display_name", alter_name)
                webhook_username = display_name + system_tag
                
                # Ensure username is within Discord's 80 character limit
                if len(webhook_username) > 80:
                    webhook_username = webhook_username[:77] + "..."
                
                logger.info(f"Webhook username: '{webhook_username}' (display_name: '{display_name}', system_tag: '{system_tag}')")
                
                # Get avatar
                avatar_url = alter_data.get("proxy_avatar") or alter_data.get("avatar")
                if not avatar_url and profile and profile.get("system"):
                    avatar_url = profile["system"].get("avatar")
                
                # Handle attachments and embeds
                files = []
                embeds = []
                
                # Process attachments
                if message.attachments:
                    for attachment in message.attachments:
                        try:
                            # Download the attachment
                            file_data = await attachment.read()
                            file = discord.File(
                                io.BytesIO(file_data),
                                filename=attachment.filename,
                                spoiler=attachment.is_spoiler()
                            )
                            files.append(file)
                        except Exception as e:
                            logger.error(f"Error processing attachment {attachment.filename}: {e}")
                
                # Handle GIFs and links that should embed
                if message_content:
                    # Check for Tenor GIF links and convert them to proper embeds
                    tenor_pattern = r'https?://tenor\.com/view/[^\s]+'
                    if re.search(tenor_pattern, message_content):
                        # Let Discord handle the embed naturally by keeping the link
                        pass
                    
                    # Check for other media links
                    media_patterns = [
                        r'https?://[^\s]*\.(gif|png|jpg|jpeg|webp|mp4|mov|webm)',
                        r'https?://cdn\.discordapp\.com/attachments/[^\s]+',
                        r'https?://media\.discordapp\.net/attachments/[^\s]+',
                        r'https?://imgur\.com/[^\s]+',
                        r'https?://i\.imgur\.com/[^\s]+',
                        r'https?://gyazo\.com/[^\s]+',
                        r'https?://i\.gyazo\.com/[^\s]+'
                    ]
                    
                    for pattern in media_patterns:
                        if re.search(pattern, message_content):
                            # Let Discord handle these embeds naturally
                            break
                
                # Send the proxied message
                proxied_message = await webhook.send(
                    content=message_content if message_content.strip() else None,
                    username=webhook_username,
                    avatar_url=avatar_url,
                    files=files,
                    embeds=embeds,
                    wait=True,
                    allowed_mentions=discord.AllowedMentions(
                        everyone=message.author.guild_permissions.mention_everyone,
                        users=True,
                        roles=message.author.guild_permissions.mention_everyone
                    )
                )
                
                # Delete original message
                try:
                    await message.delete()
                except discord.NotFound:
                    pass  # Message was already deleted
                except discord.Forbidden:
                    logger.warning(f"No permission to delete message in {message.channel.name}")
                
                # Update autoproxy latch (server-specific)
                if proxy_pattern:  # Only update latch for manual proxies
                    guild_id = str(message.guild.id)
                    autoproxy_key = f"{user_id}_{guild_id}"
                    autoproxy_settings = db.get_autoproxy(autoproxy_key)
                    if autoproxy_settings.get("mode") == "latch":
                        autoproxy_settings["last_alter"] = alter_name
                        autoproxy_settings["guild_id"] = guild_id
                        db.save_autoproxy(autoproxy_key, autoproxy_settings)
                        logger.info(f"Updated latch to {alter_name} for guild {guild_id}")
                
                # Store message info for editing/deletion
                self._message_cache[proxied_message.id] = {
                    "original_author": message.author.id,
                    "alter_name": alter_name,
                    "timestamp": datetime.utcnow()
                }
                
                logger.info(f"Successfully proxied message as {alter_name} with username '{webhook_username}'")
                
            except Exception as e:
                logger.error(f"Error in proxy: {e}")
                if "Cannot send an empty message" in str(e):
                    logger.warning(f"Attempted to send empty message for {alter_name}")
                elif "Unknown Message" in str(e):
                    logger.warning(f"Original message was deleted before proxy could complete")
                else:
                    # For other errors, try to inform the user
                    try:
                        await message.channel.send(f"❌ Error proxying message: {str(e)}", delete_after=10)
                    except:
                        pass

    def _check_pattern_match(self, content: str, prefix: Optional[str], suffix: Optional[str]) -> bool:
        """Check if content matches the proxy pattern."""
        if not content:
            return False
            
        if prefix and not content.startswith(prefix):
            return False
            
        if suffix and not content.endswith(suffix):
            return False
            
        # Ensure there's actual content between prefix and suffix
        message_content = self._extract_message_content(content, prefix, suffix)
        return bool(message_content.strip())

    def _extract_message_content(self, content: str, prefix: Optional[str], suffix: Optional[str]) -> str:
        """Extract the actual message content from a proxy pattern."""
        if prefix:
            content = content[len(prefix):].lstrip()
        if suffix:
            content = content[:-len(suffix)].rstrip()
        return content

    async def find_matching_proxy(self, message):
        """Find a matching proxy for the message."""
        user_id = str(message.author.id)
        guild_id = str(message.guild.id)
        
        try:
            profile = db.get_profile(user_id)
        except Exception as e:
            logger.error(f"Failed to get profile for {user_id}: {e}")
            return None, None
        
        if not profile or not profile.get("alters"):
            return None, None
            
        content = message.content
        
        # Check autoproxy first (server-specific)
        try:
            autoproxy_key = f"{user_id}_{guild_id}"
            autoproxy_settings = db.get_autoproxy(autoproxy_key)
            if autoproxy_settings.get("enabled"):
                mode = autoproxy_settings.get("mode")
                if mode == "latch" and autoproxy_settings.get("last_alter"):
                    alter_name = autoproxy_settings["last_alter"]
                    if alter_name in profile["alters"]:
                        logger.info(f"Using latch autoproxy for {alter_name} in guild {guild_id}")
                        return profile["alters"][alter_name], alter_name
                elif mode == "front" and autoproxy_settings.get("fronter"):
                    alter_name = autoproxy_settings["fronter"]
                    if alter_name in profile["alters"]:
                        logger.info(f"Using front autoproxy for {alter_name} in guild {guild_id}")
                        return profile["alters"][alter_name], alter_name
                elif mode == "member" and autoproxy_settings.get("member"):
                    alter_name = autoproxy_settings["member"]
                    if alter_name in profile["alters"]:
                        logger.info(f"Using member autoproxy for {alter_name} in guild {guild_id}")
                        return profile["alters"][alter_name], alter_name
        except Exception as e:
            logger.error(f"Failed to check autoproxy settings: {e}")
        
        # Check manual proxy patterns
        for alter_name, alter_data in profile["alters"].items():
            proxy_pattern = alter_data.get("proxy")
            if not proxy_pattern:
                continue
                
            prefix, suffix = self.parse_proxy_pattern(proxy_pattern)
            if self._check_pattern_match(content, prefix, suffix):
                logger.info(f"Using manual proxy for {alter_name}")
                return alter_data, alter_name
                
        return None, None

    async def retry_cache_initialization(self):
        """Retry cache initialization if it failed during startup."""
        if not self.proxy_cache and not self.autoproxy_settings:
            logger.info("🔄 Retrying proxy cache initialization...")
            await self.initialize_cache()

async def setup(bot):
    """Set up the proxy cog."""
    cog = ProxyCommands(bot)
    try:
        await cog.initialize_cache()
    except Exception as e:
        logger.error(f"❌ Failed to initialize proxy cache during setup: {e}")
        logger.info("🔄 Proxy cog loaded without cache - will retry connection later")
    
    await bot.add_cog(cog)
    print("✅ Proxy cog loaded successfully")
