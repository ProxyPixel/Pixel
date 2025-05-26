import discord
from discord.ext import commands
from utils.mongodb import db
from utils.helpers import find_alter_by_name, create_embed
import asyncio

class FolderCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="create_folder")
    async def create_folder(self, ctx, *, folder_name: str):
        """Create a new folder with a name, color, banner, icon, and alters."""
        
        user_id = str(ctx.author.id)

        # Get or create profile
        profile = db.get_profile(user_id)
        if not profile:
            profile = {"user_id": user_id, "system": {}, "alters": {}, "folders": {}}

        if folder_name in profile["folders"]:
            await ctx.send(f"❌ A folder with the name **{folder_name}** already exists.")
            return

        profile["folders"][folder_name] = {
            "name": folder_name,
            "color": None,
            "banner": None,
            "icon": None,
            "description": None,
            "alters": []
        }
        db.save_profile(user_id, profile)
        
        embed = discord.Embed(
            title="✅ Folder Created Successfully",
            description=f"Folder **{folder_name}** has been created!",
            color=0x8A2BE2
        )
        embed.add_field(name="📝 Next Steps", value="Use `!edit_folder` to customize it or `!add_alters` to add alters to this folder.", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="edit_folder")
    async def edit_folder(self, ctx, *, folder_name: str):
        """Edit an existing folder."""
        
        user_id = str(ctx.author.id)

        profile = db.get_profile(user_id)
        if not profile or folder_name not in profile.get("folders", {}):
            await ctx.send(f"❌ Folder '{folder_name}' does not exist.")
            return

        embed = discord.Embed(
            title=f"⚙️ Edit Folder: {folder_name}",
            description="React with the corresponding emoji to edit that field:",
            color=0x8A2BE2
        )
        embed.add_field(name="🏷️ Name", value="Edit folder name", inline=True)
        embed.add_field(name="📝 Description", value="Edit description", inline=True)
        embed.add_field(name="🌈 Color", value="Edit color (hex)", inline=True)
        embed.add_field(name="🎨 Banner", value="Edit banner URL", inline=True)
        embed.add_field(name="🖼️ Icon", value="Edit icon URL", inline=True)

        message = await ctx.send(embed=embed)
        
        # Add reaction emojis
        reactions = ['🏷️', '📝', '🌈', '🎨', '🖼️']
        for reaction in reactions:
            await message.add_reaction(reaction)

        def check(reaction, user):
            return user == ctx.author and reaction.message.id == message.id and str(reaction.emoji) in reactions

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            
            if str(reaction.emoji) == '🏷️':
                await self._edit_folder_field(ctx, folder_name, 'name', 'Enter the new folder name:')
            elif str(reaction.emoji) == '📝':
                await self._edit_folder_field(ctx, folder_name, 'description', 'Enter the new description:')
            elif str(reaction.emoji) == '🌈':
                await self._edit_folder_field(ctx, folder_name, 'color', 'Enter the new color (hex format, e.g., #FF5733):')
            elif str(reaction.emoji) == '🎨':
                await self._edit_folder_field(ctx, folder_name, 'banner', 'Enter the new banner URL:')
            elif str(reaction.emoji) == '🖼️':
                await self._edit_folder_field(ctx, folder_name, 'icon', 'Enter the new icon URL:')

        except asyncio.TimeoutError:
            await ctx.send("⏰ Edit menu timed out.")

    async def _edit_folder_field(self, ctx, folder_name, field, prompt):
        """Helper function to edit a specific folder field."""
        await ctx.send(prompt)
        
        def check(msg):
            return msg.author == ctx.author and msg.channel == ctx.channel

        try:
            response = await self.bot.wait_for('message', timeout=60.0, check=check)
            user_id = str(ctx.author.id)
            
            profile = db.get_profile(user_id)
            if not profile:
                await ctx.send("❌ Folder not found.")
                return

            if field == 'color':
                # Validate hex color
                color_value = response.content.strip()
                if not color_value.startswith('#') or len(color_value) != 7:
                    await ctx.send("❌ Invalid color format. Please use hex format like #FF5733")
                    return
                profile["folders"][folder_name][field] = color_value
            elif field == 'name':
                # Handle folder rename
                new_name = response.content.strip()
                if new_name != folder_name:
                    # Check if new name already exists
                    if new_name in profile["folders"]:
                        await ctx.send(f"❌ A folder with the name '{new_name}' already exists.")
                        return
                    # Rename the folder
                    folder_data = profile["folders"].pop(folder_name)
                    folder_data['name'] = new_name
                    profile["folders"][new_name] = folder_data
                    folder_name = new_name  # Update for success message
                else:
                    profile["folders"][folder_name][field] = new_name
            else:
                profile["folders"][folder_name][field] = response.content.strip()
            
            db.save_profile(user_id, profile)
            await ctx.send(f"✅ Folder {field} updated successfully!")
            
        except asyncio.TimeoutError:
            await ctx.send("⏰ Edit timed out.")

    @commands.command(name="delete_folder")
    async def delete_folder(self, ctx, *, folder_name: str):
        """Delete a folder."""
        
        user_id = str(ctx.author.id)

        profile = db.get_profile(user_id)
        if not profile or folder_name not in profile.get("folders", {}):
            await ctx.send(f"❌ Folder '{folder_name}' does not exist.")
            return

        # Confirmation
        embed = discord.Embed(
            title="⚠️ Delete Folder",
            description=f"Are you sure you want to delete the folder **{folder_name}**? This action cannot be undone.\n\nReact with ✅ to confirm or ❌ to cancel.",
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
                del profile["folders"][folder_name]
                db.save_profile(user_id, profile)
                await ctx.send(f"✅ Folder '{folder_name}' has been deleted.")
            else:
                await ctx.send("❌ Deletion cancelled.")
                
        except asyncio.TimeoutError:
            await ctx.send("⏰ Deletion timed out.")

    @commands.command(name="show_folder")
    async def show_folder(self, ctx, *, folder_name: str):
        """Show the contents of a folder."""
        
        user_id = str(ctx.author.id)

        profile = db.get_profile(user_id)
        if not profile or folder_name not in profile.get("folders", {}):
            await ctx.send(f"❌ Folder '{folder_name}' does not exist.")
            return

        folder_data = profile["folders"][folder_name]
        
        # Use folder's color or default
        color = int(folder_data.get('color', '0x8A2BE2'), 16) if folder_data.get('color') else 0x8A2BE2
        
        embed = discord.Embed(
            title=f"📁 {folder_data['name']}",
            color=color
        )

        # Description
        if folder_data.get('description'):
            embed.add_field(name="📝 Description", value=folder_data['description'], inline=False)

        # Color
        if folder_data.get('color'):
            embed.add_field(name="🎨 Color", value=folder_data['color'], inline=True)

        # Alters in folder
        alters_in_folder = folder_data.get('alters', [])
        if alters_in_folder:
            # Get alter display names
            alter_list = []
            for alter_name in alters_in_folder:
                if alter_name in profile["alters"]:
                    display_name = profile["alters"][alter_name].get('displayname', alter_name)
                    alter_list.append(display_name)
            
            if alter_list:
                embed.add_field(name=f"👥 Alters ({len(alter_list)})", value="\n".join(alter_list), inline=False)

        # Icon
        if folder_data.get('icon'):
            embed.set_thumbnail(url=folder_data['icon'])

        # Banner
        if folder_data.get('banner'):
            embed.set_image(url=folder_data['banner'])

        await ctx.send(embed=embed)

    @commands.command(name="add_alters")
    async def add_alters(self, ctx, folder_name: str, *, alter_names: str):
        """Add alters to a folder."""
        
        user_id = str(ctx.author.id)

        profile = db.get_profile(user_id)
        if not profile or folder_name not in profile.get("folders", {}):
            await ctx.send(f"❌ Folder '{folder_name}' does not exist.")
            return

        # Split alter names by commas and clean up whitespace
        alter_list = [name.strip() for name in alter_names.split(",")]
        
        # Process each alter
        added = []
        skipped = []
        not_found = []
        
        for alter_name in alter_list:
            actual_name = find_alter_by_name(profile, alter_name)
            if not actual_name:
                not_found.append(alter_name)
                continue
                
            if actual_name in profile["folders"][folder_name]["alters"]:
                skipped.append(actual_name)
                continue
                
            profile["folders"][folder_name]["alters"].append(actual_name)
            added.append(actual_name)

        # Save changes if any alters were added
        if added:
            db.save_profile(user_id, profile)

        # Create response embed
        embed = discord.Embed(
            title=f"📁 Folder Update: {folder_name}",
            color=0x8A2BE2
        )
        
        if added:
            embed.add_field(name="✅ Added", value="\n".join(added), inline=False)
        if skipped:
            embed.add_field(name="⏭️ Already in folder", value="\n".join(skipped), inline=False)
        if not_found:
            embed.add_field(name="❌ Not found", value="\n".join(not_found), inline=False)
            
        await ctx.send(embed=embed)

    @commands.command(name="remove_alters")
    async def remove_alters(self, ctx, folder_name: str, *, alter_names: str):
        """Remove alters from a folder."""
        
        user_id = str(ctx.author.id)

        profile = db.get_profile(user_id)
        if not profile or folder_name not in profile.get("folders", {}):
            await ctx.send(f"❌ Folder '{folder_name}' does not exist.")
            return

        # Split alter names by commas and clean up whitespace
        alter_list = [name.strip() for name in alter_names.split(",")]
        
        # Process each alter
        removed = []
        not_in_folder = []
        not_found = []
        
        for alter_name in alter_list:
            actual_name = find_alter_by_name(profile, alter_name)
            if not actual_name:
                not_found.append(alter_name)
                continue
                
            if actual_name not in profile["folders"][folder_name]["alters"]:
                not_in_folder.append(actual_name)
                continue
                
            profile["folders"][folder_name]["alters"].remove(actual_name)
            removed.append(actual_name)

        # Save changes if any alters were removed
        if removed:
            db.save_profile(user_id, profile)

        # Create response embed
        embed = discord.Embed(
            title=f"📁 Folder Update: {folder_name}",
            color=0x8A2BE2
        )
        
        if removed:
            embed.add_field(name="✅ Removed", value="\n".join(removed), inline=False)
        if not_in_folder:
            embed.add_field(name="⏭️ Not in folder", value="\n".join(not_in_folder), inline=False)
        if not_found:
            embed.add_field(name="❌ Not found", value="\n".join(not_found), inline=False)
            
        await ctx.send(embed=embed)

    @commands.command(name="wipe_folder_alters")
    async def wipe_folder_alters(self, ctx, *, folder_name: str):
        """Remove all alters from a folder."""
        
        user_id = str(ctx.author.id)

        profile = db.get_profile(user_id)
        if not profile or folder_name not in profile.get("folders", {}):
            await ctx.send(f"❌ Folder '{folder_name}' does not exist.")
            return

        # Get current alter count
        alter_count = len(profile["folders"][folder_name].get("alters", []))
        if alter_count == 0:
            await ctx.send(f"❌ Folder '{folder_name}' is already empty.")
            return

        # Confirmation
        embed = discord.Embed(
            title="⚠️ Wipe Folder",
            description=f"Are you sure you want to remove all {alter_count} alter(s) from folder **{folder_name}**?\n\nReact with ✅ to confirm or ❌ to cancel.",
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
                profile["folders"][folder_name]["alters"] = []
                db.save_profile(user_id, profile)
                await ctx.send(f"✅ Removed all alters from folder '{folder_name}'.")
            else:
                await ctx.send("❌ Operation cancelled.")
                
        except asyncio.TimeoutError:
            await ctx.send("⏰ Operation timed out.")

    @commands.command(name="list_folders")
    async def list_folders(self, ctx):
        """List all folders and their contents."""
        
        user_id = str(ctx.author.id)

        profile = db.get_profile(user_id)
        if not profile or not profile.get("folders"):
            await ctx.send("❌ You don't have any folders. Use `!create_folder <name>` to create one.")
            return

        folders = profile["folders"]
        
        embed = discord.Embed(
            title="📂 Your Folders",
            description=f"Total: {len(folders)} folder(s)",
            color=0x8A2BE2
        )

        for folder_name, folder_data in folders.items():
            # Safety check for folder_data
            if not folder_data or not isinstance(folder_data, dict):
                continue
                
            # Get number of alters in folder
            alter_count = len(folder_data.get('alters', []))
            
            # Get description preview
            description = folder_data.get('description', 'No description')
            if description and len(description) > 100:
                description = description[:97] + "..."
            elif not description:
                description = 'No description'
                
            value = f"📝 {description}\n👥 {alter_count} alter(s)"
            
            embed.add_field(
                name=f"📁 {folder_name}",
                value=value,
                inline=False
            )

        await ctx.send(embed=embed)

async def setup(bot):
    """Set up the folders cog."""
    await bot.add_cog(FolderCommands(bot))
