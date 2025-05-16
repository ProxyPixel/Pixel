import discord
from discord.ext import commands, tasks
import random

status_options = [
    "Managing systems",
    "Proxying messages",
    "Organizing folders",
    "Handling proxies",
    "!pixelhelp for all commands",
    "Connecting systems",
    "Serving multiple servers"
]

class ReadyEvent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.change_status.start()

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅ Bot is online as {self.bot.user}")

    @tasks.loop(minutes=1)
    async def change_status(self):
        """Loop to change status every minute."""
        new_status = random.choice(status_options)
        await self.bot.change_presence(activity=discord.Game(name=new_status))

def setup(bot):
    bot.add_cog(ReadyEvent(bot))
