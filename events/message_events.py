from discord.ext import commands

class MessageEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Removed on_message handler - Discord.py processes commands automatically
    # This was causing duplicate command execution

async def setup(bot):
    await bot.add_cog(MessageEvents(bot))
