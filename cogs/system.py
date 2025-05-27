import json
import io
import uuid
import asyncio
import logging
from datetime import datetime

import discord
from discord.ext import commands

from utils.mongodb import db

logger = logging.getLogger(__name__)

class SystemCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="create_system")
    async def create_system(self, ctx, *, system_name: str):
        """Create a new system."""
        logger.info(f"Instance {self.bot.instance_id} processing create_system for {ctx.author}")
        user_id = str(ctx.author.id)

        profile = db.get_profile(user_id)
        # If existing profile has a system key, user already has a system
        if profile.get("system"):
            await ctx.send("❌ You already have a system. Use `!edit_system` to modify it.")
            return

        # Generate unique system ID
        system_id = str(uuid.uuid4())[:8]
        created_date = datetime.utcnow().isoformat()

        # Build new profile structure
        new_profile = {
            "user_id": user_id,
            "system": {
                "name": system_name,
                "description": None,
                "avatar": None,
                "banner": None,
                "pronouns": None,
                "color": None,
                "linked_accounts": [ctx.author.name],
                "system_id": system_id,
                "created_date": created_date
            },
            "alters": {},
            "folders": {}
        }
        db.save_profile(user_id, new_profile)

        embed = discord.Embed(
            title="✅ System Created Successfully",
            description=(
                f"System **{system_name}** has been created!\n"
                f"System ID: `{system_id}`"
            ),
            color=0x8A2BE2
        )
        await ctx.send(embed=embed)

    @commands.command(name="system")
    async def show_system(self, ctx):
        """Show system information."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        system_data = profile.get("system")

        if not system_data:
            await ctx.send("❌ You don't have a system set up. Use `!create_system <name>` to create one.")
            return

        # Normalize color value
        def normalize_color(c):
            try:
                if c and isinstance(c, str):
                    return int(c.lstrip('#'), 16)
            except:
                pass
            return 0x8A2BE2

        color_val = normalize_color(system_data.get("color"))
        embed = discord.Embed(title=f"🏷️ {system_data['name']}", color=color_val)

        # Optionally add fields
        if system_data.get('color'):
            embed.add_field(name="🎨 Color", value=system_data['color'], inline=True)
        if system_data.get('tag'):
            embed.add_field(name="🏷️ Proxy Tag", value=f"`{system_data['tag']}`", inline=True)
        linked = system_data.get('linked_accounts', [])
        if linked:
            embed.add_field(name="🔗 Linked Accounts", value=", ".join(linked), inline=False)
        desc = system_data.get('description') or 'No description provided.'
        embed.add_field(name="📝 Description", value=desc, inline=False)
        if system_data.get('avatar'):
            embed.set_thumbnail(url=system_data['avatar'])
        if system_data.get('banner'):
            embed.set_image(url=system_data['banner'])
        if system_data.get('pronouns'):
            embed.add_field(name="👤 Pronouns", value=system_data['pronouns'], inline=True)

        created = datetime.fromisoformat(system_data['created_date'])
        footer = f"System ID: {system_data['system_id']} | Created on {created.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        embed.set_footer(text=footer)

        await ctx.send(embed=embed)

    @commands.command(name="edit_system")
    async def edit_system(self, ctx):
        """Edit the current system."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        system_data = profile.get("system")

        if not system_data:
            await ctx.send("❌ You don't have a system. Use `!create_system <name>` to create one.")
            return

        embed = discord.Embed(
            title="⚙️ System Edit Menu",
            description="React with the corresponding emoji to edit a field:",
            color=0x8A2BE2
        )
        options = {
            '🏷️': 'name',
            '📝': 'description',
            '🖼️': 'avatar',
            '🎨': 'banner',
            '👤': 'pronouns',
            '🌈': 'color'
        }
        for emoji, field in options.items():
            embed.add_field(name=emoji, value=field.capitalize(), inline=True)

        msg = await ctx.send(embed=embed)
        for emoji in options:
            await msg.add_reaction(emoji)

        def check(reaction, user):
            return user == ctx.author and reaction.message.id == msg.id and str(reaction.emoji) in options

        try:
            reaction, _ = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            field = options[str(reaction.emoji)]
            await self._edit_field(ctx, user_id, field)
        except asyncio.TimeoutError:
            await ctx.send("⏰ Edit menu timed out.")

    async def _edit_field(self, ctx, user_id: str, field: str):
        prompts = {
            'name': 'Enter the new system name:',
            'description': 'Enter the new description:',
            'avatar': 'Enter the new avatar URL:',
            'banner': 'Enter the new banner URL:',
            'pronouns': 'Enter the new pronouns:',
            'color': 'Enter the new color (hex, e.g., #FF5733):'
        }
        await ctx.send(prompts[field])

        def mcheck(m):
            return m.author.id == int(user_id) and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', timeout=60.0, check=mcheck)
            profile = db.get_profile(user_id)
            sys = profile.get('system', {})
            value = msg.content.strip()
            if field == 'color' and not value.startswith('#'):
                return await ctx.send("❌ Invalid color format. Use hex like #FF5733.")
            sys[field] = value
            profile['system'] = sys
            db.save_profile(user_id, profile)
            await ctx.send(f"✅ System {field} updated!")
        except asyncio.TimeoutError:
            await ctx.send("⏰ Edit timed out.")

    @commands.command(name="delete_system")
    async def delete_system(self, ctx):
        """Delete the current system permanently."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        if not profile.get('system'):
            return await ctx.send("❌ No system to delete.")

        embed = discord.Embed(
            title="⚠️ Delete System",
            description="React ✅ to confirm deletion or ❌ to cancel.",
            color=0xFF0000
        )
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('✅')
        await msg.add_reaction('❌')

        def check(r, u):
            return u == ctx.author and r.message.id == msg.id and str(r.emoji) in ['✅','❌']

        try:
            r, _ = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            if str(r.emoji) == '✅':
                db.delete_profile(user_id)
                return await ctx.send("✅ Your system has been deleted.")
            await ctx.send("❌ Deletion cancelled.")
        except asyncio.TimeoutError:
            await ctx.send("⏰ Deletion timed out.")

    @commands.command(name="export_system")
    async def export_system(self, ctx):
        """Export your system data as a JSON file."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        if not profile:
            return await ctx.send("❌ No system to export.")

        # Remove Mongo _id
        profile_clean = {k:v for k,v in profile.items() if k != '_id'}
        json_data = json.dumps(profile_clean, default=str, indent=4)
        file = discord.File(io.BytesIO(json_data.encode()), filename=f"system_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
        await ctx.send("✅ Here is your system backup:", file=file)

    @commands.command(name="import_system")
    async def import_system(self, ctx):
        """Import system data from a JSON file."""
        if not ctx.message.attachments:
            return await ctx.send("❌ Attach a JSON file.")
        att = ctx.message.attachments[0]
        if not att.filename.endswith('.json'):
            return await ctx.send("❌ Please provide a .json file.")

        data = await att.read()
        try:
            sys_data = json.loads(data)
        except json.JSONDecodeError:
            return await ctx.send("❌ Invalid JSON.")

        if not all(key in sys_data for key in ('system','alters','folders')):
            return await ctx.send("❌ Missing keys in system data.")

        confirm = await ctx.send("⚠️ This will overwrite your system. React ✅ to confirm.")
        await confirm.add_reaction('✅')
        def c(r,u): return u==ctx.author and r.message.id==confirm.id and str(r.emoji)=='✅'
        try:
            await self.bot.wait_for('reaction_add', timeout=60.0, check=c)
            sys_data['user_id'] = str(ctx.author.id)
            db.save_profile(str(ctx.author.id), sys_data)
            await ctx.send("✅ System imported!")
        except asyncio.TimeoutError:
            await ctx.send("⏰ Import timed out.")

    @commands.command(name="tag")
    async def set_system_tag(self, ctx, *, tag: str = None):
        """Set or view the system proxy tag."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        sys = profile.get('system') or {}
        if not sys:
            return await ctx.send("❌ You need a system first.")

        if tag is None:
            current = sys.get('tag')
            msg = f"Current tag: `{current}`" if current else "No tag set. Use `!tag <tag>` to set."
            return await ctx.send(msg)

        if len(tag)>20:
            return await ctx.send("❌ Tag must be ≤20 characters.")
        sys['tag'] = tag
        profile['system'] = sys
        db.save_profile(user_id, profile)
        await ctx.send(f"🏷️ System tag updated to `{tag}`")

async def setup(bot):
    await bot.add_cog(SystemCommands(bot))
