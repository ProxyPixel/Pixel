import discord
from discord.ext import commands
from utils.mongodb import db
import time
import asyncio

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_admin(ctx):
        """Check if user has administrator permissions."""
        return ctx.author.guild_permissions.administrator

    @commands.command(name="pixel")
    @commands.check(is_admin)
    async def pixel_status(self, ctx):
        """Check the bot's current speed and latency (admin only)."""
        
        start_time = time.time()
        
        # Test message send latency
        message = await ctx.send("🔄 Testing bot latency...")
        
        end_time = time.time()
        message_latency = (end_time - start_time) * 1000
        
        # Get websocket latency
        ws_latency = self.bot.latency * 1000
        
        embed = discord.Embed(
            title="🤖 PIXEL Bot Status",
            color=0x8A2BE2
        )
        embed.add_field(name="📡 WebSocket Latency", value=f"{ws_latency:.2f}ms", inline=True)
        embed.add_field(name="💬 Message Latency", value=f"{message_latency:.2f}ms", inline=True)
        embed.add_field(name="🟢 Status", value="Online & Operational", inline=True)
        
        # Add server count if bot is in multiple servers
        server_count = len(self.bot.guilds)
        embed.add_field(name="🌐 Servers", value=str(server_count), inline=True)
        
        # Add user count
        user_count = sum(guild.member_count for guild in self.bot.guilds)
        embed.add_field(name="👥 Total Users", value=str(user_count), inline=True)
        
        # Add MongoDB status
        try:
            db.connect()
            embed.add_field(name="📊 Database", value="Connected", inline=True)
        except Exception as e:
            embed.add_field(name="📊 Database", value="Error", inline=True)
        
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        
        await message.edit(content=None, embed=embed)

    @commands.command(name="blacklist_channel")
    @commands.check(is_admin)
    async def blacklist_channel(self, ctx, channel: discord.TextChannel):
        """Blacklist a channel from proxy detection (admin only)."""
        
        guild_id = str(ctx.guild.id)
        
        # Get or create blacklist settings
        blacklist = db.get_blacklist(guild_id)
        if not blacklist:
            blacklist = {"guild_id": guild_id, "channels": [], "categories": []}
        
        if channel.id in blacklist["channels"]:
            await ctx.send(f"❌ {channel.mention} is already blacklisted.")
            return
        
        blacklist["channels"].append(channel.id)
        db.save_blacklist(guild_id, blacklist)
        
        embed = discord.Embed(
            title="✅ Channel Blacklisted",
            description=f"{channel.mention} has been blacklisted from proxy detection.",
            color=0x8A2BE2
        )
        await ctx.send(embed=embed)

    @commands.command(name="blacklist_category")
    @commands.check(is_admin)
    async def blacklist_category(self, ctx, category: discord.CategoryChannel):
        """Blacklist an entire category from proxy detection (admin only)."""
        
        guild_id = str(ctx.guild.id)
        
        # Get or create blacklist settings
        blacklist = db.get_blacklist(guild_id)
        if not blacklist:
            blacklist = {"guild_id": guild_id, "channels": [], "categories": []}
        
        if category.id in blacklist["categories"]:
            await ctx.send(f"❌ Category '{category.name}' is already blacklisted.")
            return
        
        blacklist["categories"].append(category.id)
        db.save_blacklist(guild_id, blacklist)
        
        embed = discord.Embed(
            title="✅ Category Blacklisted",
            description=f"Category '{category.name}' and all its channels have been blacklisted from proxy detection.",
            color=0x8A2BE2
        )
        await ctx.send(embed=embed)

    @commands.command(name="list_blacklists")
    @commands.check(is_admin)
    async def list_blacklists(self, ctx):
        """List all blacklisted channels and categories (admin only)."""
        
        guild_id = str(ctx.guild.id)
        
        # Get blacklist settings
        blacklist = db.get_blacklist(guild_id)
        if not blacklist:
            blacklist = {"channels": [], "categories": []}
        
        embed = discord.Embed(
            title="🚫 Blacklisted Channels & Categories",
            color=0x8A2BE2
        )
        
        # List blacklisted channels
        if blacklist["channels"]:
            channel_mentions = []
            for channel_id in blacklist["channels"]:
                channel = self.bot.get_channel(channel_id)
                if channel:
                    channel_mentions.append(channel.mention)
                else:
                    channel_mentions.append(f"Unknown Channel (ID: {channel_id})")
            
            embed.add_field(
                name="📺 Blacklisted Channels",
                value="\n".join(channel_mentions) if channel_mentions else "None",
                inline=False
            )
        else:
            embed.add_field(name="📺 Blacklisted Channels", value="None", inline=False)
        
        # List blacklisted categories
        if blacklist["categories"]:
            category_names = []
            for category_id in blacklist["categories"]:
                category = self.bot.get_channel(category_id)
                if category:
                    category_names.append(f"📁 {category.name}")
                else:
                    category_names.append(f"Unknown Category (ID: {category_id})")
            
            embed.add_field(
                name="📁 Blacklisted Categories",
                value="\n".join(category_names) if category_names else "None",
                inline=False
            )
        else:
            embed.add_field(name="📁 Blacklisted Categories", value="None", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="admin_commands")
    @commands.check(is_admin)
    async def admin_commands(self, ctx):
        """Display all admin commands (admin only)."""
        
        embed = discord.Embed(
            title="🔧 Admin Commands",
            description="Available administrative commands for PIXEL bot.",
            color=0x8A2BE2
        )
        
        embed.add_field(
            name="🚫 Blacklist Management",
            value="`!blacklist_channel <channel>` - Blacklist a channel\n"
                  "`!blacklist_category <category>` - Blacklist a category\n"
                  "`!list_blacklists` - View all blacklists",
            inline=False
        )
        
        embed.add_field(
            name="🛠️ Utility",
            value="`!pixel` - Check bot status and latency\n"
                  "`!admin_commands` - Show this menu",
            inline=False
        )
        
        embed.set_footer(text="All admin commands require Administrator permissions.")
        await ctx.send(embed=embed)

    @pixel_status.error
    @blacklist_channel.error
    @blacklist_category.error
    @list_blacklists.error
    @admin_commands.error
    async def admin_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.send("❌ You need Administrator permissions to use this command.")
        else:
            await ctx.send(f"❌ An error occurred: {error}")

async def setup(bot):
    """Set up the admin cog."""
    await bot.add_cog(AdminCommands(bot))
