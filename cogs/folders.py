from discord.ext import commands
from utils.profiles import load_profiles, save_profiles

global_profiles = load_profiles()

class FolderCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="create_folder")
    async def create_folder(self, ctx, *, folder_name: str):
        user_id = str(ctx.author.id)

        if user_id not in global_profiles:
            global_profiles[user_id] = {"system": {}, "alters": {}, "folders": {}}

        if folder_name in global_profiles[user_id]["folders"]:
            await ctx.send(f"⚠️ Folder '{folder_name}' already exists. Use `!edit_folder` to modify it.")
            return

        global_profiles[user_id]["folders"][folder_name] = {
            "name": folder_name,
            "color": 0x8A2BE2,
            "alters": []
        }
        save_profiles(global_profiles)
        await ctx.send(f"✅ Folder '{folder_name}' created successfully!")

    @commands.command(name="delete_folder")
    async def delete_folder(self, ctx, *, folder_name: str):
        user_id = str(ctx.author.id)

        if folder_name in global_profiles.get(user_id, {}).get("folders", {}):
            del global_profiles[user_id]["folders"][folder_name]
            save_profiles(global_profiles)
            await ctx.send(f"🗑️ Folder '{folder_name}' deleted successfully!")
        else:
            await ctx.send(f"❌ Folder '{folder_name}' does not exist.")

def setup(bot):
    bot.add_cog(FolderCommands(bot))
