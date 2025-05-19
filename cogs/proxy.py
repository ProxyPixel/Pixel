<<<<<<< HEAD
import discord
from discord.ext import commands
from utils.profiles import load_profiles, save_profiles
import aiohttp

global_profiles = load_profiles()

class ProxyCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="proxyavatar")
    async def proxyavatar(self, ctx, name: str):
        """Set a separate avatar for proxying."""
        user_id = str(ctx.author.id)
        user_profiles = global_profiles.get(user_id, {}).get("alters", {})

        if name not in user_profiles:
            await ctx.send(f"❌ Alter **{name}** does not exist.")
            return

        profile = user_profiles[name]

        if ctx.message.attachments:
            image_url = ctx.message.attachments[0].url
        elif ctx.message.content.startswith("http"):
            image_url = ctx.message.content.split(" ")[-1].strip()
        else:
            await ctx.send("❌ Invalid proxy avatar input. Please provide a direct image URL or attachment.")
            return

        profile["proxy_avatar"] = image_url
        save_profiles(global_profiles)
        await ctx.send(f"✅ Proxy avatar for **{name}** updated successfully!")

    @commands.command(name="set_proxy")
    async def set_proxy(self, ctx, name: str, *, proxy: str):
        """Set a proxy for an alter."""
        user_id = str(ctx.author.id)

        if name not in global_profiles.get(user_id, {}).get("alters", {}):
            await ctx.send(f"❌ Alter '{name}' does not exist.")
            return

        global_profiles[user_id]["alters"][name]["proxy"] = proxy
        save_profiles(global_profiles)
        await ctx.send(f"✅ Proxy for '{name}' has been set to `{proxy}`.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        user_id = str(message.author.id)
        user_profiles = global_profiles.get(user_id, {}).get("alters", {})

        for name, profile in user_profiles.items():
            proxy = profile.get("proxy")
            displayname = profile.get("displayname", name)
            proxy_avatar = profile.get("proxy_avatar") or profile.get("avatar")

            if proxy and message.content.startswith(proxy):
                clean_message = message.content[len(proxy):].strip()

                if message.guild:
                    webhook = await message.channel.create_webhook(name=displayname)

                    if proxy_avatar:
                        try:
                            async with aiohttp.ClientSession() as session:
                                async with session.get(proxy_avatar) as response:
                                    if response.status == 200:
                                        avatar_bytes = await response.read()
                                        await webhook.edit(avatar=avatar_bytes)
                                    else:
                                        print(f"Failed to fetch avatar for {displayname}: {response.status}")
                        except Exception as e:
                            print(f"Error setting avatar for {displayname}: {e}")

         
                    await webhook.send(
                        content=clean_message,
                        username=displayname,
                        allowed_mentions=discord.AllowedMentions.none()
                    )

                    # Delete the original message to prevent double posting
                    try:
                        await message.delete()
                    except discord.Forbidden:
                        print(f"⚠️ Missing permissions to delete message in {message.channel.name}")

                    # Delete the webhook after sending the message
                    await webhook.delete()
                else:
                    # Send the message directly in DMs without using a webhook
                    await message.channel.send(
                        content=clean_message,
                        username=displayname,
                        allowed_mentions=discord.AllowedMentions.none()
                    )

                return  # Stop after the first matching proxy is found

def setup(bot):
    bot.add_cog(ProxyCommands(bot))
||||||| empty tree
=======
import discord
from discord.ext import commands
from utils.profiles import load_profiles, save_profiles
import aiohttp

global_profiles = load_profiles()

class ProxyCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="proxyavatar")
    async def proxyavatar(self, ctx, name: str):
        """Set a separate avatar for proxying."""
        user_id = str(ctx.author.id)
        user_profiles = global_profiles.get(user_id, {}).get("alters", {})

        if name not in user_profiles:
            await ctx.send(f"❌ Alter **{name}** does not exist.")
            return

        profile = user_profiles[name]

        # Check if there is an attachment or a URL in the same command
        if ctx.message.attachments:
            image_url = ctx.message.attachments[0].url
        elif ctx.message.content.startswith("http"):
            image_url = ctx.message.content.split(" ")[-1].strip()
        else:
            await ctx.send("❌ Invalid proxy avatar input. Please provide a direct image URL or attachment.")
            return

        # Save the proxy avatar
        profile["proxy_avatar"] = image_url
        save_profiles(global_profiles)
        await ctx.send(f"✅ Proxy avatar for **{name}** updated successfully!")

    @commands.command(name="set_proxy")
    async def set_proxy(self, ctx, name: str, *, proxy: str):
        """Set a proxy for an alter."""
        user_id = str(ctx.author.id)

        if name not in global_profiles.get(user_id, {}).get("alters", {}):
            await ctx.send(f"❌ Alter '{name}' does not exist.")
            return

        global_profiles[user_id]["alters"][name]["proxy"] = proxy
        save_profiles(global_profiles)
        await ctx.send(f"✅ Proxy for '{name}' has been set to `{proxy}`.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        user_id = str(message.author.id)
        user_profiles = global_profiles.get(user_id, {}).get("alters", {})

        # Check each profile for a matching proxy
        for name, profile in user_profiles.items():
            proxy = profile.get("proxy")
            displayname = profile.get("displayname", name)
            proxy_avatar = profile.get("proxy_avatar") or profile.get("avatar")

            # If the profile has a proxy set, check for it
            if proxy and message.content.startswith(proxy):
                clean_message = message.content[len(proxy):].strip()

                # Create a webhook with the alter's display name (only for guilds)
                if message.guild:
                    webhook = await message.channel.create_webhook(name=displayname)

                    # Use the proxy avatar if it exists
                    if proxy_avatar:
                        try:
                            async with aiohttp.ClientSession() as session:
                                async with session.get(proxy_avatar) as response:
                                    if response.status == 200:
                                        avatar_bytes = await response.read()
                                        # Update the webhook to use the proxy avatar
                                        await webhook.edit(avatar=avatar_bytes)
                                    else:
                                        print(f"Failed to fetch avatar for {displayname}: {response.status}")
                        except Exception as e:
                            print(f"Error setting avatar for {displayname}: {e}")

                    # Send the proxied message
                    await webhook.send(
                        content=clean_message,
                        username=displayname,
                        allowed_mentions=discord.AllowedMentions.none()
                    )

                    # Delete the original message to prevent double posting
                    try:
                        await message.delete()
                    except discord.Forbidden:
                        print(f"⚠️ Missing permissions to delete message in {message.channel.name}")

                    # Delete the webhook after sending the message
                    await webhook.delete()
                else:
                    # Send the message directly in DMs without using a webhook
                    await message.channel.send(
                        content=clean_message,
                        username=displayname,
                        allowed_mentions=discord.AllowedMentions.none()
                    )

                return  # Stop after the first matching proxy is found

def setup(bot):
    bot.add_cog(ProxyCommands(bot))
>>>>>>> 148e586dd485e85a7336569dd4700d06a440eff4
