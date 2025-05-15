import os
import discord
from discord.ext import commands, tasks
from flask import Flask, jsonify
import threading
import json
import random

app = Flask(__name__)

# Set up intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True

# Initialize the bot
bot = commands.Bot(command_prefix="!", intents=intents, case_insensitive=True)

bot.remove_command("help")  # Remove the default help command

# Status options
status_options = [
    "Managing systems",
    "Proxying messages",
    "Organizing folders",
    "Handling proxies",
    "!pixelhelp for all commands",
    "Connecting systems",
    "Serving multiple servers"
]

# Load global profiles from file
PROFILES_FILE = "global_profiles.json"

def load_global_profiles():
    if not os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE, "w") as f:
            json.dump({}, f)

    try:
        with open(PROFILES_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("Error: global_profiles.json is corrupted. Resetting file.")
        return {}

def save_profiles(data):
    with open(PROFILES_FILE, "w") as f:
        json.dump(data, f, indent=4)

global_profiles = load_global_profiles()

# Flask routes for health checks
@app.route("/")
def home():
    return "Bot is running!"

@app.route("/health")
def health():
    return jsonify({"status": "Bot is healthy!"})

# Discord bot events
@bot.event
async def on_ready():
    print(f"✅ Bot is online as {bot.user}")
    await update_status()
    change_status.start()

@tasks.loop(seconds=60)
async def change_status():
    await update_status()

async def update_status():
    new_status = random.choice(status_options)
    await bot.change_presence(activity=discord.Game(name=new_status))

# Run Flask server in a separate thread
def run_flask():
    app.run(host="0.0.0.0", port=8080)

# Run Discord bot in a separate thread
def run_discord():
    bot.run(os.getenv("NEW_BOT_TOKEN"))

# Start both Flask and Discord in separate threads
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    run_discord()


# Discord bot commands
@bot.command(name="create_system")
async def create_system(ctx, *, system_name: str):
    user_id = str(ctx.author.id)

    # Prevent creating multiple systems for the same user
    if "system" in global_profiles.get(user_id, {}):
        await ctx.send("You already have a system set up. Use `!edit_system` to modify it.")
        return

    # Create the system
    if user_id not in global_profiles:
        global_profiles[user_id] = {"system": {}, "alters": {}, "folders": {}}

    global_profiles[user_id]["system"] = {
        "name": system_name,
        "description": "No description provided.",
        "avatar": None,
        "banner": None,
        "pronouns": "Not set",
        "color": 0x8A2BE2  # Default to purple
    }

    save_profiles(global_profiles)
    await ctx.send(f"✅ System '{system_name}' created successfully!")

# Run Flask server in a separate thread
def run_flask():
    app.run(host="0.0.0.0", port=8080)


# Run both Flask and Discord bot
threading.Thread(target=run_flask).start()
run_discord()



@bot.command(name="edit_system")
async def edit_system(ctx):
    user_id = str(ctx.author.id)

    # Ensure the user has a system
    if user_id not in global_profiles or "system" not in global_profiles[user_id]:
        await ctx.send("❌ You don't have a system set up yet. Use `!create_system` to create one.")
        return

    system = global_profiles[user_id]["system"]

    # Ask what field the user wants to edit
    await ctx.send("What would you like to edit? (name, description, avatar, banner, pronouns, color)")

    try:
        field_msg = await bot.wait_for("message", timeout=60, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        field = field_msg.content.strip().lower()

        if field not in ["name", "description", "avatar", "banner", "pronouns", "color"]:
            await ctx.send(f"❌ Invalid field '{field}'. Use 'name', 'description', 'avatar', 'banner', 'pronouns', or 'color'.")
            return

        # Handle avatar and banner separately to accept URLs and attachments
        if field in ["avatar", "banner"]:
            await ctx.send(f"📂 Please send the new **{field}** as an **attachment** or a **direct image URL**.")

            try:
                image_msg = await bot.wait_for("message", timeout=120, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)

                # Check if the message has an attachment
                if image_msg.attachments:
                    image_url = image_msg.attachments[0].url
                elif image_msg.content.strip().startswith("http"):
                    image_url = image_msg.content.strip()
                else:
                    await ctx.send(f"❌ Invalid {field} input. Please provide a direct image URL or attachment.")
                    return

                # Save the image URL to the system
                system[field] = image_url
                save_profiles(global_profiles)
                await ctx.send(f"✅ {field.capitalize()} for your system updated successfully!")
                return

            except TimeoutError:
                await ctx.send("❌ You took too long to respond. Please try the command again.")
                return

        # Handle color separately to validate hex code
        if field == "color":
            await ctx.send("🎨 Please enter the new embed color as a **hex code** (e.g., `#8A2BE2`).")
            color_msg = await bot.wait_for("message", timeout=120, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
            color_code = color_msg.content.strip()

            # Validate the hex color code
            if not color_code.startswith("#") or len(color_code) != 7:
                await ctx.send("❌ Invalid color code. Please provide a **hex code** like `#8A2BE2`.")
                return

            # Convert hex color to integer for Discord embed
            try:
                color_int = int(color_code[1:], 16)
            except ValueError:
                await ctx.send("❌ Invalid hex code. Please try again.")
                return

            # Save the color to the system
            system["color"] = color_int
            save_profiles(global_profiles)
            await ctx.send(f"✅ Color for your system updated successfully!")
            return

        # Handle all other text-based fields
        await ctx.send(f"💬 Please enter the new value for **{field}**.")
        value_msg = await bot.wait_for("message", timeout=120, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        system[field] = value_msg.content.strip()

        # Save the updated system to the global profiles
        save_profiles(global_profiles)
        await ctx.send(f"✅ System **{system.get('name', 'Unnamed System')}** updated successfully!")

    except TimeoutError:
        await ctx.send("❌ You took too long to respond. Please try the command again.")

@bot.command(name="delete_system")
async def delete_system(ctx):
    user_id = str(ctx.author.id)

    # Check if the user has a system
    if user_id not in global_profiles or "system" not in global_profiles[user_id]:
        await ctx.send("❌ You don't have a system set up yet.")
        return

    # Confirm the deletion
    await ctx.send("⚠️ **Are you sure you want to delete your entire system?**\nThis action **cannot** be undone. Type `CONFIRM` to proceed.")

    try:
        # Wait for the user to confirm
        confirmation = await bot.wait_for(
            "message",
            timeout=60,
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
        )

        # Check if the user confirmed
        if confirmation.content.strip().upper() == "CONFIRM":
            # Delete the system and all alters
            del global_profiles[user_id]["system"]

            # Optionally delete all alters as well
            if "alters" in global_profiles[user_id]:
                del global_profiles[user_id]["alters"]

            # Save the changes
            save_profiles(global_profiles)
            await ctx.send("✅ Your system has been **permanently** deleted.")
        else:
            await ctx.send("❌ System deletion **canceled**.")

    except TimeoutError:
        await ctx.send("❌ You took too long to confirm. System deletion **canceled**.")




# Create a new profile with optional embed prompt
@bot.command(name="create")
async def create(ctx, name: str, pronouns: str, *, description: str = "No description provided."):
    user_id = str(ctx.author.id)

    # Ensure the user's system exists
    if user_id not in global_profiles:
        global_profiles[user_id] = {"system": {}, "alters": {}}

    # Ensure the "alters" key exists
    if "alters" not in global_profiles[user_id]:
        global_profiles[user_id]["alters"] = {}

    # Check if the alter already exists
    if name in global_profiles[user_id]["alters"]:
        await ctx.send(f"❌ An alter with the name **{name}** already exists.")
        return

    # Ask if the user wants the profile to use an embed
    await ctx.send("🖼️ Would you like this profile to use **embeds**? (yes/no)")

    try:
        # Wait for the user's response
        response = await bot.wait_for(
            "message",
            timeout=60,
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
        )
        use_embed = response.content.strip().lower() in ["yes", "y"]

        # Create the alter profile
        global_profiles[user_id]["alters"][name] = {
            "displayname": name,
            "pronouns": pronouns,
            "description": description,
            "avatar": None,
            "proxyavatar": None,
            "banner": None,
            "proxy": None,
            "aliases": [],
            "color": 0x8A2BE2,  # Default to purple
            "use_embed": use_embed
        }

        # Save the profiles to file
        save_profiles(global_profiles)

        await ctx.send(f"✅ Profile **{name}** created successfully!")

    except TimeoutError:
        await ctx.send("❌ You took too long to respond. Please try the command again.")



# Edit an existing profile with interactive prompts, including color customization and proxy avatars
@bot.command(name="edit")
async def edit(ctx, name: str):
    user_id = str(ctx.author.id)

    # Ensure the user's profile exists
    if user_id not in global_profiles or name not in global_profiles[user_id]["alters"]:
        await ctx.send(f"❌ Profile '{name}' does not exist.")
        return

    profile = global_profiles[user_id]["alters"][name]

    # Ask what field the user wants to edit
    await ctx.send("What would you like to edit? (name, displayname, pronouns, description, avatar, proxyavatar, banner, proxy, color)")

    try:
        field_msg = await bot.wait_for("message", timeout=60, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        field = field_msg.content.strip().lower()

        # Validate the selected field
        valid_fields = ["name", "displayname", "pronouns", "description", "avatar", "proxyavatar", "banner", "proxy", "color"]
        if field not in valid_fields:
            await ctx.send(f"❌ Invalid field '{field}'. Please choose from: {', '.join(valid_fields)}.")
            return

        # Handle avatar, banner, and proxy_avatar separately to accept URLs and attachments
        if field in ["avatar", "banner", "proxyavatar"]:
            await ctx.send(f"📂 Please send the new **{field}** as an **attachment** or a **direct image URL**.")
            image_msg = await bot.wait_for("message", timeout=120, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)

            # Check if the message has an attachment
            if image_msg.attachments:
                image_url = image_msg.attachments[0].url
            elif image_msg.content.startswith("http"):
                image_url = image_msg.content.strip()
            else:
                await ctx.send(f"❌ Invalid {field} input. Please provide a direct image URL or attachment.")
                return

            # Update the profile with the new image URL
            profile[field] = image_url
            save_profiles(global_profiles)
            await ctx.send(f"✅ {field.replace('_', ' ').capitalize()} for profile '{name}' updated successfully!")
            return

        # Handle color separately to validate hex code
        if field == "color":
            await ctx.send("🎨 Please enter the new embed color as a **hex code** (e.g., `#8A2BE2`).")
            color_msg = await bot.wait_for("message", timeout=120, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
            color_code = color_msg.content.strip()

            # Validate the hex color code
            if not color_code.startswith("#") or len(color_code) != 7:
                await ctx.send("❌ Invalid color code. Please provide a **hex code** like `#8A2BE2`.")
                return

            # Convert hex color to integer for Discord embed
            try:
                color_int = int(color_code[1:], 16)
            except ValueError:
                await ctx.send("❌ Invalid hex code. Please try again.")
                return

            profile["color"] = color_int
            save_profiles(global_profiles)
            await ctx.send(f"✅ Color for profile '{name}' updated successfully!")
            return

        # Handle all other fields as plain text
        await ctx.send(f"💬 Please enter the new value for **{field}**.")
        value_msg = await bot.wait_for("message", timeout=120, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        profile[field] = value_msg.content.strip()

        # Save the updated profile to the global profiles file
        save_profiles(global_profiles)
        await ctx.send(f"✅ Profile '{name}' updated successfully!")

    except TimeoutError:
        await ctx.send("❌ You took too long to respond. Please try the command again.")



# Set a proxy avatar for an alter
@bot.command(name="proxyavatar")
async def proxyavatar(ctx, name: str):
    user_id = str(ctx.author.id)
    user_profiles = global_profiles.get(user_id, {}).get("alters", {})

    if name not in user_profiles:
        await ctx.send(f"❌ Alter **{name}** does not exist.")
        return

    profile = user_profiles[name]

    # Ask for the new proxy avatar URL or attachment
    await ctx.send("📂 Please send the new **proxy avatar** as an **attachment** or a **direct image URL**.")

    try:
        image_msg = await bot.wait_for("message", timeout=120, check=lambda m: m.author == ctx.author and m.channel == ctx.channel)

        # Check if the message has an attachment
        if image_msg.attachments:
            image_url = image_msg.attachments[0].url
        elif image_msg.content.startswith("http"):
            image_url = image_msg.content.strip()
        else:
            await ctx.send("❌ Invalid proxy avatar input. Please provide a direct image URL or attachment.")
            return

        # Save the proxy avatar
        profile["proxy_avatar"] = image_url
        save_profiles(global_profiles)
        await ctx.send(f"✅ Proxy avatar for **{name}** updated successfully!")

    except TimeoutError:
        await ctx.send("❌ You took too long to respond. Please try the command again.")






@bot.command(name="show")
async def show(ctx, name: str):
            user_id = str(ctx.author.id)
            user_profiles = global_profiles.get(user_id, {}).get("alters", {})

            if name not in user_profiles:
                await ctx.send(f"❌ Profile '{name}' does not exist.")
                return

            profile = user_profiles[name]
            displayname = profile.get("displayname", name)
            aliases = profile.get("aliases", [])
            alias_list = ", ".join(aliases) if aliases else "None"
            avatar_url = profile.get("avatar", None)
            proxy_avatar_url = profile.get("proxy_avatar", None)
            banner_url = profile.get("banner", None)
            embed_color = profile.get("color", 0x8A2BE2)  # Default to purple if no color is set
            use_embed = profile.get("use_embed", True)  # Default to True if not set

            # Properly handle empty or missing descriptions
            description = profile.get("description", "No description provided") or "No description provided"

            # Properly format Markdown, including links
            description = discord.utils.escape_markdown(description)  # Escape special characters
            description = re.sub(r"\\\*", "*", description)  # Allow bold and italics
            description = re.sub(r"\\_", "_", description)  # Allow underscores
            description = re.sub(r"\\~", "~", description)  # Allow strikethrough
            description = re.sub(r"\\`", "`", description)  # Allow code blocks
            description = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"[\1](\2)", description)  # Allow links

            # Use an embed if the profile has embeds enabled
            if use_embed:
                embed = discord.Embed(
                    title=f"🗂️  {displayname}",
                    color=embed_color
                )
                embed.add_field(name=" Display Name", value=displayname, inline=False)
                embed.add_field(name="👤 Alter Name", value=name, inline=False)
                embed.add_field(name=" Pronouns", value=profile.get("pronouns", "Not set"), inline=False)
                embed.add_field(name=" Proxy", value=profile.get("proxy", "Not set"), inline=False)
                embed.add_field(name=" Aliases", value=alias_list, inline=False)

                # Add the description as a separate field
                embed.add_field(name="📝 Description", value=description, inline=False)

                # Set the avatar as a thumbnail if it exists
                if avatar_url:
                    embed.set_thumbnail(url=avatar_url)

                # Set the banner as the main image if it exists
                if banner_url:
                    embed.set_image(url=banner_url)

                # Set the proxy avatar as the footer icon if it exists
                if proxy_avatar_url:
                    embed.set_footer(text=f"Proxy Avatar for {displayname}", icon_url=proxy_avatar_url)
                else:
                    embed.set_footer(text=f"User ID: {user_id}")

                await ctx.send(embed=embed)

            # Fallback to plain text if the profile doesn't use embeds
            else:
                message = (
                    f"**🗂️ Profile:** {displayname}\n"
                    f"👤 **Alter Name:** {name}\n"
                    f" **Pronouns:** {profile.get('pronouns', 'Not set')}\n"
                    f" **Proxy:** {profile.get('proxy', 'Not set')}\n"
                    f" **Aliases:** {alias_list}\n"
                    f"📝 **Description:** {description}\n"
                )
                await ctx.send(message)


import discord
from discord.ui import View, Button

class ProfilePaginator(View):
    def __init__(self, user_id, system_name, pages):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.system_name = system_name
        self.pages = pages
        self.current_page = 0
        self.total_pages = len(pages)

        # Disable buttons if there is only one page
        if self.total_pages == 1:
            self.disable_buttons()

    def disable_buttons(self):
        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True

    async def update_message(self, interaction):
        embed = discord.Embed(
            title=f"🗂️ Profiles for {self.system_name} (Page {self.current_page + 1}/{self.total_pages})",
            description="\n".join(self.pages[self.current_page]),
            color=0x8A2BE2  # Default to purple
        )
        embed.set_footer(text=f"User ID: {self.user_id}")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction, button):
        self.current_page -= 1
        if self.current_page < 0:
            self.current_page = self.total_pages - 1  # Wrap around to the last page
        await self.update_message(interaction)

    @discord.ui.button(label="➡️ Next", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction, button):
        self.current_page += 1
        if self.current_page >= self.total_pages:
            self.current_page = 0  # Wrap around to the first page
        await self.update_message(interaction)


@bot.command(name="list_profiles")
async def list_profiles(ctx):
    user_id = str(ctx.author.id)
    user_data = global_profiles.get(user_id, {})
    user_profiles = user_data.get("alters", {})

    # Check if the user has a system name set, fall back to the Discord username if not
    system_info = user_data.get("system", {})
    system_name = system_info.get("name") or ctx.author.display_name

    # Check if the user has any profiles
    if not user_profiles:
        await ctx.send("You don't have any profiles set up yet. Use `!create` to add a profile.")
        return

    # Prepare the profile list, sorted alphabetically by profile name
    profile_entries = sorted(
        [f"• **{name}** — `{profile.get('proxy', 'No proxy set')}`" for name, profile in user_profiles.items()],
        key=lambda x: x.split("**")[1].lower()  # Sort by the profile name
    )

    # Split the profiles into pages
    chunk_size = 15  # Number of profiles per page
    pages = [profile_entries[i:i + chunk_size] for i in range(0, len(profile_entries), chunk_size)]

    # Create the first embed
    embed = discord.Embed(
        title=f"🗂️ Profiles for {system_name} (Page 1/{len(pages)})",
        description="\n".join(pages[0]),
        color=0x8A2BE2  # Default to purple
    )
    embed.set_footer(text=f"User ID: {user_id}")

    # Send the initial message with the paginator view
    message = await ctx.send(embed=embed, view=ProfilePaginator(user_id, system_name, pages))


# Delete a profile
@bot.command()
async def delete(ctx, name: str):
    if name not in profiles:
        await ctx.send(f"Profile '{name}' does not exist.")
        return
    del profiles[name]
    save_profiles()
    backup_profiles()
    await ctx.send(f"Profile '{name}' has been deleted successfully.")

# Add an alias to a profile
@bot.command()
async def alias(ctx, name: str, *, alias: str):
    if name not in profiles:
        await ctx.send(f"Profile '{name}' does not exist.")
        return
    profiles[name].setdefault("aliases", []).append(alias)
    save_profiles()
    backup_profiles()
    await ctx.send(f"Alias '{alias}' added to profile '{name}' successfully!")

# Remove an alias from a profile
@bot.command()
async def remove_alias(ctx, name: str, *, alias: str):
    if name not in profiles:
        await ctx.send(f"Profile '{name}' does not exist.")
        return
    if alias not in profiles[name].get("aliases", []):
        await ctx.send(f"Alias '{alias}' does not exist for profile '{name}'.")
        return
    profiles[name]["aliases"].remove(alias)
    save_profiles()
    backup_profiles()
    await ctx.send(f"Alias '{alias}' removed from profile '{name}' successfully!")

# Backup all profiles manually
@bot.command()
async def backup(ctx):
    backup_profiles()
    await ctx.send("Profiles have been backed up successfully!")




import discord
import re

# Show system info for the current user with full Markdown support, including links
@bot.command(name="system")
async def system(ctx):
    user_id = str(ctx.author.id)
    user_data = global_profiles.get(user_id, {})
    system_info = user_data.get("system", {})

    # Check if the system exists
    if not system_info:
        await ctx.send("❌ You don't have a system set up yet. Use `!create_system` to create one.")
        return

    # Extract system info
    system_name = system_info.get("name", "Unnamed System")
    system_pronouns = system_info.get("pronouns", "Not set")
    system_description = system_info.get("description", "No description provided.")
    system_avatar = system_info.get("avatar", None)
    system_banner = system_info.get("banner", None)
    system_color = system_info.get("color", 0x8A2BE2)  # Default to purple

    # Preserve Markdown links without escaping them
    def preserve_links(text):
        # Preserve links in [text](link) format
        return re.sub(
            r"(?<!\\)\[([^\]]+)\]\((https?://[^\s)]+)\)",
            r"[\1](\2)",
            text
        )

    # Process the description for markdown and links
    system_description = preserve_links(system_description)

    # Create the system info embed
    embed = discord.Embed(
        title=system_name,
        description=(
            f"**System Name:** {system_name}\n"
            f"**Pronouns:** {system_pronouns}\n"
            f"**Description:** {system_description}\n\n"
            f"||Linked Discord Account: {ctx.author.mention}||"
        ),
        color=system_color
    )

    # Set system avatar as thumbnail if it exists
    if system_avatar:
        embed.set_thumbnail(url=system_avatar)

    # Set system banner as main image if it exists
    if system_banner:
        embed.set_image(url=system_banner)

    # Set a footer with the user ID for reference
    embed.set_footer(text=f"User ID: {user_id}")

    await ctx.send(embed=embed)




# Wipe all alters from the current system
@bot.command(name="wipe_alters")
async def wipe_alters(ctx):
    user_id = str(ctx.author.id)

    # Check if the user has any profiles
    user_data = global_profiles.get(user_id, {})
    if not user_data.get("alters"):
        await ctx.send("You don't have any alters to wipe.")
        return

    # Confirm the wipe
    await ctx.send("⚠️ **Are you sure you want to wipe all alters from your system?**\nThis action **cannot** be undone. Type `CONFIRM` to proceed.")

    try:
        confirmation = await bot.wait_for(
            "message",
            timeout=60,
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel
        )

        if confirmation.content.strip().upper() == "CONFIRM":
            # Clear the alters
            global_profiles[user_id]["alters"] = {}
            save_profiles(global_profiles)
            await ctx.send("✅ All alters have been wiped from your system.")
        else:
            await ctx.send("❌ Wipe canceled. Your alters are safe.")

    except TimeoutError:
        await ctx.send("❌ Wipe canceled. You took too long to confirm.")





    import discord
    from discord.ext import commands
    import json

# Ensure the "folders" key exists for each system
def ensure_folders_exist(user_id):
    if user_id not in global_profiles:
        global_profiles[user_id] = {"system": {}, "alters": {}, "folders": {}}
    elif "folders" not in global_profiles[user_id]:
        global_profiles[user_id]["folders"] = {}




# Create a new folder
@bot.command(name="create_folder")
async def create_folder(ctx):
        user_id = str(ctx.author.id)
        ensure_folders_exist(user_id)

        # Ask for the folder name
        await ctx.send("📁 What would you like to name this folder?")
        try:
            folder_name_msg = await bot.wait_for(
                "message",
                timeout=120,
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
            folder_name = folder_name_msg.content.strip()

            # Check if the folder already exists
            folders = global_profiles[user_id]["folders"]
            if folder_name in folders:
                await ctx.send(f"⚠️ Folder **{folder_name}** already exists. Use **!edit_folder** to modify it.")
                return

            # Create the new folder
            folders[folder_name] = {
                "name": folder_name,
                "color": 0x8A2BE2,  # Default to purple
                "banner": None,
                "icon": None,
                "alters": []
            }

            save_profiles(global_profiles)
            await ctx.send(f"✅ Folder **{folder_name}** created successfully!")

        except TimeoutError:
            await ctx.send("❌ You took too long to respond. Please try the command again.")

# Edit an existing folder
@bot.command(name="edit_folder")
async def edit_folder(ctx, folder_name: str):
        user_id = str(ctx.author.id)
        ensure_folders_exist(user_id)

        # Check if the folder exists
        folders = global_profiles[user_id]["folders"]
        if folder_name not in folders:
            await ctx.send(f"❌ Folder **{folder_name}** does not exist. Use **!create_folder** to create it first.")
            return

        folder = folders[folder_name]

        try:
            # Ask if they want to rename the folder
            await ctx.send(f"📝 Would you like to **rename** the folder **{folder_name}**? (yes/no)")
            rename_msg = await bot.wait_for(
                "message",
                timeout=120,
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
            if rename_msg.content.strip().lower() == "yes":
                await ctx.send("📁 What should the new **name** of this folder be?")
                new_name_msg = await bot.wait_for(
                    "message",
                    timeout=120,
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel
                )
                new_name = new_name_msg.content.strip()
                if new_name != folder_name and new_name not in folders:
                    folders[new_name] = folder
                    del folders[folder_name]
                    folder["name"] = new_name
                    folder_name = new_name
                    await ctx.send(f"✅ Folder renamed to **{new_name}**.")

            # Ask for the new color
            await ctx.send("🎨 Please enter a **hex color code** for this folder (e.g., #8A2BE2), or type skip to keep the current color.")
            color_msg = await bot.wait_for(
                "message",
                timeout=120,
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
            color_code = color_msg.content.strip()

            # Validate the hex color code
            if color_code.lower() != "skip":
                if not color_code.startswith("#") or len(color_code) != 7:
                    await ctx.send("❌ Invalid color code. Using the previous color.")
                else:
                    try:
                        folder["color"] = int(color_code.lstrip("#"), 16)
                        await ctx.send(f"🎨 Color updated to **{color_code}**.")
                    except ValueError:
                        await ctx.send("❌ Invalid color code. Using the previous color.")

            # Ask for the banner image
            await ctx.send("🖼️ Please upload a **banner** image or provide a **direct image URL** (or type skip to keep the current banner).")
            banner_msg = await bot.wait_for(
                "message",
                timeout=120,
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
            if banner_msg.content.strip().lower() != "skip":
                if banner_msg.attachments:
                    folder["banner"] = banner_msg.attachments[0].url
                    await ctx.send("🖼️ Banner updated successfully.")
                elif banner_msg.content.startswith("http"):
                    folder["banner"] = banner_msg.content.strip()
                    await ctx.send("🖼️ Banner updated successfully.")
                else:
                    await ctx.send("❌ Invalid banner input. Keeping the previous banner.")

            # Ask for the icon image
            await ctx.send("📌 Please upload an **icon** image or provide a **direct image URL** (or type skip to keep the current icon).")
            icon_msg = await bot.wait_for(
                "message",
                timeout=120,
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
            if icon_msg.content.strip().lower() != "skip":
                if icon_msg.attachments:
                    folder["icon"] = icon_msg.attachments[0].url
                    await ctx.send("📌 Icon updated successfully.")
                elif icon_msg.content.startswith("http"):
                    folder["icon"] = icon_msg.content.strip()
                    await ctx.send("📌 Icon updated successfully.")
                else:
                    await ctx.send("❌ Invalid icon input. Keeping the previous icon.")

            # Save the updated folder
            save_profiles(global_profiles)
            await ctx.send(f"✅ Folder **{folder_name}** updated successfully!")

        except TimeoutError:
            await ctx.send("❌ You took too long to respond. Please try the command again.")


# Show the contents of a folder with vertical alter listing
@bot.command(name="show_folder")
async def show_folder(ctx, folder_name: str):
            user_id = str(ctx.author.id)
            ensure_folders_exist(user_id)

            folders = global_profiles[user_id]["folders"]
            if folder_name not in folders:
                await ctx.send(f"❌ Folder **{folder_name}** does not exist.")
                return

            folder = folders[folder_name]
            alters = folder["alters"]

            # Create the folder embed
            embed = discord.Embed(
                title=f"📁 Folder: {folder_name}",
                color=folder["color"],
                description="No alters in this folder." if not alters else ""
            )

            # List alters vertically if any exist
            if alters:
                alter_list = "\n".join([f"- **{alter}**" for alter in alters])
                embed.add_field(name="👥 Alters", value=alter_list, inline=False)

            # Set the icon as a thumbnail if it exists
            if folder["icon"]:
                embed.set_thumbnail(url=folder["icon"])

            # Set the banner as the main image if it exists
            if folder["banner"]:
                embed.set_image(url=folder["banner"])

            # Set a footer with the folder name for reference
            embed.set_footer(text=f"Folder: {folder_name}")

            await ctx.send(embed=embed)


# Add single or multiple alters to a folder
@bot.command(name="add_alters")
async def add_alters(ctx, folder_name: str, *, alters: str):
        user_id = str(ctx.author.id)
        ensure_folders_exist(user_id)

        # Check if the folder exists
        folders = global_profiles[user_id]["folders"]
        if folder_name not in folders:
            await ctx.send(f"❌ Folder **{folder_name}** does not exist. Use **!create_folder** to create it first.")
            return

        folder = folders[folder_name]
        alter_names = [name.strip() for name in alters.split(",")]

        added_alters = []
        skipped_alters = []

        # Add each alter to the folder
        for alter_name in alter_names:
            if alter_name in global_profiles[user_id]["alters"]:
                if alter_name not in folder["alters"]:
                    folder["alters"].append(alter_name)
                    added_alters.append(alter_name)
                else:
                    skipped_alters.append(alter_name)
            else:
                skipped_alters.append(alter_name)

        # Save the updated folders
        save_profiles(global_profiles)

        # Send a confirmation message
        added_msg = f"✅ Added: {', '.join(added_alters)}" if added_alters else "No alters were added."
        skipped_msg = f"⚠️ Skipped: {', '.join(skipped_alters)}" if skipped_alters else ""
        await ctx.send(f"🗂️ Folder **{folder_name}** updated.\n{added_msg}\n{skipped_msg}")

# Remove single or multiple alters from a folder
@bot.command(name="remove_alters")
async def remove_alters(ctx, folder_name: str, *, alters: str):
        user_id = str(ctx.author.id)
        ensure_folders_exist(user_id)

        # Check if the folder exists
        folders = global_profiles[user_id]["folders"]
        if folder_name not in folders:
            await ctx.send(f"❌ Folder **{folder_name}** does not exist.")
            return

        folder = folders[folder_name]
        alter_names = [name.strip() for name in alters.split(",")]

        removed_alters = []
        skipped_alters = []

        # Remove each alter from the folder
        for alter_name in alter_names:
            if alter_name in folder["alters"]:
                folder["alters"].remove(alter_name)
                removed_alters.append(alter_name)
            else:
                skipped_alters.append(alter_name)

        # Save the updated folders
        save_profiles(global_profiles)

        # Send a confirmation message
        removed_msg = f"🗑️ Removed: {', '.join(removed_alters)}" if removed_alters else "No alters were removed."
        skipped_msg = f"⚠️ Not in folder: {', '.join(skipped_alters)}" if skipped_alters else ""
        await ctx.send(f"🗂️ Folder **{folder_name}** updated.\n{removed_msg}\n{skipped_msg}")

# Delete a folder
@bot.command(name="delete_folder")
async def delete_folder(ctx, folder_name: str):
        user_id = str(ctx.author.id)
        ensure_folders_exist(user_id)

        folders = global_profiles[user_id]["folders"]
        if folder_name in folders:
            del folders[folder_name]
            save_profiles(global_profiles)
            await ctx.send(f"🗑️ Folder **{folder_name}** has been deleted successfully.")
        else:
            await ctx.send(f"❌ Folder **{folder_name}** does not exist.")

# Wipe all alters from a folder
@bot.command(name="wipe_folder_alters")
async def wipe_folder_alters(ctx, folder_name: str):
    user_id = str(ctx.author.id)
    ensure_folders_exist(user_id)

    folders = global_profiles[user_id]["folders"]
    if folder_name in folders:
        folders[folder_name]["alters"] = []
        save_profiles(global_profiles)
        await ctx.send(f"🗑️ All alters have been removed from the folder **{folder_name}**.")
    else:
        await ctx.send(f"❌ Folder **{folder_name}** does not exist.")

# Save the profile data
def save_profiles(profiles):
    with open("profiles.json", "w") as f:
        json.dump(profiles, f, indent=4)










# Pixel command to check bot latency (Admin-Only)
@bot.command(name="pixel")
@commands.has_permissions(administrator=True)
async def pixel(ctx):
    latency = round(bot.latency * 1000)  # Convert to milliseconds
    embed = discord.Embed(
        title="🌌 PixelBot Status",
        description=f"**Current Latency:** `{latency} ms`",
        color=0x8A2BE2  # Default to purple
    )
    await ctx.send(embed=embed)

# Handle missing permissions
@pixel.error
async def pixel_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You need to be a **server admin** to use this command.")





# Blacklist a category (Admin-Only)
@bot.command(name="blacklist_category")
@commands.has_permissions(administrator=True)
async def blacklist_category(ctx, category: discord.CategoryChannel):
    guild_id = str(ctx.guild.id)

    # Create the guild section if it doesn't exist
    if guild_id not in category_blacklist:
        category_blacklist[guild_id] = []

    # Add the category to the blacklist
    if category.id not in category_blacklist[guild_id]:
        category_blacklist[guild_id].append(category.id)
        save_category_blacklist(category_blacklist)
        await ctx.send(f"🚫 Category **{category.name}** has been blacklisted successfully.")
    else:
        await ctx.send(f"🚫 Category **{category.name}** is already blacklisted.")

# Unblacklist a category (Admin-Only)
@bot.command(name="unblacklist_category")
@commands.has_permissions(administrator=True)
async def unblacklist_category(ctx, category: discord.CategoryChannel):
    guild_id = str(ctx.guild.id)

    # Check if the category is blacklisted
    if guild_id in category_blacklist and category.id in category_blacklist[guild_id]:
        category_blacklist[guild_id].remove(category.id)
        save_category_blacklist(category_blacklist)
        await ctx.send(f"✅ Category **{category.name}** has been removed from the blacklist.")
    else:
        await ctx.send(f"⚠️ Category **{category.name}** is not blacklisted.")

# Handle missing permissions
@blacklist_category.error
@unblacklist_category.error
async def category_blacklist_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You need to be a **server admin** to use this command.")






# Blacklist a channel (Admin-Only)
@bot.command(name="blacklist_channel")
@commands.has_permissions(administrator=True)
async def blacklist_channel(ctx, channel: discord.TextChannel):
    guild_id = str(ctx.guild.id)

    # Create the guild section if it doesn't exist
    if guild_id not in channel_blacklist:
        channel_blacklist[guild_id] = []

    # Add the channel to the blacklist
    if channel.id not in channel_blacklist[guild_id]:
        channel_blacklist[guild_id].append(channel.id)
        save_blacklist(channel_blacklist)
        await ctx.send(f"🚫 Channel **{channel.mention}** has been blacklisted successfully.")
    else:
        await ctx.send(f"🚫 Channel **{channel.mention}** is already blacklisted.")

# Unblacklist a channel (Admin-Only)
@bot.command(name="unblacklist_channel")
@commands.has_permissions(administrator=True)
async def unblacklist_channel(ctx, channel: discord.TextChannel):
    guild_id = str(ctx.guild.id)

    # Check if the channel is blacklisted
    if guild_id in channel_blacklist and channel.id in channel_blacklist[guild_id]:
        channel_blacklist[guild_id].remove(channel.id)
        save_blacklist(channel_blacklist)
        await ctx.send(f"✅ Channel **{channel.mention}** has been removed from the blacklist.")
    else:
        await ctx.send(f"⚠️ Channel **{channel.mention}** is not blacklisted.")

# Handle missing permissions
@blacklist_channel.error
@unblacklist_channel.error
async def blacklist_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You need to be a **server admin** to use this command.")





import discord
import aiofiles
import json

# Export the entire system and alters to a JSON file
@bot.command(name="export_system")
async def export_system(ctx):
    user_id = str(ctx.author.id)

    # Check if the user has a system
    if user_id not in global_profiles or not global_profiles[user_id]:
        await ctx.send("❌ You don't have a system set up yet.")
        return

    # Prepare the export data
    user_data = global_profiles[user_id]
    export_filename = f"{user_id}_system_backup.json"

    try:
        # Save the system data to a JSON file
        async with aiofiles.open(export_filename, "w") as f:
            await f.write(json.dumps(user_data, indent=4))

        # Send the JSON file to the user via DM
        dm_channel = await ctx.author.create_dm()
        await dm_channel.send(
            "📂 Here is your **Pixel** system export file. You can use this to **re-import** your system anytime:",
            file=discord.File(export_filename)
        )

        # Confirm in the server
        await ctx.send("✅ Your system has been exported and sent to your DMs.")

    except Exception as e:
        print(f"⚠️ Error exporting system for {ctx.author}: {e}")
        await ctx.send("❌ An error occurred while exporting your system. Please try again.")

import discord
import aiohttp
import aiofiles
import json

# Import a PixelBot system from a JSON file
@bot.command(name="import_system")
async def import_system(ctx):
    user_id = str(ctx.author.id)

    # Ask the user to upload their backup file
    await ctx.send("📂 Please upload your **PixelBot** system backup JSON file.")

    try:
        # Wait for the user to upload the file
        message = await bot.wait_for(
            "message",
            timeout=300,
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel and m.attachments
        )

        # Get the attached file
        file_url = message.attachments[0].url

        # Download the file
        async with message.channel.typing():
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Overwrite the user's system and alters
                        global_profiles[user_id] = data
                        save_profiles(global_profiles)

                        await ctx.send("✅ Your system has been successfully imported.")
                    else:
                        await ctx.send("❌ Failed to download the file. Please try again.")

    except TimeoutError:
        await ctx.send("❌ You took too long to upload the file. Please try again.")

    except Exception as e:
        print(f"⚠️ Error importing system for {ctx.author}: {e}")
        await ctx.send("❌ An error occurred while importing your system. Please try again.")







import os
import discord
from discord.ext import commands
import aiohttp
import json

# Import PluralKit JSON file with proxy avatar and color support
@bot.command(name="import_pluralkit")
async def import_pluralkit(ctx):
            user_id = str(ctx.author.id)

            # Ask the user to upload their PluralKit JSON file
            await ctx.send("📂 Please upload your **PluralKit** JSON export file.")

            try:
                # Wait for the user to upload the file
                message = await bot.wait_for(
                    "message",
                    timeout=300,
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel and m.attachments
                )

                # Get the attached file
                file_url = message.attachments[0].url

                # Download the file
                async with message.channel.typing():
                    async with aiohttp.ClientSession() as session:
                        async with session.get(file_url) as response:
                            if response.status == 200:
                                data = await response.json()

                                # Create the user system if it doesn't exist
                                if user_id not in global_profiles:
                                    global_profiles[user_id] = {"system": {}, "alters": {}}

                                # Ensure the "alters" key exists
                                if "alters" not in global_profiles[user_id]:
                                    global_profiles[user_id]["alters"] = {}

                                # Import each member as a profile
                                for member in data.get("members", []):
                                    name = member.get("name", "Unnamed Alter")
                                    display_name = member.get("display_name", name)
                                    pronouns = member.get("pronouns", "Not set")
                                    description = member.get("description", "No description provided.")
                                    avatar = member.get("avatar_url", None)
                                    proxy_avatar = member.get("proxy_avatar_url", avatar)  # Use main avatar if no proxy avatar is set
                                    banner = member.get("banner", None)
                                    color = member.get("color", "#8A2BE2")  # Default to purple if no color is set
                                    proxy_tags = member.get("proxy_tags", [])

                                    # Convert the color from hex to integer
                                    try:
                                        # Use a default color if the color is None or empty
                                        if not color or color.strip() == "":
                                            color_int = 0x8A2BE2  # Default to purple
                                        else:
                                            color_int = int(color.lstrip("#"), 16)
                                    except (ValueError, AttributeError):
                                        color_int = 0x8A2BE2  # Default to purple if conversion fails



                                    # Combine all prefix-suffix pairs into a single proxy format
                                    proxies = []
                                    for tag in proxy_tags:
                                        prefix = tag.get("prefix", "") or ""
                                        suffix = tag.get("suffix", "") or ""

                                        # Format the proxy correctly
                                        if prefix and suffix:
                                            proxies.append(f"{prefix}...{suffix}")
                                        elif prefix:
                                            proxies.append(prefix)
                                        elif suffix:
                                            proxies.append(suffix)

                                    # Use the first proxy as the main one, if any exist
                                    main_proxy = proxies[0] if proxies else "No proxy set"

                                    # Create the alter profile
                                    global_profiles[user_id]["alters"][name] = {
                                        "displayname": display_name,
                                        "pronouns": pronouns,
                                        "description": description,
                                        "avatar": avatar,
                                        "proxy_avatar": proxy_avatar,
                                        "banner": banner,
                                        "proxy": main_proxy,
                                        "aliases": [name],  # Add the original name as an alias
                                        "color": color_int,
                                        "use_embed": True
                                    }

                                # Save the imported profiles
                                save_profiles(global_profiles)
                                await ctx.send("✅ Your PluralKit profiles have been imported successfully!")
                            else:
                                await ctx.send("❌ Failed to download the file. Please try again.")

            except TimeoutError:
                await ctx.send("❌ You took too long to upload the file. Please try again.")

            except Exception as e:
                print(f"⚠️ Error importing PluralKit system for {ctx.author}: {e}")
                await ctx.send("❌ An error occurred while importing your system. Please try again.")







@bot.command(name="pixelhelp")
async def pixelhelp(ctx):
    embed = discord.Embed(
        title="📂 PixelBot Command List",
        description="Here are all the available commands for managing systems, alters, folders, and more:",
        color=0x8A2BE2
    )

    # System Management
    embed.add_field(
        name="🗃️ **System Management**",
        value=(
            "`!create_system <name>` - Create a new system.\n"
            "`!edit_system` - Edit the current system (name, avatar, banner, description, pronouns, color).\n"
            "`!delete_system` - Delete the current system.\n"
            "`!system` - Show the current system’s info, including avatars, banners, and colors.\n"
            "`!export_system` - Export your entire system to a JSON file (sent to DMs).\n"
            "`!import_system` - Import a previously exported system from a JSON file."
        ),
        inline=False
    )

    # Profile and Alter Management
    embed.add_field(
        name="👥 **Profile and Alter Management**",
        value=(
            "`!create <name> <pronouns> <description>` - Create a new profile with optional embed support.\n"
            "`!edit <name>` - Edit an existing profile (name, displayname, pronouns, description, avatar, banner, proxy, color, proxy avatar).\n"
            "`!show <name>` - Show a profile, including avatars, banners, and colors.\n"
            "`!list_profiles` - List all profiles in the current system.\n"
            "`!delete <name>` - Delete a profile.\n"
            "`!alias <name> <alias>` - Add an alias to a profile.\n"
            "`!remove_alias <name> <alias>` - Remove an alias from a profile."
        ),
        inline=False
    )

    # Folder Management
    embed.add_field(
        name="📁 **Folder Management**",
        value=(
            "`!create_folder` - Create a new folder with a name, color, banner, icon, and alters.\n"
            "`!edit_folder <folder name>` - Edit an existing folder.\n"
            "`!delete_folder <folder name>` - Delete a folder.\n"
            "`!wipe_folder_alters <folder name>` - Remove all alters from a folder.\n"
            "`!show_folder <folder name>` - Show the contents of a folder.\n"
            "`!add_alters <folder name> <alter1, alter2>` - Add one or more alters to a folder.\n"
            "`!remove_alters <folder name> <alter1, alter2>` - Remove one or more alters from a folder."
        ),
        inline=False
    )

    # Proxy Management
    embed.add_field(
        name="🗣️ **Proxy Management**",
        value=(
            "`!proxyavatar <name>` - Set a separate avatar for proxying.\n"
            "`!proxy` - Send a proxied message.\n"
            "`!set_proxy <name> <proxy>` - Set a proxy for an alter."
        ),
        inline=False
    )

    # Import and Export
    embed.add_field(
        name="📂 **Import and Export**",
        value=(
            "`!export_system` - Export your entire system to a JSON file (sent to DMs).\n"
            "`!import_system` - Import a previously exported system from a JSON file.\n"
            "`!import_pluralkit` - Import your PluralKit profiles, including proxy avatars and colors."
        ),
        inline=False
    )


    # Admin Commands
    embed.add_field(
        name="🔧 **Admin Commands**",
        value=(
            "`!blacklist_channel <channel>` - Blacklist a channel from proxy detection (admin only).\n"
            "`!blacklist_category <category>` - Blacklist an entire category from proxy detection (admin only).\n"
            "`!list_blacklists` - List all blacklisted channels and categories (admin only).\n"
            "`!admin_commands` - Display all admin commands (admin only)."
        ),
        inline=False
    )

    # Utility Commands
    embed.add_field(
        name="🛠️ **Utility Commands**",
        value=(
            "`!pixel` - Check the bot’s current speed and latency (admin only).\n"
            "`!pixelhelp` - Show the full command list."
        ),
        inline=False
    )

    embed.set_footer(text="PixelBot - The Ultimate Proxy and System Management Bot")

    await ctx.send(embed=embed)



# Admin Commands List
@bot.command(name="admincommands")
@commands.has_permissions(administrator=True)
async def admincommands(ctx):
    embed = discord.Embed(
        title="🔧 Admin Commands",
        description="A list of all available admin-only commands:",
        color=0x8A2BE2  # Default to purple
    )

    # Add all admin commands here
    embed.add_field(
        name="🌌 **Pixel**",
        value="`!pixel` - Check the bot's current latency.",
        inline=False
    )

    embed.add_field(
        name="🛠️ **Admin Commands**",
        value="`!admincommands` - Show a list of all admin commands.",
        inline=False
    )

    embed.add_field(
        name="🚫 **Channel Blacklist**",
        value=(
            "`!blacklist_channel <channel>` - Prevent the bot from reading or sending messages in a channel.\n"
            "`!unblacklist_channel <channel>` - Remove a channel from the bot's blacklist.\n"
            "`!blacklist_category <category>` - Prevent the bot from reading or sending messages in a whole category.\n"
            "`!unblacklist_category <category>` - Remove a category from the bot's blacklist."
        ),
        inline=False
    )

    # Set a footer for consistency
    embed.set_footer(text="Admin commands - Only for server admins")

    await ctx.send(embed=embed)

# Handle missing permissions
@admincommands.error
async def admincommands_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🚫 You need to be a **server admin** to use this command.")




# Display the total number of systems and guilds
@bot.command(name="bot_stats")
async def bot_stats(ctx):
    # Count the total number of systems
    total_systems = len(global_profiles)

    # Count the total number of guilds the bot has ever been in
    total_guilds = len({guild.id for guild in bot.guilds})

    # Create the embed
    embed = discord.Embed(
        title="📊 Bot Statistics",
        description="Current stats for the bot:",
        color=0x8A2BE2  # Default to purple
    )
    embed.add_field(name="🔄 Total Systems", value=f"{total_systems}", inline=True)
    embed.add_field(name="🏠 Total Guilds", value=f"{total_guilds}", inline=True)
    embed.set_footer(text="PixelBot - Bringing your system to life 🌌")

    # Send the embed
    await ctx.send(embed=embed)






PROFILES_FILE = "global_profiles.json"

# Ensure the global profiles file exists
if not os.path.exists(PROFILES_FILE):
    with open(PROFILES_FILE, "w") as f:
        json.dump({}, f)

# Load profiles from file
def load_profiles():
    with open(PROFILES_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

# Save profiles to file
def save_profiles(profiles):
    with open(PROFILES_FILE, "w") as f:
        json.dump(profiles, f, indent=4)

global_profiles = load_profiles()

CATEGORY_BLACKLIST_FILE = "category_blacklist.json"

# Ensure the category blacklist file exists
if not os.path.exists(CATEGORY_BLACKLIST_FILE):
    with open(CATEGORY_BLACKLIST_FILE, "w") as f:
        json.dump({}, f)

# Load the category blacklist from file
def load_category_blacklist():
    with open(CATEGORY_BLACKLIST_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

# Save the category blacklist to file
def save_category_blacklist(blacklist):
    with open(CATEGORY_BLACKLIST_FILE, "w") as f:
        json.dump(blacklist, f, indent=4)

category_blacklist = load_category_blacklist()

BLACKLIST_FILE = "channel_blacklist.json"

# Ensure the blacklist file exists
if not os.path.exists(BLACKLIST_FILE):
    with open(BLACKLIST_FILE, "w") as f:
        json.dump({}, f)

# Load the blacklist from file
def load_blacklist():
    with open(BLACKLIST_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

# Save the blacklist to file
def save_blacklist(blacklist):
    with open(BLACKLIST_FILE, "w") as f:
        json.dump(blacklist, f, indent=4)

channel_blacklist = load_blacklist()


# Backup profiles to a separate file for safety
def backup_profiles():
    with open(BACKUP_FILE, "w") as f:
        json.dump(profiles, f, indent=4)









import discord
from discord.ext import commands
from discord.ui import View, Button
import json

suggestion_channels = {}

# Load the suggestion channels from a file
def load_suggestion_channels():
    global suggestion_channels
    try:
        with open("suggestion_channels.json", "r") as f:
            suggestion_channels = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        suggestion_channels = {}

# Save the suggestion channels to a file
def save_suggestion_channels():
    with open("suggestion_channels.json", "w") as f:
        json.dump(suggestion_channels, f, indent=4)

load_suggestion_channels()

# Set the suggestion channel (admin only)
@bot.command(name="set_suggestion_channel")
@commands.has_permissions(administrator=True)
async def set_suggestion_channel(ctx, channel: discord.TextChannel):
    guild_id = str(ctx.guild.id)

    # Save the suggestion channel
    suggestion_channels[guild_id] = channel.id
    save_suggestion_channels()

    await ctx.send(f"✅ Suggestions will now be sent to {channel.mention}.")

# Submit a fully anonymous suggestion with accept/reject buttons
@bot.command(name="suggest")
async def suggest(ctx):
    guild_id = str(ctx.guild.id)

    # Check if a suggestion channel is set
    if guild_id not in suggestion_channels:
        await ctx.send("❌ The suggestion channel has not been set up yet. Please ask an admin to set it with `!set_suggestion_channel`.")
        return

    # Delete the command message for full anonymity
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        print(f"⚠️ Missing permissions to delete message in {ctx.channel.name}")

    # Send a DM to the user to collect their suggestion
    try:
        dm_channel = await ctx.author.create_dm()
        await dm_channel.send("💡 Please type your suggestion. You have **2 minutes** to respond.")

        # Wait for the user's response
        message = await bot.wait_for(
            "message",
            timeout=120,
            check=lambda m: m.author == ctx.author and isinstance(m.channel, discord.DMChannel)
        )

        # Get the suggestion channel
        suggestion_channel = bot.get_channel(suggestion_channels[guild_id])

        # Create the suggestion embed
        embed = discord.Embed(
            title="📝 New Anonymous Suggestion",
            description=message.content.strip(),
            color=0x8A2BE2
        )
        embed.set_footer(text="Sent anonymously")

        # Create the view with Accept and Reject buttons
        view = View()

        # Accept Button
        async def accept_callback(interaction):
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ You don't have permission to do this.", ephemeral=True)
                return

            try:
                await dm_channel.send("✅ Your suggestion has been **accepted**. Thank you for your input!")
                await interaction.message.edit(content="✅ This suggestion has been **accepted**.", embed=embed, view=None)
                await interaction.response.send_message("✅ Suggestion accepted.", ephemeral=True)
            except Exception as e:
                print(f"⚠️ Error sending DM to {ctx.author}: {e}")

        # Reject Button
        async def reject_callback(interaction):
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ You don't have permission to do this.", ephemeral=True)
                return

            try:
                await dm_channel.send("❌ Your suggestion has been **rejected**. Thank you for your input!")
                await interaction.message.edit(content="❌ This suggestion has been **rejected**.", embed=embed, view=None)
                await interaction.response.send_message("❌ Suggestion rejected.", ephemeral=True)
            except Exception as e:
                print(f"⚠️ Error sending DM to {ctx.author}: {e}")

        # Add the buttons to the view
        accept_button = Button(label="✅ Accept", style=discord.ButtonStyle.success)
        reject_button = Button(label="❌ Reject", style=discord.ButtonStyle.danger)

        accept_button.callback = accept_callback
        reject_button.callback = reject_callback

        view.add_item(accept_button)
        view.add_item(reject_button)

        # Send the suggestion to the channel
        await suggestion_channel.send(embed=embed, view=view)
        await dm_channel.send("✅ Your suggestion has been sent anonymously. Thank you for your feedback!")

    except TimeoutError:
        await dm_channel.send("❌ You took too long to respond. Please try again.")

    except Exception as e:
        print(f"⚠️ Error sending DM to {ctx.author}: {e}")





import aiohttp

# Detect and resend proxies as webhooks, while respecting the blacklist and proxy avatars
@bot.event
async def on_message(message):
    # Ignore messages from bots (including itself)
    if message.author.bot:
        return

    # Determine if the message is in a guild or a DM
    if message.guild:
        guild_id = str(message.guild.id)
        category_id = message.channel.category_id

        # Check if the message is in a blacklisted category
        if guild_id in category_blacklist and category_id in category_blacklist[guild_id]:
            return  # Ignore messages in blacklisted categories

        # Check if the message is in a blacklisted channel
        if guild_id in channel_blacklist and message.channel.id in channel_blacklist[guild_id]:
            return  # Ignore messages in blacklisted channels

    user_id = str(message.author.id)
    user_profiles = global_profiles.get(user_id, {}).get("alters", {})

    # Check each profile for a matching proxy
    for name, profile in user_profiles.items():
        proxy = profile.get("proxy")
        displayname = profile.get("displayname", name)

        # Use the proxy avatar if it exists, otherwise use the main avatar
        proxy_avatar = profile.get("proxy_avatar") or profile.get("avatar")

        # If the profile has a proxy set, check for it
        if proxy and message.content.startswith(proxy):
            # Remove the proxy from the message
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

    # Process other bot commands normally
    await bot.process_commands(message)






import os

# Use the bot token from the Replit secret
bot.run(os.getenv("NEW_BOT_TOKEN"))
