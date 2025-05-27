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
        # Ensure MongoDB connection on load
        db.connect()

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
            db.connect()
            embed.add_field(name="📊 Database", value="Connected", inline=True)
        except Exception:
            embed.add_field(name="📊 Database", value="Error", inline=True)

        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await msg.edit(content=None, embed=embed)

    @commands.command(name="blacklist_channel")
    @commands.check(is_admin)
    async def blacklist_channel(self, ctx, channel: discord.TextChannel):
        """Blacklist a channel from proxy detection (admin only)."""
        guild_id = str(ctx.guild.id)
        entry = db.get_blacklist(guild_id) or {"guild_id": guild_id, "channels": [], "categories": []}

        if channel.id in entry.get("channels", []):
            return await ctx.send(f"❌ {channel.mention} is already blacklisted.")

        entry.setdefault("channels", []).append(channel.id)
        db.save_blacklist(guild_id, entry)
        await ctx.send(embed=discord.Embed(
            title="✅ Channel Blacklisted",
            description=f"{channel.mention} has been blacklisted from proxy detection.",
            color=0x8A2BE2
        ))

    @commands.command(name="blacklist_category")
    @commands.check(is_admin)
    async def blacklist_category(self, ctx, category: discord.CategoryChannel):
        """Blacklist an entire category from proxy detection (admin only)."""
        guild_id = str(ctx.guild.id)
        entry = db.get_blacklist(guild_id) or {"guild_id": guild_id, "channels": [], "categories": []}

        if category.id in entry.get("categories", []):
            return await ctx.send(f"❌ Category '{category.name}' is already blacklisted.")

        entry.setdefault("categories", []).append(category.id)
        db.save_blacklist(guild_id, entry)
        await ctx.send(embed=discord.Embed(
            title="✅ Category Blacklisted",
            description=f"Category '{category.name}' has been blacklisted from proxy detection.",
            color=0x8A2BE2
        ))

    @commands.command(name="list_blacklists")
    @commands.check(is_admin)
    async def list_blacklists(self, ctx):
        """List all blacklisted channels and categories (admin only)."""
        guild_id = str(ctx.guild.id)
        entry = db.get_blacklist(guild_id) or {"channels": [], "categories": []}

        embed = discord.Embed(title="🚫 Blacklisted Channels & Categories", color=0x8A2BE2)
        # Channels
        chans = entry.get("channels", [])
        if chans:
            embed.add_field(
                name="📺 Channels", 
                value="\n".join(
                    channel.mention if (channel := self.bot.get_channel(cid)) else f"Unknown ID {cid}" 
                    for cid in chans
                ),
                inline=False
            )
        else:
            embed.add_field(name="📺 Channels", value="None", inline=False)
        # Categories
        cats = entry.get("categories", [])
        if cats:
            embed.add_field(
                name="📁 Categories",
                value="\n".join(
                    f"{self.bot.get_channel(cid).name}" if self.bot.get_channel(cid) else f"Unknown ID {cid}"
                    for cid in cats
                ),
                inline=False
            )
        else:
            embed.add_field(name="📁 Categories", value="None", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="admin_commands")
    @commands.check(is_admin)
    async def admin_commands(self, ctx):
        """Display all admin commands (admin only)."""
        embed = discord.Embed(title="🔧 Admin Commands", color=0x8A2BE2)
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
