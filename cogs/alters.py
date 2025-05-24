import discord
from discord.ext import commands
from utils.profiles import load_profiles, save_profiles
from utils.helpers import find_alter_by_name, create_embed
import asyncio
import uuid
from datetime import datetime

global_profiles = load_profiles()

class AlterCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="create")
    async def create_alter(self, ctx, name: str, pronouns: str = None, *, description: str = None):
        """Create a new profile."""
        user_id = str(ctx.author.id)

        if user_id not in global_profiles:
            global_profiles[user_id] = {"system": {}, "alters": {}, "folders": {}}

        if name in global_profiles[user_id]["alters"]:
            await ctx.send(f"❌ An alter with the name **{name}** already exists.")
            return

        # Generate unique alter ID
        alter_id = str(uuid.uuid4())[:8]

        global_profiles[user_id]["alters"][name] = {
            "name": name,
            "alter_id": alter_id,
            "displayname": name,
            "pronouns": pronouns,
            "description": description,
            "avatar": None,
            "banner": None,
            "proxy": None,
            "proxy_avatar": None,
            "aliases": [],
            "color": None,
            "created_date": datetime.utcnow().isoformat()
        }
        save_profiles(global_profiles)
        
        embed = discord.Embed(
            title="✅ Alter Created Successfully",
            description=f"Alter **{name}** has been created!\nAlter ID: `{alter_id}`",
            color=0x8A2BE2
        )
        if pronouns:
            embed.add_field(name="Pronouns", value=pronouns, inline=True)
        if description:
            embed.add_field(name="Description", value=description, inline=False)
            
        await ctx.send(embed=embed)

    @commands.command(name="show")
    async def show_alter(self, ctx, *, name: str):
        """Show a profile, including avatars, banners, and colors."""
        user_id = str(ctx.author.id)
        
        actual_name = find_alter_by_name(user_id, name)
        if not actual_name:
            await ctx.send(f"❌ Alter '{name}' does not exist.")
            return

        alter_data = global_profiles[user_id]["alters"][actual_name]
        
        # Use alter's color or default
        color = int(alter_data.get('color', '0x8A2BE2'), 16) if alter_data.get('color') else 0x8A2BE2
        
        embed = discord.Embed(
            title=f"👤 {alter_data.get('displayname', actual_name)}",
            color=color
        )

        # Basic info
        if alter_data.get('pronouns'):
            embed.add_field(name="🏷️ Pronouns", value=alter_data['pronouns'], inline=True)
        
        if alter_data.get('description'):
            embed.add_field(name="📝 Description", value=alter_data['description'], inline=False)

        # Proxy info
        if alter_data.get('proxy'):
            embed.add_field(name="🗨️ Proxy Tags", value=f"`{alter_data['proxy']}`", inline=True)

        # Aliases
        if alter_data.get('aliases'):
            aliases_text = ", ".join(alter_data['aliases'])
            embed.add_field(name="🔗 Aliases", value=aliases_text, inline=False)

        # Color
        if alter_data.get('color'):
            embed.add_field(name="🎨 Color", value=alter_data['color'], inline=True)

        # Avatar
        if alter_data.get('avatar'):
            embed.set_thumbnail(url=alter_data['avatar'])

        # Banner
        if alter_data.get('banner'):
            embed.set_image(url=alter_data['banner'])

        # Proxy avatar note
        if alter_data.get('proxy_avatar'):
            embed.add_field(name="🖼️ Proxy Avatar", value="Set (different from display avatar)", inline=True)

        embed.set_footer(text=f"Internal name: {actual_name}")
        await ctx.send(embed=embed)

    @commands.command(name="list_profiles")
    async def list_profiles(self, ctx):
        """List all profiles in the current system."""
        user_id = str(ctx.author.id)

        if user_id not in global_profiles or not global_profiles[user_id].get("alters"):
            await ctx.send("❌ You don't have any alters. Use `!create <name> <pronouns>` to create one.")
            return

        alters = global_profiles[user_id]["alters"]
        
        embed = discord.Embed(
            title="👥 Your Alters",
            description=f"Total: {len(alters)} alter(s)",
            color=0x8A2BE2
        )

        for i, (name, data) in enumerate(alters.items(), 1):
            display_name = data.get('displayname', name)
            pronouns = data.get('pronouns', 'Not set')
            proxy_info = f" • Proxy: `{data['proxy']}`" if data.get('proxy') else ""
            
            embed.add_field(
                name=f"{i}. {display_name}",
                value=f"Pronouns: {pronouns}{proxy_info}",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command(name="edit")
    async def edit_alter(self, ctx, *, name: str):
        """Edit an existing profile (name, displayname, pronouns, description, avatar, banner, proxy, color, proxy avatar)."""
        user_id = str(ctx.author.id)
        
        actual_name = find_alter_by_name(user_id, name)
        if not actual_name:
            await ctx.send(f"❌ Alter '{name}' does not exist.")
            return

        embed = discord.Embed(
            title=f"⚙️ Edit {actual_name}",
            description="React with the corresponding emoji to edit that field:",
            color=0x8A2BE2
        )
        embed.add_field(name="🏷️ Display Name", value="Edit display name", inline=True)
        embed.add_field(name="👤 Pronouns", value="Edit pronouns", inline=True)
        embed.add_field(name="📝 Description", value="Edit description", inline=True)
        embed.add_field(name="🖼️ Avatar", value="Edit avatar URL", inline=True)
        embed.add_field(name="🎨 Banner", value="Edit banner URL", inline=True)
        embed.add_field(name="🗨️ Proxy", value="Edit proxy tags", inline=True)
        embed.add_field(name="🌈 Color", value="Edit color (hex)", inline=True)
        embed.add_field(name="👥 Proxy Avatar", value="Edit proxy avatar", inline=True)

        message = await ctx.send(embed=embed)
        
        # Add reaction emojis
        reactions = ['🏷️', '👤', '📝', '🖼️', '🎨', '🗨️', '🌈', '👥']
        for reaction in reactions:
            await message.add_reaction(reaction)

        def check(reaction, user):
            return user == ctx.author and reaction.message.id == message.id and str(reaction.emoji) in reactions

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            
            if str(reaction.emoji) == '🏷️':
                await self._edit_alter_field(ctx, actual_name, 'displayname', 'Enter the new display name:')
            elif str(reaction.emoji) == '👤':
                await self._edit_alter_field(ctx, actual_name, 'pronouns', 'Enter the new pronouns:')
            elif str(reaction.emoji) == '📝':
                await self._edit_alter_field(ctx, actual_name, 'description', 'Enter the new description:')
            elif str(reaction.emoji) == '🖼️':
                await self._edit_alter_field(ctx, actual_name, 'avatar', 'Enter the new avatar URL:')
            elif str(reaction.emoji) == '🎨':
                await self._edit_alter_field(ctx, actual_name, 'banner', 'Enter the new banner URL:')
            elif str(reaction.emoji) == '🗨️':
                await self._edit_alter_field(ctx, actual_name, 'proxy', 'Enter the new proxy tags (e.g., "A: TEXT" or "TEXT :a"):')
            elif str(reaction.emoji) == '🌈':
                await self._edit_alter_field(ctx, actual_name, 'color', 'Enter the new color (hex format, e.g., #FF5733):')
            elif str(reaction.emoji) == '👥':
                await self._edit_alter_field(ctx, actual_name, 'proxy_avatar', 'Enter the new proxy avatar URL:')

        except asyncio.TimeoutError:
            await ctx.send("⏰ Edit menu timed out.")

    async def _edit_alter_field(self, ctx, alter_name, field, prompt):
        """Helper function to edit a specific alter field."""
        await ctx.send(prompt)
        
        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        try:
            response = await self.bot.wait_for('message', timeout=60.0, check=check)
            user_id = str(ctx.author.id)
            
            if field == 'color':
                # Validate hex color
                color_value = response.content.strip()
                if not color_value.startswith('#') or len(color_value) != 7:
                    await ctx.send("❌ Invalid color format. Please use hex format like #FF5733")
                    return
                global_profiles[user_id]["alters"][alter_name][field] = color_value
            else:
                global_profiles[user_id]["alters"][alter_name][field] = response.content.strip()
            
            save_profiles(global_profiles)
            await ctx.send(f"✅ {alter_name}'s {field} updated successfully!")
            
        except asyncio.TimeoutError:
            await ctx.send("⏰ Edit timed out.")

    @commands.command(name="delete")
    async def delete_alter(self, ctx, *, name: str):
        """Delete a profile."""
        user_id = str(ctx.author.id)

        actual_name = find_alter_by_name(user_id, name)
        if not actual_name:
            await ctx.send(f"❌ Alter '{name}' does not exist.")
            return

        # Confirmation
        embed = discord.Embed(
            title="⚠️ Delete Alter",
            description=f"Are you sure you want to delete **{actual_name}**? This action cannot be undone.\n\nReact with ✅ to confirm or ❌ to cancel.",
            color=0xFF0000
        )
        message = await ctx.send(embed=embed)
        
        await message.add_reaction('✅')
        await message.add_reaction('❌')

        def check(reaction, user):
            return user == ctx.author and reaction.message.id == message.id and str(reaction.emoji) in ['✅', '❌']

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == '✅':
                del global_profiles[user_id]["alters"][actual_name]
                save_profiles(global_profiles)
                await ctx.send(f"🗑️ Alter '{actual_name}' deleted successfully!")
            else:
                await ctx.send("❌ Deletion cancelled.")
                
        except asyncio.TimeoutError:
            await ctx.send("⏰ Confirmation timed out. Deletion cancelled.")

    @commands.command(name="alias")
    async def add_alias(self, ctx, name: str, *, alias: str):
        """Add an alias to a profile."""
        user_id = str(ctx.author.id)
        
        actual_name = find_alter_by_name(user_id, name)
        if not actual_name:
            await ctx.send(f"❌ Alter '{name}' does not exist.")
            return

        aliases = global_profiles[user_id]["alters"][actual_name].setdefault("aliases", [])
        
        if alias in aliases:
            await ctx.send(f"❌ Alias '{alias}' already exists for {actual_name}.")
            return

        aliases.append(alias)
        save_profiles(global_profiles)
        await ctx.send(f"✅ Added alias '{alias}' to {actual_name}.")

    @commands.command(name="remove_alias")
    async def remove_alias(self, ctx, name: str, *, alias: str):
        """Remove an alias from a profile."""
        user_id = str(ctx.author.id)
        
        actual_name = find_alter_by_name(user_id, name)
        if not actual_name:
            await ctx.send(f"❌ Alter '{name}' does not exist.")
            return

        aliases = global_profiles[user_id]["alters"][actual_name].get("aliases", [])
        
        if alias not in aliases:
            await ctx.send(f"❌ Alias '{alias}' does not exist for {actual_name}.")
            return

        aliases.remove(alias)
        save_profiles(global_profiles)
        await ctx.send(f"✅ Removed alias '{alias}' from {actual_name}.")

    @commands.command(name="proxyavatar")
    async def set_proxy_avatar(self, ctx, name: str, *, avatar_url: str = None):
        """Set a separate avatar for proxying."""
        user_id = str(ctx.author.id)

        actual_name = find_alter_by_name(user_id, name)
        if not actual_name:
            await ctx.send(f"❌ Alter '{name}' does not exist.")
            return

        if avatar_url:
            global_profiles[user_id]["alters"][actual_name]["proxy_avatar"] = avatar_url
            save_profiles(global_profiles)
            await ctx.send(f"✅ Proxy avatar set for {actual_name}.")
        else:
            # Remove proxy avatar
            global_profiles[user_id]["alters"][actual_name]["proxy_avatar"] = None
            save_profiles(global_profiles)
            await ctx.send(f"✅ Proxy avatar removed for {actual_name}.")

async def setup(bot):
    await bot.add_cog(AlterCommands(bot))
