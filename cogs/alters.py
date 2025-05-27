import discord
from discord.ext import commands
from utils.mongodb import db
from utils.helpers import find_alter_by_name, create_embed
import asyncio
import uuid
from datetime import datetime

class AlterCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="create")
    async def create_alter(self, ctx, name: str, pronouns: str = None, *, description: str = None):
        """Create a new profile."""
        
        user_id = str(ctx.author.id)

        # Get or create profile
        profile = db.get_profile(user_id)
        if not profile:
            profile = {"user_id": user_id, "system": {}, "alters": {}, "folders": {}}

        if name in profile["alters"]:
            await ctx.send(f"❌ An alter with the name **{name}** already exists.")
            return

        # Generate unique alter ID
        alter_id = str(uuid.uuid4())[:8]

        profile["alters"][name] = {
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
        db.save_profile(user_id, profile)
        
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
        
        profile = db.get_profile(user_id)
        if not profile:
            await ctx.send("❌ You don't have any alters.")
            return

        actual_name = find_alter_by_name(profile, name)
        if not actual_name:
            await ctx.send(f"❌ Alter '{name}' does not exist.")
            return

        alter_data = profile["alters"][actual_name]
        
        # Helper function to normalize color format
        def normalize_color(color_str):
            if not color_str:
                return 0x8A2BE2  # Default color
            # Remove # if present and ensure it's a valid hex color
            color_clean = color_str.replace('#', '') if color_str.startswith('#') else color_str
            try:
                # Validate it's a valid hex color
                return int(color_clean, 16)
            except ValueError:
                return 0x8A2BE2  # Default color
        
        # Use alter's color or default
        color = normalize_color(alter_data.get('color'))
        
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
            # Clean up the proxy display - remove None suffixes and show proper format
            proxy_display = alter_data['proxy']
            if proxy_display.endswith('None'):
                proxy_display = proxy_display.replace('None', '')
            embed.add_field(name="🗨️ Proxy Tags", value=f"`{proxy_display}`", inline=True)

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
        """List all profiles in the current system with pagination."""
        
        user_id = str(ctx.author.id)

        profile = db.get_profile(user_id)
        if not profile or not profile.get("alters"):
            await ctx.send("❌ You don't have any alters. Use `!create <name> <pronouns>` to create one.")
            return

        alters = profile["alters"]
        alter_list = list(alters.items())
        
        # Pagination settings
        per_page = 10  # Show 10 alters per page
        total_pages = (len(alter_list) + per_page - 1) // per_page
        current_page = 1
        
        def create_page_embed(page_num):
            start_idx = (page_num - 1) * per_page
            end_idx = min(start_idx + per_page, len(alter_list))
            
            embed = discord.Embed(
                title="👥 Your Alters",
                description=f"Total: {len(alters)} alter(s) • Page {page_num}/{total_pages}",
                color=0x8A2BE2
            )

            for i in range(start_idx, end_idx):
                name, data = alter_list[i]
                display_name = data.get('displayname') or name
                pronouns = data.get('pronouns') or 'Not set'
                proxy_info = f" • Proxy: `{data['proxy']}`" if data.get('proxy') else ""
                
                embed.add_field(
                    name=f"{i + 1}. {display_name}",
                    value=f"Pronouns: {pronouns}{proxy_info}",
                    inline=False
                )
            
            if total_pages > 1:
                embed.set_footer(text=f"Use ⬅️ and ➡️ to navigate pages")
            
            return embed

        # Send initial embed
        embed = create_page_embed(current_page)
        message = await ctx.send(embed=embed)
        
        # Add reactions for pagination if there are multiple pages AND we're in a guild
        if total_pages > 1 and ctx.guild:
            await message.add_reaction('⬅️')
            await message.add_reaction('➡️')
            
            def check(reaction, user):
                return (user == ctx.author and 
                       reaction.message.id == message.id and 
                       str(reaction.emoji) in ['⬅️', '➡️'])
            
            # Handle pagination
            while True:
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                    
                    if str(reaction.emoji) == '⬅️' and current_page > 1:
                        current_page -= 1
                    elif str(reaction.emoji) == '➡️' and current_page < total_pages:
                        current_page += 1
                    else:
                        # Remove the reaction if it's invalid
                        try:
                            await message.remove_reaction(reaction.emoji, user)
                        except discord.Forbidden:
                            pass  # Can't remove reactions in DMs
                        continue
                    
                    # Update the embed
                    new_embed = create_page_embed(current_page)
                    await message.edit(embed=new_embed)
                    
                    # Remove the user's reaction
                    try:
                        await message.remove_reaction(reaction.emoji, user)
                    except discord.Forbidden:
                        pass  # Can't remove reactions in DMs
                    
                except asyncio.TimeoutError:
                    # Remove reactions when timeout
                    try:
                        await message.clear_reactions()
                    except:
                        pass
                    break
        elif total_pages > 1:
            # In DMs, just send a message about using page numbers
            await ctx.send(f"📄 This list has {total_pages} pages. Since this is a DM, reactions aren't available. You can use `!list_profiles` again to see the first page.")

    @commands.command(name="edit")
    async def edit_alter(self, ctx, *, name: str):
        """Edit an existing profile (name, displayname, pronouns, description, avatar, banner, proxy, color, proxy avatar)."""
        
        user_id = str(ctx.author.id)
        
        profile = db.get_profile(user_id)
        if not profile:
            await ctx.send("❌ You don't have any alters.")
            return

        actual_name = find_alter_by_name(profile, name)
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
            
            profile = db.get_profile(user_id)
            if not profile:
                await ctx.send("❌ Alter not found.")
                return

            if field == 'color':
                # Validate hex color
                color_value = response.content.strip()
                # Allow colors with or without # prefix
                if not color_value.startswith('#'):
                    color_value = '#' + color_value
                
                # Validate hex color format
                if not color_value.startswith('#') or len(color_value) != 7:
                    await ctx.send("❌ Invalid color format. Please use hex format like #FF5733 or FF5733")
                    return
                
                # Validate it's actually a valid hex color
                try:
                    int(color_value[1:], 16)  # Test if it's valid hex
                except ValueError:
                    await ctx.send("❌ Invalid hex color. Please use valid hex characters (0-9, A-F)")
                    return
                    
                profile["alters"][alter_name][field] = color_value
            else:
                profile["alters"][alter_name][field] = response.content.strip()
            
            db.save_profile(user_id, profile)
            await ctx.send(f"✅ {field.title()} updated successfully!")
            
        except asyncio.TimeoutError:
            await ctx.send("⏰ Edit timed out.")

    @commands.command(name="delete")
    async def delete_alter(self, ctx, *, name: str):
        """Delete an alter permanently."""
        
        user_id = str(ctx.author.id)
        
        profile = db.get_profile(user_id)
        if not profile:
            await ctx.send("❌ You don't have any alters.")
            return

        actual_name = find_alter_by_name(profile, name)
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
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            
            if str(reaction.emoji) == '✅':
                # Delete the alter
                del profile["alters"][actual_name]
                db.save_profile(user_id, profile)
                await ctx.send(f"✅ Alter **{actual_name}** has been deleted.")
            else:
                await ctx.send("❌ Deletion cancelled.")
                
        except asyncio.TimeoutError:
            await ctx.send("⏰ Deletion timed out.")

    @commands.command(name="alias")
    async def add_alias(self, ctx, name: str, *, alias: str):
        """Add an alias for an alter."""
        
        user_id = str(ctx.author.id)
        
        profile = db.get_profile(user_id)
        if not profile:
            await ctx.send("❌ You don't have any alters.")
            return

        actual_name = find_alter_by_name(profile, name)
        if not actual_name:
            await ctx.send(f"❌ Alter '{name}' does not exist.")
            return

        # Check if alias already exists
        if alias in profile["alters"][actual_name].get("aliases", []):
            await ctx.send(f"❌ Alias '{alias}' already exists for {actual_name}.")
            return

        # Add the alias
        if "aliases" not in profile["alters"][actual_name]:
            profile["alters"][actual_name]["aliases"] = []
        profile["alters"][actual_name]["aliases"].append(alias)
        db.save_profile(user_id, profile)
        
        await ctx.send(f"✅ Added alias '{alias}' for {actual_name}.")

    @commands.command(name="remove_alias")
    async def remove_alias(self, ctx, name: str, *, alias: str):
        """Remove an alias from an alter."""
        
        user_id = str(ctx.author.id)
        
        profile = db.get_profile(user_id)
        if not profile:
            await ctx.send("❌ You don't have any alters.")
            return

        actual_name = find_alter_by_name(profile, name)
        if not actual_name:
            await ctx.send(f"❌ Alter '{name}' does not exist.")
            return

        # Check if alias exists
        if alias not in profile["alters"][actual_name].get("aliases", []):
            await ctx.send(f"❌ Alias '{alias}' does not exist for {actual_name}.")
            return

        # Remove the alias
        profile["alters"][actual_name]["aliases"].remove(alias)
        db.save_profile(user_id, profile)
        
        await ctx.send(f"✅ Removed alias '{alias}' from {actual_name}.")

    @commands.command(name="proxyavatar")
    async def set_proxy_avatar(self, ctx, name: str, *, avatar_url: str = None):
        """Set a different avatar for proxying (or clear it)."""
        
        user_id = str(ctx.author.id)
        
        profile = db.get_profile(user_id)
        if not profile:
            await ctx.send("❌ You don't have any alters.")
            return

        actual_name = find_alter_by_name(profile, name)
        if not actual_name:
            await ctx.send(f"❌ Alter '{name}' does not exist.")
            return

        if avatar_url and avatar_url.strip():
            # Setting a proxy avatar
            profile["alters"][actual_name]["proxy_avatar"] = avatar_url.strip()
            await ctx.send(f"✅ Set proxy avatar for {actual_name}.")
        else:
            # Clearing proxy avatar (no URL provided or empty string)
            profile["alters"][actual_name]["proxy_avatar"] = None
            await ctx.send(f"✅ Cleared proxy avatar for {actual_name}.")
            
        db.save_profile(user_id, profile)

async def setup(bot):
    """Set up the alters cog."""
    await bot.add_cog(AlterCommands(bot))
