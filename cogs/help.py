print("🔍 cogs.help module loaded (reaction version)")
import asyncio
import discord
from discord.ext import commands

class HelpPaginator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("HelpPaginator (reaction) initialized")

    def create_help_embeds(self) -> list[discord.Embed]:
        """
        Creates the list of embeds for each help page.
        """
        embeds: list[discord.Embed] = []

        # Page 0: System Management
        embed0 = discord.Embed(
            title="🗂️ System Management Commands",
            description="Commands to manage your system and profiles.",
            color=0x8A2BE2
        )
        embed0.add_field(name="`!create_system <name>`", value="Create a new system.", inline=False)
        embed0.add_field(name="`!edit_system`", value="Edit your existing system (name, avatar, banner, description, pronouns, color).", inline=False)
        embed0.add_field(name="`!delete_system`", value="Delete your system permanently.", inline=False)
        embed0.add_field(name="`!system`", value="Show your system's info, including avatars, banners, and colors.", inline=False)
        embed0.add_field(name="`!tag <tag>`", value="Set a system tag that gets appended to all proxied messages.", inline=False)
        embed0.add_field(name="`!export_system`", value="Export your entire system to a JSON file (sent to DMs).", inline=False)
        embed0.add_field(name="`!import_system`", value="Import a previously exported system from a JSON file.", inline=False)
        embed0.add_field(name="`!acc_add <username>`", value="Add a linked account to your system.", inline=False)
        embeds.append(embed0)

        # Page 1: Profile and Alter Management
        embed1 = discord.Embed(
            title="👥 Profile and Alter Management Commands",
            description="Commands to manage alters and profiles.",
            color=0x8A2BE2
        )
        embed1.add_field(name="`!create <name> [pronouns] [description]`", value="Create a new profile.", inline=False)
        embed1.add_field(name="`!edit <name>`", value="Edit an existing profile (name, displayname, pronouns, description, avatar, banner, proxy, color, proxy avatar).", inline=False)
        embed1.add_field(name="`!show <name>`", value="Show a profile, including avatars, banners, and colors.", inline=False)
        embed1.add_field(name="`!list_profiles`", value="List all profiles in the current system.", inline=False)
        embed1.add_field(name="`!delete <name>`", value="Delete a profile.", inline=False)
        embed1.add_field(name="`!alias <name> <alias>`", value="Add an alias to a profile.", inline=False)
        embed1.add_field(name="`!remove_alias <name> <alias>`", value="Remove an alias from a profile.", inline=False)
        embeds.append(embed1)

        # Page 2: Folder Management
        embed2 = discord.Embed(
            title="📁 Folder Management Commands",
            description="Commands to manage folders and organize alters.",
            color=0x8A2BE2
        )
        embed2.add_field(name="`!create_folder <name>`", value="Create a new folder with a name, color, banner, icon, and alters.", inline=False)
        embed2.add_field(name="`!edit_folder <folder name>`", value="Edit an existing folder.", inline=False)
        embed2.add_field(name="`!delete_folder <folder name>`", value="Delete a folder.", inline=False)
        embed2.add_field(name="`!wipe_folder_alters <folder name>`", value="Remove all alters from a folder.", inline=False)
        embed2.add_field(name="`!show_folder <folder name>`", value="Show the contents of a folder.", inline=False)
        embed2.add_field(name="`!list_folders`", value="Shows all folders with descriptions and alter counts.", inline=False)
        embed2.add_field(name="`!add_alters <folder name> <alter1, alter2>`", value="Add one or more alters to a folder.", inline=False)
        embed2.add_field(name="`!remove_alters <folder name> <alter1, alter2>`", value="Remove one or more alters from a folder.", inline=False)
        embeds.append(embed2)

        # Page 3: Proxy Management
        embed3 = discord.Embed(
            title="🗨️ Proxy Management Commands",
            description="Commands to manage message proxying and autoproxy.",
            color=0x8A2BE2
        )
        embed3.add_field(name="`!proxyavatar <name> [url]`", value="Set a separate avatar for proxying.", inline=False)
        embed3.add_field(name="`!proxy <message>`", value="Send a proxied message.", inline=False)
        embed3.add_field(name="`!set_proxy <name> <proxy>`", value="Set a proxy for an alter (e.g., 'A: TEXT' or 'TEXT :a').", inline=False)
        embed3.add_field(name="`!autoproxy latch`", value="Enable autoproxy latch mode.", inline=False)
        embed3.add_field(name="`!autoproxy front <name>`", value="Set autoproxy to a specific alter.", inline=False)
        embed3.add_field(name="`!autoproxy off`", value="Disable autoproxy.", inline=False)
        embed3.add_field(name="`!edit <message_link> <new_content>`", value="Edit a recently proxied message.", inline=False)
        embeds.append(embed3)

        # Page 4: Import and Export
        embed4 = discord.Embed(
            title="📤 Import and Export Commands",
            description="Commands to import/export data and manage backups.",
            color=0x8A2BE2
        )
        embed4.add_field(name="`!export_system`", value="Export your entire system to a JSON file (sent to DMs).", inline=False)
        embed4.add_field(name="`!import_system`", value="Import a previously exported system from a JSON file.", inline=False)
        embed4.add_field(name="`!import_pluralkit`", value="Import your PluralKit profiles, including proxy avatars and colors.", inline=False)
        embeds.append(embed4)

        # Page 5: Admin Commands
        embed5 = discord.Embed(
            title="🔧 Admin Commands",
            description="Server administration commands (admin only).",
            color=0x8A2BE2
        )
        embed5.add_field(name="`!blacklist_channel <channel>`", value="Blacklist a channel from proxy detection (admin only).", inline=False)
        embed5.add_field(name="`!blacklist_category <category>`", value="Blacklist an entire category from proxy detection (admin only).", inline=False)
        embed5.add_field(name="`!list_blacklists`", value="List all blacklisted channels and categories (admin only).", inline=False)
        embed5.add_field(name="`!admin_commands`", value="Display all admin commands (admin only).", inline=False)
        embeds.append(embed5)

        # Page 6: Utility Commands
        embed6 = discord.Embed(
            title="🛠️ Utility Commands",
            description="General utility and information commands.",
            color=0x8A2BE2
        )
        embed6.add_field(name="`!pixel`", value="Check the bot's current speed and latency (admin only).", inline=False)
        embed6.add_field(name="`!pixelhelp`", value="Show the full command list (this menu).", inline=False)
        embeds.append(embed6)

        return embeds

    @commands.command(name='pixelhelp')
    async def pixelhelp(self, ctx: commands.Context):
        """
        Display paginated help via reactions.
        """
        embeds = self.create_help_embeds()
        current_page = 0

        # Send the first embed
        embed = embeds[current_page]
        embed.set_footer(text=f"Page {current_page + 1}/{len(embeds)} • Use ⬅️ ➡️ to navigate")
        message = await ctx.send(embed=embed)

        # Add navigation reactions
        for emoji in ('⬅️', '➡️'):
            await message.add_reaction(emoji)

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return (
                user == ctx.author and
                reaction.message.id == message.id and
                str(reaction.emoji) in ('⬅️', '➡️')
            )

        while True:
            try:
                reaction, user = await self.bot.wait_for(
                    'reaction_add', check=check
                )
                if str(reaction.emoji) == '➡️':
                    current_page = (current_page + 1) % len(embeds)
                else:
                    current_page = (current_page - 1) % len(embeds)

                embed = embeds[current_page]
                embed.set_footer(text=f"Page {current_page + 1}/{len(embeds)} • Use ⬅️ ➡️ to navigate")
                await message.edit(embed=embed)

                try:
                    await message.remove_reaction(reaction.emoji, user)
                except discord.Forbidden:
                    # no Manage Messages permission
                    pass

            except Exception as e:
                print(f"⚠️ Pagination error: {e}")
                # continue listening if non-fatal
                continue

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpPaginator(bot))
    print("✅ HelpPaginator (reaction) cog added (async)")
