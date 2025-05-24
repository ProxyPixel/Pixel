import discord
from discord.ext import commands
from utils.profiles import load_profiles, save_profiles
import json
import io
import asyncio
from datetime import datetime
import uuid

global_profiles = load_profiles()

class SystemCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="create_system")
    async def create_system(self, ctx, *, system_name: str):
        """Create a new system."""
        user_id = str(ctx.author.id)

        if user_id not in global_profiles:
            global_profiles[user_id] = {"system": {}, "alters": {}, "folders": {}}

        if "system" in global_profiles[user_id] and global_profiles[user_id]["system"]:
            await ctx.send("❌ You already have a system. Use `!edit_system` to modify it.")
            return

        # Generate unique system ID
        system_id = str(uuid.uuid4())[:8]
        created_date = datetime.utcnow()

        global_profiles[user_id]["system"] = {
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
        save_profiles(global_profiles)
        
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

        if user_id not in global_profiles or not global_profiles[user_id].get("system"):
            await ctx.send("❌ You don't have a system. Use `!create_system <name>` to create one.")
            return

        system_data = global_profiles[user_id]["system"]
        
        # Create embed with system info
        embed = discord.Embed(
            title=f"🏷️ {system_data['name']}",
            color=int(system_data.get('color', '0x8A2BE2'), 16) if system_data.get('color') else 0x8A2BE2
        )

        # System Tag (name) is already in title
        
        # Color field (only if color is set)
        if system_data.get('color'):
            embed.add_field(name="🎨 Color", value=system_data['color'], inline=True)

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

        if user_id not in global_profiles or not global_profiles[user_id].get("system"):
            await ctx.send("❌ You don't have a system. Use `!create_system <name>` to create one.")
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
            
            if field == 'color':
                # Validate hex color
                color_value = response.content.strip()
                if not color_value.startswith('#') or len(color_value) != 7:
                    await ctx.send("❌ Invalid color format. Please use hex format like #FF5733")
                    return
                global_profiles[user_id]["system"][field] = color_value
            else:
                global_profiles[user_id]["system"][field] = response.content.strip()
            
            save_profiles(global_profiles)
            await ctx.send(f"✅ System {field} updated successfully!")
            
        except asyncio.TimeoutError:
            await ctx.send("⏰ Edit timed out.")

    @commands.command(name="delete_system")
    async def delete_system(self, ctx):
        """Delete the current system permanently."""
        user_id = str(ctx.author.id)

        if user_id not in global_profiles or not global_profiles[user_id].get("system"):
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
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == '✅':
            del global_profiles[user_id]["system"]
            save_profiles(global_profiles)
            await ctx.send("🗑️ System deleted successfully!")
        else:
                await ctx.send("❌ System deletion cancelled.")
                
        except asyncio.TimeoutError:
            await ctx.send("⏰ Confirmation timed out. System deletion cancelled.")

    @commands.command(name="export_system")
    async def export_system(self, ctx):
        """Export your entire system to a JSON file (sent to DMs)."""
        user_id = str(ctx.author.id)

        if user_id not in global_profiles:
            await ctx.send("❌ You don't have any data to export.")
            return

        try:
            # Create JSON export
            export_data = {
                "exported_at": datetime.utcnow().isoformat(),
                "user_id": user_id,
                "system": global_profiles[user_id].get("system", {}),
                "alters": global_profiles[user_id].get("alters", {}),
                "folders": global_profiles[user_id].get("folders", {})
            }
            
            json_data = json.dumps(export_data, indent=2)
            file_obj = io.StringIO(json_data)
            
            # Send to DMs
            discord_file = discord.File(io.BytesIO(json_data.encode()), filename=f"pixel_system_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            
            try:
                await ctx.author.send("📤 Here's your system export:", file=discord_file)
                await ctx.send("✅ System exported successfully! Check your DMs.")
            except discord.Forbidden:
                await ctx.send("❌ I couldn't send you a DM. Please enable DMs from server members and try again.")
                
        except Exception as e:
            await ctx.send(f"❌ Error exporting system: {str(e)}")

    @commands.command(name="import_system")
    async def import_system(self, ctx):
        """Import a previously exported system from a JSON file."""
        if not ctx.message.attachments:
            await ctx.send("❌ Please attach a JSON file to import.")
            return

        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith('.json'):
            await ctx.send("❌ Please attach a valid JSON file.")
            return

        try:
            data = await attachment.read()
            import_data = json.loads(data.decode())
            
            user_id = str(ctx.author.id)
            
            # Validate import data structure
            if not all(key in import_data for key in ['system', 'alters', 'folders']):
                await ctx.send("❌ Invalid export file format.")
                return

            # Confirmation
            embed = discord.Embed(
                title="⚠️ Import System",
                description="This will overwrite your current system data. Are you sure?\n\nReact with ✅ to confirm or ❌ to cancel.",
                color=0xFF9900
            )
            message = await ctx.send(embed=embed)
            
            await message.add_reaction('✅')
            await message.add_reaction('❌')

            def check(reaction, user):
                return user == ctx.author and reaction.message.id == message.id and str(reaction.emoji) in ['✅', '❌']

            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
            
            if str(reaction.emoji) == '✅':
                global_profiles[user_id] = {
                    "system": import_data['system'],
                    "alters": import_data['alters'],
                    "folders": import_data['folders']
                }
                save_profiles(global_profiles)
                await ctx.send("✅ System imported successfully!")
            else:
                await ctx.send("❌ Import cancelled.")
                
        except json.JSONDecodeError:
            await ctx.send("❌ Invalid JSON file.")
        except asyncio.TimeoutError:
            await ctx.send("⏰ Import confirmation timed out.")
        except Exception as e:
            await ctx.send(f"❌ Error importing system: {str(e)}")

    @commands.command(name="acc_add", aliases=["system_acc_add"])
    async def add_linked_account(self, ctx, username: str):
        """Add a linked account to your system."""
        user_id = str(ctx.author.id)

        if user_id not in global_profiles or not global_profiles[user_id].get("system"):
            await ctx.send("❌ You don't have a system. Use `!create_system <name>` to create one.")
            return

        linked_accounts = global_profiles[user_id]["system"].setdefault("linked_accounts", [])
        
        if username in linked_accounts:
            await ctx.send(f"❌ `{username}` is already linked to your system.")
            return

        linked_accounts.append(username)
        save_profiles(global_profiles)
        await ctx.send(f"✅ Added `{username}` as a linked account to your system.")

    @commands.command(name="import_pluralkit")
    async def import_pluralkit(self, ctx):
        """Import your PluralKit profiles, including proxy avatars and colors."""
        if not ctx.message.attachments:
            await ctx.send("❌ Please attach a PluralKit export JSON file to import.\n\n📝 **How to get your PluralKit export:**\n1. Use `pk;export` in DMs with PluralKit\n2. Download the JSON file\n3. Upload it with this command")
            return

        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith('.json'):
            await ctx.send("❌ Please attach a valid JSON file.")
            return

        try:
            data = await attachment.read()
            pk_data = json.loads(data.decode())
            
            user_id = str(ctx.author.id)
            
            # Validate PluralKit export structure
            if 'members' not in pk_data:
                await ctx.send("❌ This doesn't appear to be a valid PluralKit export file.")
                return

            # Initialize user data if not exists
            if user_id not in global_profiles:
                global_profiles[user_id] = {"system": {}, "alters": {}, "folders": {}}

            # Import system info if available
            if 'system' in pk_data and pk_data['system']:
                pk_system = pk_data['system']
                
                # Create system if doesn't exist
                if not global_profiles[user_id].get("system"):
                    system_name = pk_system.get('name', 'Imported System')
                    global_profiles[user_id]["system"] = {
                        "name": system_name,
                        "system_id": str(uuid.uuid4()),
                        "created_date": datetime.utcnow().isoformat(),
                        "description": pk_system.get('description', ''),
                        "avatar": pk_system.get('avatar_url', ''),
                        "banner": pk_system.get('banner', ''),
                        "pronouns": pk_system.get('pronouns', ''),
                        "color": pk_system.get('color'),
                        "linked_accounts": []
                    }

            # Import members (alters)
            imported_count = 0
            skipped_count = 0
            
            for member in pk_data['members']:
                member_name = member.get('name', 'Unknown')
                
                # Skip if alter already exists
                if member_name in global_profiles[user_id]["alters"]:
                    skipped_count += 1
                    continue
                
                # Convert PluralKit proxy tags to our format
                proxy_tags = member.get('proxy_tags', [])
                proxy_format = ""
                if proxy_tags:
                    # Use the first proxy tag
                    first_tag = proxy_tags[0]
                    prefix = first_tag.get('prefix', '')
                    suffix = first_tag.get('suffix', '')
                    if prefix and suffix:
                        proxy_format = f"{prefix}TEXT{suffix}"
                    elif prefix:
                        proxy_format = f"{prefix}TEXT"
                    elif suffix:
                        proxy_format = f"TEXT{suffix}"

                # Create the alter
                global_profiles[user_id]["alters"][member_name] = {
                    "name": member_name,
                    "displayname": member.get('display_name', member_name),
                    "pronouns": member.get('pronouns', ''),
                    "description": member.get('description', ''),
                    "avatar": member.get('avatar_url', ''),
                    "banner": member.get('banner', ''),
                    "proxy": proxy_format,
                    "color": member.get('color'),
                    "proxy_avatar": member.get('proxy_avatar_url', ''),
                    "aliases": [],
                    "created_date": member.get('created', datetime.utcnow().isoformat())
                }
                imported_count += 1

            save_profiles(global_profiles)

            # Send success message
            embed = discord.Embed(
                title="🔄 PluralKit Import Complete",
                description="Your PluralKit data has been imported successfully!",
                color=0x00FF00
            )
            embed.add_field(name="✅ Imported Alters", value=str(imported_count), inline=True)
            if skipped_count > 0:
                embed.add_field(name="⏭️ Skipped (Already Exist)", value=str(skipped_count), inline=True)
            
            embed.add_field(
                name="📝 What was imported:",
                value="• Alter names and display names\n• Descriptions and pronouns\n• Avatar and banner URLs\n• Proxy tags (converted to our format)\n• Colors and proxy avatars\n• System info (if you didn't have one)",
                inline=False
            )
            embed.add_field(
                name="🔧 Next Steps:",
                value="Use `!list_profiles` to see your imported alters or `!edit <name>` to customize them further.",
                inline=False
            )

            await ctx.send(embed=embed)
                
        except json.JSONDecodeError:
            await ctx.send("❌ Invalid JSON file. Please make sure this is a valid PluralKit export.")
        except Exception as e:
            await ctx.send(f"❌ Error importing PluralKit data: {str(e)}")

async def setup(bot):
    await bot.add_cog(SystemCommands(bot))
