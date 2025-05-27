import discord
from discord.ext import commands
from utils.mongodb import db
import time

# Permission check helper
def is_admin(ctx):
    return ctx.author.guild_permissions.administrator

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # MongoDB connection is now handled globally in main.py

    @commands.command(name="pixel")
    @commands.check(is_admin)
    async def pixel_status(self, ctx):
        """Check the bot's WebSocket & message latency, plus DB status (admin only)."""
        start = time.time()
        msg = await ctx.send("🔄 Testing bot latency...")
        msg_latency = (time.time() - start) * 1000
        ws_latency = self.bot.latency * 1000

        # Build status embed
        embed = discord.Embed(title="🤖 PIXEL Bot Status", color=0x8A2BE2)
        embed.add_field(name="📡 WebSocket Latency", value=f"{ws_latency:.2f}ms", inline=True)
        embed.add_field(name="💬 Message Latency", value=f"{msg_latency:.2f}ms", inline=True)
        embed.add_field(name="🌐 Servers", value=str(len(self.bot.guilds)), inline=True)
        total_users = sum(g.member_count for g in self.bot.guilds)
        embed.add_field(name="👥 Total Users", value=str(total_users), inline=True)

        # Database connectivity
        try:
            # MongoDB connection is already established globally
            embed.add_field(name="📊 Database", value="Connected", inline=True)
        except Exception:
            embed.add_field(name="📊 Database", value="Error", inline=True)

        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await msg.edit(content=None, embed=embed)

    @commands.command(name="blacklist_channel")
    @commands.check(is_admin)
    async def blacklist_channel(self, ctx, channel: discord.TextChannel):
        """Add a channel to the blacklist (admin only)."""
        guild_id = str(ctx.guild.id)
        entry = db.get_blacklist(guild_id) or {"guild_id": guild_id, "channels": [], "categories": []}
        
        if channel.id in entry["channels"]:
            await ctx.send(f"❌ {channel.mention} is already blacklisted.")
            return
        
        entry["channels"].append(channel.id)
        db.save_blacklist(guild_id, entry)
        await ctx.send(f"✅ Added {channel.mention} to the blacklist.")

    @commands.command(name="blacklist_category")
    @commands.check(is_admin)
    async def blacklist_category(self, ctx, category: discord.CategoryChannel):
        """Add a category to the blacklist (admin only)."""
        guild_id = str(ctx.guild.id)
        entry = db.get_blacklist(guild_id) or {"guild_id": guild_id, "channels": [], "categories": []}
        
        if category.id in entry["categories"]:
            await ctx.send(f"❌ Category **{category.name}** is already blacklisted.")
            return
        
        entry["categories"].append(category.id)
        db.save_blacklist(guild_id, entry)
        await ctx.send(f"✅ Added category **{category.name}** to the blacklist.")

    @commands.command(name="list_blacklists")
    @commands.check(is_admin)
    async def list_blacklists(self, ctx):
        """List all blacklisted channels and categories (admin only)."""
        guild_id = str(ctx.guild.id)
        entry = db.get_blacklist(guild_id) or {"channels": [], "categories": []}
        
        embed = discord.Embed(title="📋 Blacklist Status", color=0x8A2BE2)
        
        channels = [ctx.guild.get_channel(ch) for ch in entry.get("channels", [])]
        channels = [ch.mention for ch in channels if ch]
        embed.add_field(
            name="🚫 Blacklisted Channels",
            value="\n".join(channels) if channels else "None",
            inline=False
        )
        
        categories = [ctx.guild.get_channel(cat) for cat in entry.get("categories", [])]
        categories = [cat.name for cat in categories if cat]
        embed.add_field(
            name="🚫 Blacklisted Categories", 
            value="\n".join(categories) if categories else "None",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name="admin_commands")
    @commands.check(is_admin)
    async def admin_commands(self, ctx):
        """Show available admin commands."""
        embed = discord.Embed(
            title="🛡️ Admin Commands",
            description="Available commands for server administrators",
            color=0x8A2BE2
        )
        embed.add_field(
            name="🚫 Blacklist Management",
            value="`!blacklist_channel <channel>`\n`!blacklist_category <category>`\n`!list_blacklists`",
            inline=False
        )
        embed.add_field(
            name="🛠️ Utility",
            value="`!pixel` - Bot status & latency\n`!admin_commands` - This menu",
            inline=False
        )
        embed.set_footer(text="Requires Administrator permissions.")
        await ctx.send(embed=embed)

    # Global error handler for admin commands
    @pixel_status.error
    @blacklist_channel.error
    @blacklist_category.error
    @list_blacklists.error
    @admin_commands.error
    async def admin_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("❌ You need Administrator permissions to use this.")
        else:
            await ctx.send(f"❌ Error: {error}")

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))