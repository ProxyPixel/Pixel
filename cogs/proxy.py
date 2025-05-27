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
        self.proxy_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.autoproxy_settings: Dict[str, Dict[str, Any]] = {}
        self.message_map: Dict[str, int] = {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._webhook_cache: Dict[str, discord.Webhook] = {}
        self._webhook_locks: Dict[str, asyncio.Lock] = {}
        self._lock = asyncio.Lock()
        self._webhook_cleanup_task: Optional[asyncio.Task] = None
        self._last_webhook_cleanup = datetime.utcnow()
        self._message_cache: Dict[int, Dict[str, Any]] = {}

    async def get_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    def cog_unload(self):
        if self._session and not self._session.closed:
            asyncio.create_task(self._session.close())
        if self._webhook_cleanup_task:
            self._webhook_cleanup_task.cancel()

    async def initialize_cache(self):
        try:
            # Check if MongoDB collections are available
            if not db.profiles or not db.autoproxy:
                logger.warning("⚠️ MongoDB collections not available - proxy cache initialization skipped")
                return
                
            # Load all proxy tags
            async for user_data in db.profiles.find({}):
                user_id = user_data.get('user_id')
                if not user_id:
                    continue
                proxies = []
                for alter_name, alter_data in user_data.get('alters', {}).items():
                    proxy_tag = alter_data.get('proxy')
                    if proxy_tag:
                        prefix, suffix = self.parse_proxy_pattern(proxy_tag)
                        proxies.append({
                            'name': alter_name,
                            'prefix': prefix,
                            'suffix': suffix,
                            'display_name': alter_data.get('displayname', alter_name),
                            'avatar': alter_data.get('proxy_avatar') or alter_data.get('avatar'),
                            'proxy_tag': proxy_tag
                        })
                if proxies:
                    self.proxy_cache[user_id] = proxies

            # Load autoproxy settings
            async for settings in db.autoproxy.find({}):
                user_id = settings.get('user_id')
                if user_id:
                    self.autoproxy_settings[user_id] = settings

            self._webhook_cleanup_task = asyncio.create_task(self._cleanup_webhooks_periodically())
            logger.info("✅ Proxy cache initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize proxy cache: {e}")
            logger.info("🔄 Proxy cog will continue without cache - features may be limited until database connection is restored")

    async def _cleanup_webhooks_periodically(self):
        try:
            while True:
                await asyncio.sleep(300)
                now = datetime.utcnow()
                for key, webhook in list(self._webhook_cache.items()):
                    try:
                        await webhook.fetch()
                    except (discord.NotFound, discord.Forbidden):
                        del self._webhook_cache[key]
                        if key in self._webhook_locks:
                            del self._webhook_locks[key]
                self._last_webhook_cleanup = now
        except asyncio.CancelledError:
            pass

    async def create_or_get_webhook(self, channel: discord.TextChannel) -> Optional[discord.Webhook]:
        cache_key = f"{channel.guild.id}_{channel.id}"
        perms = channel.permissions_for(channel.guild.me)
        if not (perms.manage_webhooks and perms.manage_messages):
            await channel.send("❌ Missing **Manage Webhooks** or **Manage Messages** permissions.")
            return None

        if cache_key not in self._webhook_locks:
            self._webhook_locks[cache_key] = asyncio.Lock()

        if key := self._webhook_cache.get(cache_key):
            try:
                await key.fetch()
                return key
            except discord.NotFound:
                del self._webhook_cache[cache_key]

        async with self._webhook_locks[cache_key]:
            data = db.get_webhook(channel.id, channel.guild.id)
            if data:
                try:
                    webhook = discord.Webhook.partial(data['webhook_id'], data['webhook_token'], session=await self.get_session())
                    await webhook.fetch()
                    self._webhook_cache[cache_key] = webhook
                    return webhook
                except discord.NotFound:
                    db.delete_webhook(channel.id, channel.guild.id)

            # Create new webhook
            try:
                webhook = await channel.create_webhook(name="PIXEL Proxy")
                db.save_webhook(channel.id, channel.guild.id, webhook.id, webhook.token)
                self._webhook_cache[cache_key] = webhook
                return webhook
            except discord.Forbidden:
                await channel.send("❌ Cannot create webhook; missing permissions.")
                return None
            except Exception as e:
                logger.error(f"Error creating webhook: {e}")
                return None

    def parse_proxy_pattern(self, pattern: str) -> Tuple[Optional[str], Optional[str]]:
        if not pattern:
            return None, None
        if pattern.endswith("None"):
            pattern = pattern.replace("None", "")
        if "TEXT" in pattern:
            pre, suf = pattern.split("TEXT", 1)
            return (pre or None, suf or None)
        if ":" in pattern.lower():
            parts = pattern.split(":", 1)
            return (f"{parts[0]}:", None)
        return (pattern.strip(), None)

    @commands.command(name="set_proxy")
    async def set_proxy(self, ctx, alter_name: str = None, *, proxy_tag: str = None):
        if not alter_name or not proxy_tag:
            return await ctx.send("❌ Usage: `!set_proxy <alter_name> <proxy_tag>`")
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        if not profile.get('alters'):
            return await ctx.send("❌ You don't have any alters set up.")
        actual = find_alter_by_name(profile, alter_name)
        if not actual:
            return await ctx.send(f"❌ Alter '{alter_name}' not found.")
        if "text" in proxy_tag.lower() and "TEXT" not in proxy_tag:
            proxy_tag = proxy_tag.replace("text", "TEXT")
        if proxy_tag.endswith("None"):
            proxy_tag = proxy_tag.replace("None", "")
        profile['alters'][actual]['proxy'] = proxy_tag
        db.save_profile(user_id, profile)
        await self.initialize_cache()
        pre, suf = self.parse_proxy_pattern(proxy_tag)
        example = f"{f'`{pre}`' if pre else ''}Your message{f'`{suf}`' if suf else ''}"
        embed = create_embed(
            title="✅ Proxy Set Successfully",
            description=(
                f"Proxy for **{actual}** set to `{proxy_tag}`. When you type {example}, bot proxies as **{actual}**."
            )
        )
        await ctx.send(embed=embed)

    @commands.command(name="proxy")
    async def proxy_management(self, ctx, action: str, alter_name: str = None, *, proxy_tag: str = None):
        if action.lower() == 'remove':
            user_id = str(ctx.author.id)
            profile = db.get_profile(user_id)
            if not profile.get('alters'):
                return await ctx.send("❌ No alters to remove proxy from.")
            actual = find_alter_by_name(profile, alter_name)
            if not actual:
                return await ctx.send(f"❌ Alter '{alter_name}' not found.")
            profile['alters'][actual].pop('proxy', None)
            db.save_profile(user_id, profile)
            await self.initialize_cache()
            return await ctx.send(f"✅ Removed proxy from **{actual}**.")
        if action.lower() == 'list':
            user_id = str(ctx.author.id)
            profile = db.get_profile(user_id)
            alters = profile.get('alters', {})
            proxies = [f"**{an}**: `{ad['proxy']}`" for an, ad in alters.items() if ad.get('proxy')]
            if proxies:
                return await ctx.send(embed=create_embed("Your Proxies", "\n".join(proxies)))
            return await ctx.send("❌ No proxies set.")
        return await ctx.send("❌ Invalid action. Use `remove` or `list`.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.content.startswith(self.bot.command_prefix):
            return
        if not message.guild:
            return
        async with self._lock:
            bl = db.get_blacklist(str(message.guild.id))
            if message.channel.id in bl.get('channels', []) or \
               (message.channel.category and message.channel.category.id in bl.get('categories', [])):
                return
            alter_data, alter_name = await self.find_matching_proxy(message)
            if not alter_data:
                return
            webhook = await self.create_or_get_webhook(message.channel)
            if not webhook:
                return
            content = message.content
            is_manual = alter_data.get('_is_manual_proxy', False)
            if is_manual:
                pre, suf = self.parse_proxy_pattern(alter_data['proxy'])
                content = self._extract_message_content(content, pre, suf)
            if not content.strip() and not message.attachments:
                return
            user_id = str(message.author.id)
            profile = db.get_profile(user_id)
            tag = profile.get('system', {}).get('tag', '').strip()
            system_tag = f" {tag}" if tag else ''
            display = alter_data.get('display_name')
            webhook_name = f"{display}{system_tag}"[:80]
            avatar_url = alter_data.get('proxy_avatar') or alter_data.get('avatar') or profile.get('system', {}).get('avatar')
            files = []
            for att in message.attachments:
                data = await att.read()
                files.append(discord.File(io.BytesIO(data), att.filename, spoiler=att.is_spoiler()))
            proxied = await webhook.send(content=content or None, username=webhook_name, avatar_url=avatar_url, files=files, wait=True)
            try:
                await message.delete()
            except:
                pass
            if is_manual:
                key = f"{user_id}_{message.guild.id}"
                ap = db.get_autoproxy(key)
                if ap.get('mode') == 'latch':
                    ap['last_alter'] = alter_name
                    ap['guild_id'] = str(message.guild.id)
                    db.save_autoproxy(key, ap)
            self._message_cache[proxied.id] = {'original_author': message.author.id, 'alter_name': alter_name, 'timestamp': datetime.utcnow()}

    def _check_pattern_match(self, content: str, prefix: Optional[str], suffix: Optional[str]) -> bool:
        if prefix and not content.startswith(prefix):
            return False
        if suffix and not content.endswith(suffix):
            return False
        return bool(self._extract_message_content(content, prefix, suffix).strip())

    def _extract_message_content(self, content: str, prefix: Optional[str], suffix: Optional[str]) -> str:
        if prefix:
            content = content[len(prefix):].lstrip()
        if suffix:
            content = content[:-len(suffix)].rstrip()
        return content

    async def find_matching_proxy(self, message: discord.Message) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        user_id = str(message.author.id)
        guild_id = str(message.guild.id)
        profile = db.get_profile(user_id) or {}
        # Manual patterns
        for an, ad in profile.get('alters', {}).items():
            if (pt := ad.get('proxy')):
                pre, suf = self.parse_proxy_pattern(pt)
                if self._check_pattern_match(message.content, pre, suf):
                    ad_copy = ad.copy(); ad_copy['_is_manual_proxy'] = True
                    return ad_copy, an
        # Autoproxy
        key = f"{user_id}_{guild_id}"
        ap = db.get_autoproxy(key)
        if ap.get('enabled'):
            mode = ap.get('mode')
            name = ap.get('last_alter') if mode == 'latch' else ap.get('fronter') if mode == 'front' else ap.get('member')
            if name in profile.get('alters', {}):
                ad_copy = profile['alters'][name].copy(); ad_copy['_is_manual_proxy'] = False
                return ad_copy, name
        return None, None

async def setup(bot):
    cog = ProxyCommands(bot)
    try:
        await cog.initialize_cache()
    except Exception as e:
        logger.error(f"❌ Failed proxy cache init: {e}")
    await bot.add_cog(cog)
    print("✅ Proxy cog loaded successfully")
