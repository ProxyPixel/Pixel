import discord
from discord.ext import commands
from utils.mongodb import db
import json
import io
import asyncio
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

class SystemCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="create_system")
    async def create_system(self, ctx, *, system_name: str):
        """Create a new system."""
        logger.info(f"Instance {self.bot.instance_id} processing create_system for {ctx.author}")
        
        user_id = str(ctx.author.id)

        # Check if user already has a system
        profile = db.get_profile(user_id)
        if profile and profile.get("system"):
            await ctx.send("❌ You already have a system. Use `!edit_system` to modify it.")
            return

        # Generate unique system ID
        system_id = str(uuid.uuid4())[:8]
        created_date = datetime.utcnow()

        # Create new profile if it doesn't exist
        if not profile:
            profile = {"user_id": user_id, "system": {}, "alters": {}, "folders": {}}

        profile["system"] = {
            "name": system_name,
            "description": None,
            "avatar": None,
            "banner": None,
            "pronouns": None,
            "color": None,
            "linked_accounts": [ctx.author.name],
            "system_id": system_id,
            "created_date": created_date.isoformat()
        }
        db.save_profile(user_id, profile)
        
        embed = discord.Embed(
            title="✅ System Created Successfully",
            description=f"System **{system_name}** has been created!\nSystem ID: `{system_id}`",
            color=0x8A2BE2
        )
        await ctx.send(embed=embed)

    @commands.command(name="system")
    async def show_system(self, ctx):
        """Show the current system's info, including avatars, banners, and colors."""
        
        user_id = str(ctx.author.id)

        profile = db.get_profile(user_id)
        if not profile or not profile.get("system"):
            await ctx.send("❌ You don't have a system. Use `!create_system <n>` to create one.")
            return

        system_data = profile["system"]
        
        # Create embed with system info
        embed = discord.Embed(
            title=f"🏷️ {system_data['name']}",
            color=int(system_data.get('color', '0x8A2BE2'), 16) if system_data.get('color') else 0x8A2BE2
        )

        # System Tag (name) is already in title
        
        # Color field (only if color is set)
        if system_data.get('color'):
            embed.add_field(name="🎨 Color", value=system_data['color'], inline=True)

        # System Tag for proxying
        if system_data.get('proxy_tag'):
            embed.add_field(name="🏷️ Proxy Tag", value=f"`{system_data['proxy_tag']}`", inline=True)

        # Linked accounts (not spoilered)
        linked_accounts = system_data.get('linked_accounts', [])
        if linked_accounts:
            accounts_text = ", ".join(linked_accounts)
            embed.add_field(name="🔗 Linked Accounts", value=accounts_text, inline=False)

        # Description
        description = system_data.get('description', 'No description provided.')
        if description:
            embed.add_field(name="📝 Description", value=description, inline=False)

        # Avatar
        if system_data.get('avatar'):
            embed.set_thumbnail(url=system_data['avatar'])

        # Banner
        if system_data.get('banner'):
            embed.set_image(url=system_data['banner'])

        # Pronouns
        if system_data.get('pronouns'):
            embed.add_field(name="👤 Pronouns", value=system_data['pronouns'], inline=True)

        # Footer with System ID and creation date
        created_date = datetime.fromisoformat(system_data['created_date'])
        footer_text = f"System ID: {system_data['system_id']} | Created on {created_date.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        embed.set_footer(text=footer_text)

        await ctx.send(embed=embed)

    @commands.command(name="edit_system")
    async def edit_system(self, ctx):
        """Edit the current system (name, avatar, banner, description, pronouns, color)."""
        
        user_id = str(ctx.author.id)

        profile = db.get_profile(user_id)
        if not profile or not profile.get("system"):
            await ctx.send("❌ You don't have a system. Use `!create_system <n>` to create one.")
            return

        embed = discord.Embed(
            title="⚙️ System Edit Menu",
            description="React with the corresponding emoji to edit that field:",
            color=0x8A2BE2
        )
        embed.add_field(name="🏷️ Name", value="Edit system name", inline=True)
        embed.add_field(name="📝 Description", value="Edit description", inline=True)
        embed.add_field(name="🖼️ Avatar", value="Edit avatar URL", inline=True)
        embed.add_field(name="🎨 Banner", value="Edit banner URL", inline=True)
        embed.add_field(name="👤 Pronouns", value="Edit pronouns", inline=True)
        embed.add_field(name="🌈 Color", value="Edit color (hex)", inline=True)

        message = await ctx.send(embed=embed)
        
        # Add reaction emojis
        reactions = ['🏷️', '📝', '🖼️', '🎨', '👤', '🌈']
        for reaction in reactions:
            await message.add_reaction(reaction)

        def check(reaction, user):
            return user == ctx.author and reaction.message.id == message.id and str(reaction.emoji) in reactions

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            
            if str(reaction.emoji) == '🏷️':
                await self._edit_system_field(ctx, 'name', 'Enter the new system name:')
            elif str(reaction.emoji) == '📝':
                await self._edit_system_field(ctx, 'description', 'Enter the new description:')
            elif str(reaction.emoji) == '🖼️':
                await self._edit_system_field(ctx, 'avatar', 'Enter the new avatar URL:')
            elif str(reaction.emoji) == '🎨':
                await self._edit_system_field(ctx, 'banner', 'Enter the new banner URL:')
            elif str(reaction.emoji) == '👤':
                await self._edit_system_field(ctx, 'pronouns', 'Enter the new pronouns:')
            elif str(reaction.emoji) == '🌈':
                await self._edit_system_field(ctx, 'color', 'Enter the new color (hex format, e.g., #FF5733):')

        except asyncio.TimeoutError:
            await ctx.send("⏰ Edit menu timed out.")

    async def _edit_system_field(self, ctx, field, prompt):
        """Helper function to edit a specific system field."""
        await ctx.send(prompt)
        
        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        try:
            response = await self.bot.wait_for('message', timeout=60.0, check=check)
            user_id = str(ctx.author.id)
            
            profile = db.get_profile(user_id)
            if not profile:
                await ctx.send("❌ System not found.")
                return

            if field == 'color':
                # Validate hex color
                color_value = response.content.strip()
                if not color_value.startswith('#') or len(color_value) != 7:
                    await ctx.send("❌ Invalid color format. Please use hex format like #FF5733")
                    return
                profile["system"][field] = color_value
            else:
                profile["system"][field] = response.content.strip()
            
            db.save_profile(user_id, profile)
            await ctx.send(f"✅ System {field} updated successfully!")
            
        except asyncio.TimeoutError:
            await ctx.send("⏰ Edit timed out.")

    @commands.command(name="delete_system")
    async def delete_system(self, ctx):
        """Delete the current system permanently."""
        
        user_id = str(ctx.author.id)

        profile = db.get_profile(user_id)
        if not profile or not profile.get("system"):
            await ctx.send("❌ You don't have a system to delete.")
            return

        # Confirmation
        embed = discord.Embed(
            title="⚠️ Delete System",
            description="Are you sure you want to delete your system? This action cannot be undone.\n\nReact with ✅ to confirm or ❌ to cancel.",
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
                # Delete the system
                db.delete_profile(user_id)
                await ctx.send("✅ Your system has been deleted.")
            else:
                await ctx.send("❌ System deletion cancelled.")
                
        except asyncio.TimeoutError:
            await ctx.send("⏰ Deletion timed out.")

    @commands.command(name="export_system")
    async def export_system(self, ctx):
        """Export your system data as a JSON file."""
        
        user_id = str(ctx.author.id)

        profile = db.get_profile(user_id)
        if not profile:
            await ctx.send("❌ You don't have a system to export.")
            return

        # Convert MongoDB ObjectId to string for JSON serialization
        def convert_objectid(obj):
            if hasattr(obj, '__dict__'):
                for key, value in obj.__dict__.items():
                    if hasattr(value, '__class__') and 'ObjectId' in str(value.__class__):
                        obj.__dict__[key] = str(value)
            return obj

        # Clean the profile data for JSON export
        clean_profile = {}
        for key, value in profile.items():
            if hasattr(value, '__class__') and 'ObjectId' in str(value.__class__):
                clean_profile[key] = str(value)
            elif key == '_id':
                # Skip MongoDB's _id field
                continue
            else:
                clean_profile[key] = value

        try:
            # Convert the data to JSON
            json_data = json.dumps(clean_profile, indent=4, default=str)
            
            # Create a discord.File object
            discord_file = discord.File(
                fp=io.BytesIO(json_data.encode()),
                filename=f"system_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            
            # Try to send via DM first
            try:
                await ctx.author.send("✅ Here's your system data backup:", file=discord_file)
                await ctx.send("✅ I've DMed you your system backup! Make sure your DMs are open.")
            except discord.Forbidden:
                # If DM fails, send in channel
                await ctx.send("❌ I couldn't DM you the backup file. Here it is in this channel:", file=discord_file)
                
        except Exception as e:
            logger.error(f"Error exporting system: {str(e)}")
            await ctx.send("❌ An error occurred while exporting your system data. Please try again later.")

    @commands.command(name="import_system")
    async def import_system(self, ctx):
        """Import system data from a JSON file."""
        
        if not ctx.message.attachments:
            await ctx.send("❌ Please attach a JSON file containing your system data.")
            return
            
        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith('.json'):
            await ctx.send("❌ Please provide a JSON file.")
            return
            
        try:
            # Download and read the file
            json_data = await attachment.read()
            system_data = json.loads(json_data)
            
            # Basic validation
            required_keys = ["system", "alters", "folders"]
            if not all(key in system_data for key in required_keys):
                await ctx.send("❌ Invalid system data format.")
                return
                
            # Confirmation
            embed = discord.Embed(
                title="⚠️ Import System",
                description="This will overwrite your current system data. Are you sure?\n\nReact with ✅ to confirm or ❌ to cancel.",
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
                    # Import the data
                    user_id = str(ctx.author.id)
                    system_data["user_id"] = user_id  # Ensure user_id is set
                    db.save_profile(user_id, system_data)
                    await ctx.send("✅ System data imported successfully!")
                else:
                    await ctx.send("❌ Import cancelled.")
                    
            except asyncio.TimeoutError:
                await ctx.send("⏰ Import timed out.")
                
        except json.JSONDecodeError:
            await ctx.send("❌ Invalid JSON format.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {str(e)}")

    @commands.command(name="acc_add", aliases=["system_acc_add"])
    async def add_linked_account(self, ctx, username: str):
        """Add a linked account to your system."""
        user_id = str(ctx.author.id)

        profile = db.get_profile(user_id)
        if not profile or not profile.get("system"):
            await ctx.send("❌ You don't have a system. Use `!create_system <n>` to create one.")
            return

        if username in profile["system"]["linked_accounts"]:
            await ctx.send("❌ This account is already linked to your system.")
            return

        profile["system"]["linked_accounts"].append(username)
        db.save_profile(user_id, profile)
        await ctx.send(f"✅ Added {username} to your system's linked accounts.")

    @commands.command(name="import_pluralkit")
    async def import_pluralkit(self, ctx):
        """Import system data from a PluralKit export file."""
        if not ctx.message.attachments:
            await ctx.send("❌ Please attach your PluralKit export file.")
            return
            
        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith('.json'):
            await ctx.send("❌ Please provide a JSON file.")
            return
            
        try:
            # Download and read the file
            json_data = await attachment.read()
            pk_data = json.loads(json_data)
            
            # Basic validation
            if "system" not in pk_data or "members" not in pk_data:
                await ctx.send("❌ Invalid PluralKit export format.")
                return
                
            # Convert PluralKit data to our format
            user_id = str(ctx.author.id)
            system_data = {
                "user_id": user_id,
                "system": {
                    "name": pk_data["system"].get("name", "Imported System"),
                    "description": pk_data["system"].get("description"),
                    "avatar": pk_data["system"].get("avatar_url"),
                    "banner": None,  # PK doesn't have banners
                    "pronouns": pk_data["system"].get("pronouns"),
                    "color": f"#{pk_data['system'].get('color', '8A2BE2')}",
                    "linked_accounts": [ctx.author.name],
                    "system_id": str(uuid.uuid4())[:8],
                    "created_date": datetime.utcnow().isoformat()
                },
                "alters": {},
                "folders": {}
            }
            
            # Convert members to alters
            for member in pk_data["members"]:
                alter_id = str(uuid.uuid4())[:8]
                system_data["alters"][member["name"]] = {
                    "id": alter_id,
                    "displayname": member.get("display_name", member["name"]),
                    "avatar": member.get("avatar_url"),
                    "description": member.get("description"),
                    "pronouns": member.get("pronouns"),
                    "color": f"#{member.get('color', '8A2BE2')}",
                    "proxy": f"{member.get('prefix', '')}TEXT{member.get('suffix', '')}" if member.get('prefix') or member.get('suffix') else None
                }
            
            # Confirmation
            embed = discord.Embed(
                title="⚠️ Import PluralKit Data",
                description="This will overwrite your current system data. Are you sure?\n\nReact with ✅ to confirm or ❌ to cancel.",
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
                    # Import the data
                    db.save_profile(user_id, system_data)
                    await ctx.send("✅ PluralKit data imported successfully!")
                else:
                    await ctx.send("❌ Import cancelled.")
                    
            except asyncio.TimeoutError:
                await ctx.send("⏰ Import timed out.")
                
        except json.JSONDecodeError:
            await ctx.send("❌ Invalid JSON format.")
        except Exception as e:
            await ctx.send(f"❌ An error occurred: {str(e)}")

    @commands.command(name="tag")
    async def set_system_tag(self, ctx, *, tag: str = None):
        """Set a system tag that appears next to the alter name when proxying."""
        
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        
        if not profile or not profile.get("system"):
            await ctx.send("❌ You don't have a system. Use `!create_system <name>` to create one.")
            return
        
        if tag is None:
            # Show current tag
            current_tag = profile["system"].get("tag", "")
            if current_tag:
                await ctx.send(f"🏷️ Current system tag: `{current_tag}`")
            else:
                await ctx.send("🏷️ No system tag set. Use `!tag <tag>` to set one.")
            return
        
        # Validate tag length
        if len(tag) > 20:
            await ctx.send("❌ System tag must be 20 characters or less.")
            return
        
        # Update system tag
        profile["system"]["tag"] = tag
        db.save_profile(user_id, profile)
        
        embed = discord.Embed(
            title="🏷️ System Tag Updated",
            description=f"System tag set to: `{tag}`\n\nThis tag will appear next to alter names when proxying.",
            color=0x8A2BE2
        )
        await ctx.send(embed=embed)

async def setup(bot):
    """Set up the system cog."""
    await bot.add_cog(SystemCommands(bot))
