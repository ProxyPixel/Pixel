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
        embed0.add_field(name="`!edit_system`", value="Edit your existing system.", inline=False)
        embed0.add_field(name="`!delete_system`", value="Delete your system permanently.", inline=False)
        embed0.add_field(name="`!system`", value="Display system info.", inline=False)
        embed0.add_field(name="`!export_system`", value="Export your system data to JSON.", inline=False)
        embed0.add_field(name="`!import_system`", value="Import system data from JSON.", inline=False)
        embeds.append(embed0)

        # Page 1: Profile Management
        embed1 = discord.Embed(
            title="👥 Profile Management Commands",
            description="Commands to manage alters and profiles.",
            color=0x8A2BE2
        )
        embed1.add_field(name="`!create <name> <pronouns>`", value="Create a new profile with specified pronouns.", inline=False)
        embed1.add_field(name="`!edit <name>`", value="Edit an existing profile.", inline=False)
        embed1.add_field(name="`!delete <name>`", value="Delete a profile.", inline=False)
        embed1.add_field(name="`!show <name>`", value="Display profile info.", inline=False)
        embed1.add_field(name="`!list_profiles`", value="List all profiles.", inline=False)
        embeds.append(embed1)

        # Page 2: Folder Management
        embed2 = discord.Embed(
            title="📁 Folder Management Commands",
            description="Commands to manage folders and organize alters.",
            color=0x8A2BE2
        )
        embed2.add_field(name="`!create_folder <name>`", value="Create a new folder.", inline=False)
        embed2.add_field(name="`!edit_folder <name>`", value="Edit an existing folder.", inline=False)
        embed2.add_field(name="`!delete_folder <name>`", value="Delete a folder permanently.", inline=False)
        embed2.add_field(name="`!show_folder <name>`", value="Display folder info.", inline=False)
        embed2.add_field(name="`!list_folders`", value="List all folders.", inline=False)
        embeds.append(embed2)

        return embeds

    @commands.command(name='pixelhelp')
    async def pixelhelp(self, ctx: commands.Context):
        """
        Display paginated help via reactions.
        """
        embeds = self.create_help_embeds()
        current_page = 0

        # Send the first embed
        message = await ctx.send(embed=embeds[current_page])

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
                    'reaction_add', timeout=60.0, check=check
                )
                if str(reaction.emoji) == '➡️':
                    current_page = (current_page + 1) % len(embeds)
                else:
                    current_page = (current_page - 1) % len(embeds)

                await message.edit(embed=embeds[current_page])

                try:
                    await message.remove_reaction(reaction.emoji, user)
                except discord.Forbidden:
                    # no Manage Messages permission
                    pass

            except asyncio.TimeoutError:
                break
            except Exception as e:
                print(f"⚠️ Pagination error: {e}")
                # continue listening if non-fatal
                continue

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpPaginator(bot))
    print("✅ HelpPaginator (reaction) cog added (async)")
