import discord
from discord.ext import commands
from utils.profiles import load_profiles, save_profiles
from utils.helpers import find_alter_by_name, create_embed
import aiohttp
import re
import asyncio
from typing import Optional, Tuple, Dict, List

global_profiles = load_profiles()

class ProxyCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.proxy_cache = {}  # Cache proxy settings for performance
        self.autoproxy_settings = {}  # Store autoproxy user preferences
        self.webhook_cache = {}  # Store recently used webhooks
        self.message_map = {}  # Map proxied message IDs to original author IDs
        
    async def initialize_cache(self):
        """Initialize cache from the database to speed up proxy matching."""
        for user_id, user_data in global_profiles.items():
            if user_id == "_meta":
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
                        "avatar": alter_data.get("avatar"),
                        "proxy_tag": proxy_tag
                    })
            
            if user_proxies:
                self.proxy_cache[user_id] = user_proxies
    
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
        
    @commands.command(name="proxy")
    async def proxy_management(self, ctx, action: str, alter_name: str = None, *, proxy_tag: str = None):
        """Manage proxy settings for your alters (set, remove, list)."""
        user_id = str(ctx.author.id)
        
        if action.lower() == "set":
            if not alter_name or not proxy_tag:
                await ctx.send("❌ Usage: `!proxy set <alter_name> <proxy_tag>`\nExample: `!proxy set Alex A: TEXT` or `!proxy set Alex TEXT :A`")
                return
                
            actual_name = find_alter_by_name(user_id, alter_name)
            if not actual_name:
                await ctx.send(f"❌ Alter '{alter_name}' does not exist.")
            return

            if "text" in proxy_tag.lower() and "TEXT" not in proxy_tag:
                proxy_tag = proxy_tag.replace("text", "TEXT")
                
            global_profiles[user_id]["alters"][actual_name]["proxy"] = proxy_tag
            save_profiles(global_profiles)
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
                color=global_profiles[user_id]["alters"][actual_name].get("color", 0x8A2BE2)
            )
            await ctx.send(embed=embed)
            
        elif action.lower() in ["remove", "clear"]:
            if not alter_name:
                await ctx.send("❌ Usage: `!proxy remove <alter_name>`")
                return

            actual_name = find_alter_by_name(user_id, alter_name)
            if not actual_name:
                await ctx.send(f"❌ Alter '{alter_name}' does not exist.")
                return

            if "proxy" in global_profiles[user_id]["alters"][actual_name]:
                del global_profiles[user_id]["alters"][actual_name]["proxy"]
                save_profiles(global_profiles)
                await self.initialize_cache()
                await ctx.send(f"✅ Proxy for '{alter_name}' has been removed.")
            else:
                await ctx.send(f"❌ Alter '{alter_name}' does not have a proxy set.")
                
        elif action.lower() == "list":
            if user_id not in global_profiles or not global_profiles[user_id]["alters"]:
                await ctx.send("❌ You don't have any alters to list proxies for.")
                return

            proxies = []
            for name, alter in global_profiles[user_id]["alters"].items():
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
            await ctx.send("❌ Invalid action. Use `set`, `remove`, or `list`.")

    @commands.command(name="set_proxy")
    async def set_proxy(self, ctx, name: str, *, proxy: str):
        """Set a proxy for an alter (legacy command for backward compatibility)."""
        await self.proxy_management(ctx, "set", name, proxy_tag=proxy)

    @commands.command(name="autoproxy")
    async def autoproxy_command(self, ctx, mode: str = None, *, alter_name: str = None):
        """Set your autoproxy preferences.
        
        Modes:
        - off: Disable autoproxy
        - latch: Automatically proxy as the last alter you proxied as
        - front: Automatically proxy as a specific alter
        """
        user_id = str(ctx.author.id)

        if not mode:
            # Display current autoproxy setting
            current_setting = self.autoproxy_settings.get(user_id, {})
            mode = current_setting.get("mode", "off")
            alter = current_setting.get("alter", None)
            
            if mode == "off":
                await ctx.send("Autoproxy is currently **disabled**.")
            elif mode == "latch":
                last_alter = current_setting.get("last_used")
                if last_alter:
                    await ctx.send(f"Autoproxy is set to **latch** mode. Currently latched to: **{last_alter}**")
                else:
                    await ctx.send("Autoproxy is set to **latch** mode, but no alter has been proxied yet.")
            elif mode == "front":
                if alter:
                    await ctx.send(f"Autoproxy is set to **front** mode for alter: **{alter}**")
                else:
                    await ctx.send("Autoproxy is set to **front** mode, but no alter is specified.")
            return
            
        mode = mode.lower()
        
        if mode not in ["off", "latch", "front"]:
            await ctx.send("❌ Invalid mode. Use `off`, `latch`, or `front`.")
            return
            
        if mode == "front" and not alter_name:
            await ctx.send("❌ Front mode requires an alter name. Usage: `!autoproxy front <alter_name>`")
            return
            
        if mode == "front":
            # Verify alter exists
            actual_name = find_alter_by_name(user_id, alter_name)
            if not actual_name:
                await ctx.send(f"❌ Alter '{alter_name}' does not exist.")
                return
                
            # Set autoproxy to front with the specified alter
            self.autoproxy_settings[user_id] = {
                "mode": "front",
                "alter": actual_name
            }
            await ctx.send(f"✅ Autoproxy set to **front** mode for alter: **{actual_name}**")
        elif mode == "latch":
            # Set autoproxy to latch mode
            self.autoproxy_settings[user_id] = {
                "mode": "latch",
                "last_used": None
            }
            await ctx.send("✅ Autoproxy set to **latch** mode. Messages will automatically proxy as your last used alter.")
        else:  # off
            # Disable autoproxy
            self.autoproxy_settings[user_id] = {
                "mode": "off"
            }
            await ctx.send("✅ Autoproxy has been **disabled**.")

    @commands.command(name="edit")
    async def edit_proxied(self, ctx, message_link: str = None, *, new_content: str = None):
        """Edit a recently proxied message."""
        user_id = str(ctx.author.id)

        # If no arguments given, show usage
        if not message_link and not new_content and not ctx.message.reference:
            await ctx.send("❌ Usage: `!edit [message_link] <new_content>` or reply to a message with `!edit <new_content>`")
            return

        # Get the target message ID
        target_message_id = None
        
        # If replying to a message, get that message ID
        if ctx.message.reference and ctx.message.reference.message_id:
            target_message_id = ctx.message.reference.message_id
            
        # If a message link was provided
        elif message_link:
            # Try to extract message ID from link
            match = re.search(r'/channels/\d+/\d+/(\d+)', message_link)
            if match:
                target_message_id = int(match.group(1))
                
        if not target_message_id:
            await ctx.send("❌ Could not determine which message to edit. Please provide a valid message link or reply to a message.")
            return

        # Check if this message was proxied by the user
        if target_message_id not in self.message_map or self.message_map[target_message_id] != user_id:
            await ctx.send("❌ You can only edit messages that you proxied.")
            return

        # Try to find the message in any of the channels
        target_message = None
        for channel in ctx.guild.text_channels:
            try:
                target_message = await channel.fetch_message(target_message_id)
                break
            except (discord.NotFound, discord.Forbidden):
                continue
                
        if not target_message:
            await ctx.send("❌ Could not find the message to edit.")
            return

        # If the message is a webhook message, edit it
        if target_message.webhook_id:
            webhooks = await ctx.channel.webhooks()
            webhook = next((w for w in webhooks if w.id == target_message.webhook_id), None)
            
            if webhook:
                try:
                    await webhook.edit_message(target_message_id, content=new_content)
                    await ctx.message.delete()  # Delete the command message
                except discord.NotFound:
                    await ctx.send("❌ This message is too old to edit (Discord limitation).")
                    return
                except discord.Forbidden:
                    await ctx.send("❌ I don't have permission to edit this webhook message.")
                    return
            else:
                await ctx.send("❌ Could not find the webhook that sent this message.")
                return
        else:
            await ctx.send("❌ This message was not sent by a webhook and cannot be edited.")
            return

    async def create_or_get_webhook(self, channel):
        """Create or retrieve a webhook for the channel."""
        # Check cache first
        if channel.id in self.webhook_cache:
            try:
                webhook = self.webhook_cache[channel.id]
                # Validate the webhook still exists
                try:
                    await webhook.fetch()
                    return webhook
                except (discord.NotFound, discord.HTTPException):
                    # Webhook was deleted, continue to recreation
                    del self.webhook_cache[channel.id]
            except Exception as e:
                print(f"Error checking cached webhook: {e}")
                
        # Create a new webhook
        try:
            webhooks = await channel.webhooks()
            # Look for existing PIXEL Proxy webhook
            webhook = next((w for w in webhooks if w.name == "PIXEL Proxy"), None)
            
            if not webhook:
                webhook = await channel.create_webhook(name="PIXEL Proxy")
                
            # Cache the webhook
            self.webhook_cache[channel.id] = webhook
            return webhook
        except discord.Forbidden:
            print(f"Missing permissions to manage webhooks in {channel.name}")
            return None
        except Exception as e:
            print(f"Error creating webhook: {e}")
            return None

    async def find_matching_proxy(self, message):
        """Check if a message matches any proxy patterns."""
        user_id = str(message.author.id)
        
        # Check autoproxy first
        autoproxy = self.autoproxy_settings.get(user_id, {"mode": "off"})
        
        # Skip cache lookup if we're using autoproxy
        if autoproxy["mode"] != "off" and not any(p for p in self.proxy_cache.get(user_id, []) if self._check_pattern_match(message.content, p["prefix"], p["suffix"])):
            # No explicit proxy tag found, try autoproxy
            if autoproxy["mode"] == "latch" and autoproxy.get("last_used"):
                last_alter = autoproxy["last_used"]
                alter_data = None
                
                # Find the alter data
                for alter_name, data in global_profiles.get(user_id, {}).get("alters", {}).items():
                    if alter_name == last_alter:
                        alter_data = data
                        break
                
                if alter_data:
                    return {
                        "name": last_alter,
                        "display_name": alter_data.get("displayname", last_alter),
                        "avatar": alter_data.get("avatar"),
                        "content": message.content,
                        "autoproxy": True,
                        "alter_data": alter_data
                    }
            
            elif autoproxy["mode"] == "front" and autoproxy.get("alter"):
                front_alter = autoproxy["alter"]
                alter_data = None
                
                # Find the alter data
                for alter_name, data in global_profiles.get(user_id, {}).get("alters", {}).items():
                    if alter_name == front_alter:
                        alter_data = data
                        break
                
                if alter_data:
                    return {
                        "name": front_alter,
                        "display_name": alter_data.get("displayname", front_alter),
                        "avatar": alter_data.get("avatar"),
                        "content": message.content,
                        "autoproxy": True,
                        "alter_data": alter_data
                    }
        
        # Check for explicit proxy tags
        for proxy_info in self.proxy_cache.get(user_id, []):
            prefix = proxy_info["prefix"]
            suffix = proxy_info["suffix"]
            
            if self._check_pattern_match(message.content, prefix, suffix):
                # Extract the actual message content
                content = self._extract_message_content(message.content, prefix, suffix)
                
                # Find the full alter data
                alter_data = None
                for alter_name, data in global_profiles.get(user_id, {}).get("alters", {}).items():
                    if alter_name == proxy_info["name"]:
                        alter_data = data
                        break
                
                # Update latch mode if applicable
                if autoproxy["mode"] == "latch":
                    self.autoproxy_settings[user_id]["last_used"] = proxy_info["name"]
                
                return {
                    "name": proxy_info["name"],
                    "display_name": proxy_info["display_name"],
                    "avatar": proxy_info["avatar"],
                    "content": content,
                    "autoproxy": False,
                    "alter_data": alter_data
                }
                
        return None

    def _check_pattern_match(self, content, prefix, suffix):
        """Check if a message matches a proxy pattern."""
        if not content:
            return False
            
        if prefix and suffix:
            return content.startswith(prefix) and content.endswith(suffix)
        elif prefix:
            return content.startswith(prefix)
        elif suffix:
            return content.endswith(suffix)
        return False

    def _extract_message_content(self, content, prefix, suffix):
        """Extract the actual message content from proxied text."""
        if prefix:
            content = content[len(prefix):]
        if suffix and content.endswith(suffix):
            content = content[:-len(suffix)]
        return content.strip()

    @commands.Cog.listener()
    async def on_message(self, message):
        # Skip if the message is from a bot
        if message.author.bot:
            return

        # Skip command messages
        if message.content.startswith('!'):
            return
            
        # Skip messages in DMs
        if not message.guild:
            return

        # Check if the message matches any proxy patterns
        proxy_match = await self.find_matching_proxy(message)
        if not proxy_match:
            return
            
        # Skip or apply proxy based on the message content
        if message.content == "\\":
            # Skip proxying this message (escape sequence)
            return

        # Delete the original message first
        try:
            await message.delete()
        except discord.Forbidden:
            print(f"⚠️ Missing permissions to delete message in {message.channel.name}")
            return  # Don't proceed with proxying if we can't delete the original
            
        # Get or create a webhook for this channel
        webhook = await self.create_or_get_webhook(message.channel)
        if not webhook:
            try:
                await message.channel.send("❌ I need the 'Manage Webhooks' permission to proxy messages in this channel.")
            except discord.Forbidden:
                pass
            return
            
        # Set the avatar if one exists
        avatar_url = proxy_match["avatar"]
        
        # Get the color for embeds (if any embeds in the message)
        color = proxy_match.get("alter_data", {}).get("color", 0x8A2BE2)
        
        try:
            # Create a webhook message with the alter's identity
            proxy_message = await webhook.send(
                content=proxy_match["content"],
                username=proxy_match["display_name"],
                avatar_url=avatar_url,
                allowed_mentions=discord.AllowedMentions.all(),
                wait=True,  # We need the message object for the message map
                embeds=[discord.Embed(description=embed.description, title=embed.title, color=color) 
                        for embed in message.embeds] if message.embeds else None,
                files=[await a.to_file() for a in message.attachments] if message.attachments else None
            )
            
            # Store this message in the message map for editing later
            self.message_map[proxy_message.id] = str(message.author.id)

        except Exception as e:
            print(f"Error sending proxied message: {e}")
            try:
                await message.channel.send(f"❌ Error sending proxied message: {e}")
            except:
                pass

async def setup(bot):
    await bot.add_cog(ProxyCommands(bot))

# For discord.py v2
async def async_setup(bot):
    cog = ProxyCommands(bot)
    await bot.add_cog(cog)
