import discord
from discord.ext import commands
import asyncio
from datetime import datetime

from utils.mongodb import db
from utils.helpers import find_alter_by_name, create_embed

class FolderCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="create_folder")
    async def create_folder(self, ctx, *, folder_name: str):
        """Create a new folder."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        # Initialize profile if empty
        if not profile:
            profile = {"user_id": user_id, "system": {}, "alters": {}, "folders": {}}

        if folder_name in profile.get("folders", {}):
            return await ctx.send(f"❌ A folder named **{folder_name}** already exists.")

        profile.setdefault("folders", {})[folder_name] = {
            "name": folder_name,
            "description": None,
            "color": None,
            "banner": None,
            "icon": None,
            "alters": []
        }
        db.save_profile(user_id, profile)

        embed = create_embed(
            title="✅ Folder Created",
            description=f"Folder **{folder_name}** has been created.",
        )
        embed.add_field(
            name="Next Steps",
            value="Use `!edit_folder`, `!add_alters`, or other folder commands to customize.",
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.command(name="edit_folder")
    async def edit_folder(self, ctx, *, folder_name: str):
        """Edit folder properties."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        folders = profile.get("folders", {})
        if folder_name not in folders:
            return await ctx.send(f"❌ Folder **{folder_name}** not found.")

        embed = create_embed(
            title=f"⚙️ Edit Folder: {folder_name}",
            description="React with emoji to choose a field to edit:",
        )
        options = {'🏷️': 'name', '📝': 'description', '🌈': 'color', '🎨': 'banner', '🖼️': 'icon'}
        for emoji, field in options.items():
            embed.add_field(name=emoji, value=field.capitalize(), inline=True)

        msg = await ctx.send(embed=embed)
        for emoji in options:
            await msg.add_reaction(emoji)

        def check(r, u): return u == ctx.author and r.message.id == msg.id and str(r.emoji) in options
        try:
            reaction, _ = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            field = options[str(reaction.emoji)]
            await self._edit_folder_field(ctx, user_id, folder_name, field)
        except asyncio.TimeoutError:
            await ctx.send("⏰ Edit menu timed out.")

    async def _edit_folder_field(self, ctx, user_id: str, folder_name: str, field: str):
        prompts = {
            'name': 'Enter new folder name:',
            'description': 'Enter new description:',
            'color': 'Enter new color (hex, e.g., #FF5733):',
            'banner': 'Enter new banner URL:',
            'icon': 'Enter new icon URL:'
        }
        await ctx.send(prompts[field])
        def mcheck(m): return m.author.id == int(user_id) and m.channel == ctx.channel
        try:
            msg = await self.bot.wait_for('message', timeout=60.0, check=mcheck)
            profile = db.get_profile(user_id)
            folders = profile.setdefault('folders', {})
            fdata = folders.get(folder_name)
            if not fdata:
                return await ctx.send("❌ Folder not found.")
            if field == 'name':
                new_name = msg.content.strip()
                if new_name != folder_name and new_name in folders:
                    return await ctx.send(f"❌ Folder **{new_name}** already exists.")
                # rename
                folders[new_name] = folders.pop(folder_name)
                folders[new_name]['name'] = new_name
            elif field == 'color':
                val = msg.content.strip()
                if not val.startswith('#') or len(val) != 7:
                    return await ctx.send("❌ Invalid hex color.")
                fdata['color'] = val
            else:
                fdata[field] = msg.content.strip()
            db.save_profile(user_id, profile)
            await ctx.send(f"✅ Folder {field} updated.")
        except asyncio.TimeoutError:
            await ctx.send("⏰ Update timed out.")

    @commands.command(name="delete_folder")
    async def delete_folder(self, ctx, *, folder_name: str):
        """Delete a folder."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        folders = profile.get('folders', {})
        if folder_name not in folders:
            return await ctx.send(f"❌ Folder **{folder_name}** not found.")

        embed = create_embed(
            title="⚠️ Delete Folder",
            description=f"React ✅ to confirm deletion of **{folder_name}**, or ❌ to cancel",
        )
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('✅')
        await msg.add_reaction('❌')
        def check(r,u): return u==ctx.author and r.message.id==msg.id and str(r.emoji) in ['✅','❌']
        try:
            r,_ = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            if str(r.emoji)=='✅':
                del folders[folder_name]
                db.save_profile(user_id, profile)
                await ctx.send(f"✅ Folder **{folder_name}** deleted.")
            else:
                await ctx.send("❌ Deletion cancelled.")
        except asyncio.TimeoutError:
            await ctx.send("⏰ Deletion timed out.")

    @commands.command(name="show_folder")
    async def show_folder(self, ctx, *, folder_name: str):
        """Display folder details."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        folder = profile.get('folders', {}).get(folder_name)
        if not folder:
            return await ctx.send(f"❌ Folder **{folder_name}** not found.")

        color = int(folder['color'].lstrip('#'),16) if folder.get('color') else 0x8A2BE2
        embed = create_embed(title=f"📁 {folder_name}", color=color)
        if folder.get('description'):
            embed.add_field(name="📝 Description", value=folder['description'], inline=False)
        if folder.get('color'):
            embed.add_field(name="🎨 Color", value=folder['color'], inline=True)
        if folder.get('icon'):
            embed.set_thumbnail(url=folder['icon'])
        if folder.get('banner'):
            embed.set_image(url=folder['banner'])
        alters = folder.get('alters', [])
        if alters:
            displays = [profile['alters'][n].get('displayname',n) for n in alters if n in profile.get('alters',{})]
            embed.add_field(name=f"👥 Alters ({len(displays)})", value="\n".join(displays), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="add_alters")
    async def add_alters(self, ctx, folder_name: str, *, names: str):
        """Add alters to a folder."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        folder = profile.get('folders', {}).get(folder_name)
        if not folder:
            return await ctx.send(f"❌ Folder **{folder_name}** not found.")
        to_add = [n.strip() for n in names.split(',')]
        added, skipped, notfound = [], [], []
        for n in to_add:
            actual = find_alter_by_name(profile, n)
            if not actual:
                notfound.append(n)
            elif actual in folder['alters']:
                skipped.append(actual)
            else:
                folder['alters'].append(actual)
                added.append(actual)
        if added:
            db.save_profile(user_id, profile)
        embed = create_embed(title=f"📁 {folder_name} Update")
        if added: embed.add_field(name="✅ Added", value="\n".join(added), inline=False)
        if skipped: embed.add_field(name="⏭️ Skipped", value="\n".join(skipped), inline=False)
        if notfound: embed.add_field(name="❌ Not Found", value="\n".join(notfound), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="remove_alters")
    async def remove_alters(self, ctx, folder_name: str, *, names: str):
        """Remove alters from a folder."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        folder = profile.get('folders', {}).get(folder_name)
        if not folder:
            return await ctx.send(f"❌ Folder **{folder_name}** not found.")
        to_remove = [n.strip() for n in names.split(',')]
        removed, notin, notfound = [], [], []
        for n in to_remove:
            actual = find_alter_by_name(profile, n)
            if not actual:
                notfound.append(n)
            elif actual not in folder['alters']:
                notin.append(actual)
            else:
                folder['alters'].remove(actual)
                removed.append(actual)
        if removed:
            db.save_profile(user_id, profile)
        embed = create_embed(title=f"📁 {folder_name} Update")
        if removed: embed.add_field(name="✅ Removed", value="\n".join(removed), inline=False)
        if notin: embed.add_field(name="⏭️ Not In Folder", value="\n".join(notin), inline=False)
        if notfound: embed.add_field(name="❌ Not Found", value="\n".join(notfound), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="wipe_folder_alters")
    async def wipe_folder_alters(self, ctx, *, folder_name: str):
        """Remove all alters from a folder."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        folder = profile.get('folders', {}).get(folder_name)
        if not folder:
            return await ctx.send(f"❌ Folder **{folder_name}** not found.")
        count = len(folder.get('alters', []))
        if count == 0:
            return await ctx.send(f"❌ Folder **{folder_name}** is already empty.")
        embed = create_embed(
            title="⚠️ Wipe Folder",
            description=f"React ✅ to remove all {count} alters from **{folder_name}**, or ❌ to cancel."
        )
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('✅'); await msg.add_reaction('❌')
        def c(r,u): return u==ctx.author and r.message.id==msg.id and str(r.emoji) in ['✅','❌']
        try:
            r,_ = await self.bot.wait_for('reaction_add', timeout=60.0, check=c)
            if str(r.emoji)=='✅':
                folder['alters'].clear()
                db.save_profile(user_id, profile)
                await ctx.send(f"✅ Cleared all alters from **{folder_name}**.")
            else:
                await ctx.send("❌ Cancelled.")
        except asyncio.TimeoutError:
            await ctx.send("⏰ Timed out.")

    @commands.command(name="list_folders")
    async def list_folders(self, ctx):
        """List all folders."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        folders = profile.get('folders', {})
        if not folders:
            return await ctx.send("❌ No folders found. Use `!create_folder <name>`. ")
        embed = create_embed(
            title="📂 Your Folders",
            description=f"Total: {len(folders)} folder(s)"
        )
        for name, data in folders.items():
            desc = data.get('description') or 'No description'
            if len(desc)>100: desc=desc[:97]+"..."
            count = len(data.get('alters', []))
            embed.add_field(
                name=f"📁 {name}",
                value=f"📝 {desc}\n👥 {count} alter(s)",
                inline=False
            )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(FolderCommands(bot))
