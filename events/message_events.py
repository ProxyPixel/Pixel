from discord.ext import commands

class MessageEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        # Process regular commands
        await self.bot.process_commands(message)

def setup(bot):
    bot.add_cog(MessageEvents(bot))
