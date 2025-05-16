from discord.ext import commands
from utils.blacklist import load_blacklist, save_blacklist

channel_blacklist = load_blacklist()

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="blacklist_channel")
    @commands.has_permissions(administrator=True)
    async def blacklist_channel(self, ctx, channel_id: int):
        if channel_id not in channel_blacklist:
            channel_blacklist.append(channel_id)
            save_blacklist(channel_blacklist)
            await ctx.send(f"🚫 Channel with ID `{channel_id}` has been blacklisted.")
        else:
            await ctx.send(f"⚠️ Channel is already blacklisted.")

def setup(bot):
    bot.add_cog(AdminCommands(bot))
