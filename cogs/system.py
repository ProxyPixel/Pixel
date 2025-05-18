from discord.ext import commands
from utils.profiles import load_profiles, save_profiles

global_profiles = load_profiles()

class SystemCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="create_system")
    async def create_system(self, ctx, *, system_name: str):
        user_id = str(ctx.author.id)

        if user_id not in global_profiles:
            global_profiles[user_id] = {"system": {}, "alters": {}, "folders": {}}

        if "system" in global_profiles[user_id]:
            await ctx.send("❌ You already have a system. Use `!edit_system` to modify it.")
            return

        global_profiles[user_id]["system"] = {
            "name": system_name,
            "description": "No description provided.",
            "avatar": None,
            "banner": None,
            "pronouns": "Not set",
            "color": 0x8A2BE2
        }
        save_profiles(global_profiles)
        await ctx.send(f"✅ System '{system_name}' created successfully!")

    @commands.command(name="delete_system")
    async def delete_system(self, ctx):
        user_id = str(ctx.author.id)

        if user_id in global_profiles and "system" in global_profiles[user_id]:
            del global_profiles[user_id]["system"]
            save_profiles(global_profiles)
            await ctx.send("🗑️ System deleted successfully!")
        else:
            await ctx.send("❌ You don't have a system to delete.")

def setup(bot):
    bot.add_cog(SystemCommands(bot))
