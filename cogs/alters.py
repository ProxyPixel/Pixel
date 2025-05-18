from discord.ext import commands
from utils.profiles import load_profiles, save_profiles

global_profiles = load_profiles()

class AlterCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="create")
    async def create_alter(self, ctx, name: str, pronouns: str, *, description: str = "No description provided."):
        user_id = str(ctx.author.id)

        if user_id not in global_profiles:
            global_profiles[user_id] = {"system": {}, "alters": {}, "folders": {}}

        if name in global_profiles[user_id]["alters"]:
            await ctx.send(f"❌ An alter with the name **{name}** already exists.")
            return

        global_profiles[user_id]["alters"][name] = {
            "displayname": name,
            "pronouns": pronouns,
            "description": description,
            "avatar": None,
            "banner": None,
            "proxy": None,
            "aliases": [],
            "color": 0x8A2BE2
        }
        save_profiles(global_profiles)
        await ctx.send(f"✅ Alter '{name}' created successfully!")

    @commands.command(name="delete")
    async def delete_alter(self, ctx, name: str):
        user_id = str(ctx.author.id)

        if name in global_profiles.get(user_id, {}).get("alters", {}):
            del global_profiles[user_id]["alters"][name]
            save_profiles(global_profiles)
            await ctx.send(f"🗑️ Alter '{name}' deleted successfully!")
        else:
            await ctx.send(f"❌ Alter '{name}' does not exist.")

def setup(bot):
    bot.add_cog(AlterCommands(bot))
