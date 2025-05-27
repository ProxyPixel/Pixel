import discord
from discord.ext import commands
import asyncio
import uuid
from datetime import datetime

from utils.mongodb import db
from utils.helpers import find_alter_by_name, create_embed

class AlterCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="create")
    async def create_alter(self, ctx, name: str, pronouns: str = None, *, description: str = None):
        """Create a new alter profile."""
        user_id = str(ctx.author.id)

        # Load or initialize profile
        profile = db.get_profile(user_id) or {"user_id": user_id, "system": {}, "alters": {}, "folders": {}}

        if name in profile["alters"]:
            return await ctx.send(f"❌ An alter named **{name}** already exists.")

        alter_id = str(uuid.uuid4())[:8]
        profile["alters"][name] = {
            "alter_id": alter_id,
            "displayname": name,
            "pronouns": pronouns,
            "description": description,
            "avatar": None,
            "banner": None,
            "proxy": None,
            "proxy_avatar": None,
            "aliases": [],
            "color": None,
            "created_date": datetime.utcnow().isoformat()
        }
        db.save_profile(user_id, profile)

        embed = create_embed(
            title="✅ Alter Created Successfully",
            description=f"Alter **{name}** has been created!\nID: `{alter_id}`"
        )
        if pronouns:
            embed.add_field(name="Pronouns", value=pronouns, inline=True)
        if description:
            embed.add_field(name="Description", value=description, inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="show")
    async def show_alter(self, ctx, *, query: str):
        """Display an alter's details."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        if not profile or not profile.get("alters"):
            return await ctx.send("❌ You have no alters. Use `!create <name>` to add one.")

        actual = find_alter_by_name(profile, query)
        if not actual:
            return await ctx.send(f"❌ Alter '{query}' not found.")

        data = profile["alters"][actual]
        color = int(data.get('color', '0x8A2BE2').lstrip('#'), 16) if data.get('color') else 0x8A2BE2

        embed = discord.Embed(title=f"👤 {data.get('displayname', actual)}", color=color)
        if data.get('pronouns'):
            embed.add_field(name="🏷️ Pronouns", value=data['pronouns'], inline=True)
        if data.get('description'):
            embed.add_field(name="📝 Description", value=data['description'], inline=False)
        if data.get('proxy'):
            tag = data['proxy'].rstrip('None')
            embed.add_field(name="🗨️ Proxy Tag", value=f"`{tag}`", inline=True)
        if data.get('aliases'):
            embed.add_field(name="🔗 Aliases", value=", ".join(data['aliases']), inline=False)
        if data.get('color'):
            embed.add_field(name="🎨 Color", value=data['color'], inline=True)
        if data.get('avatar'):
            embed.set_thumbnail(url=data['avatar'])
        if data.get('banner'):
            embed.set_image(url=data['banner'])
        if data.get('proxy_avatar'):
            embed.add_field(name="🖼️ Proxy Avatar", value="Custom proxy avatar set", inline=True)

        embed.set_footer(text=f"Internal key: {actual}")
        await ctx.send(embed=embed)

    @commands.command(name="list_profiles")
    async def list_profiles(self, ctx):
        """Paginated list of all alters."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        alters = profile.get('alters', {}) if profile else {}
        if not alters:
            return await ctx.send("❌ No alters to list.")

        items = list(alters.items())
        per_page = 10
        pages = (len(items) + per_page - 1) // per_page
        page = 1

        def make_embed(p):
            start = (p-1)*per_page
            end = min(start+per_page, len(items))
            e = create_embed(
                title="👥 Your Alters",
                description=f"Total: {len(items)} • Page {p}/{pages}"
            )
            for i, (name, d) in enumerate(items[start:end], start+1):
                alias_info = f" • Aliases: {len(d.get('aliases', []))}" if d.get('aliases') else ""
                e.add_field(
                    name=f"{i}. {d.get('displayname', name)}",
                    value=f"Pronouns: {d.get('pronouns','Not set')}{alias_info}",
                    inline=False
                )
            if pages > 1:
                e.set_footer(text="Use ⬅️ and ➡️ to navigate.")
            return e

        msg = await ctx.send(embed=make_embed(page))
        if pages > 1 and ctx.guild:
            await msg.add_reaction('⬅️'); await msg.add_reaction('➡️')
            def check(r,u): return u==ctx.author and r.message.id==msg.id and str(r.emoji) in ['⬅️','➡️']
            while True:
                try:
                    r, _ = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                    if str(r.emoji)=='⬅️' and page>1: page-=1
                    elif str(r.emoji)=='➡️' and page<pages: page+=1
                    await msg.edit(embed=make_embed(page))
                    await msg.remove_reaction(r.emoji, r.user)
                except asyncio.TimeoutError:
                    try: await msg.clear_reactions()
                    except: pass
                    break
        elif pages>1:
            await ctx.send(f"📄 {pages} pages. Use in-server for reactions.")

    @commands.command(name="edit")
    async def edit_alter(self, ctx, *, query: str):
        """Interactive edit of alter fields."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        if not profile:
            return await ctx.send("❌ No alters to edit.")
        actual = find_alter_by_name(profile, query)
        if not actual:
            return await ctx.send(f"❌ Alter '{query}' not found.")

        options = ['🏷️','👤','📝','🖼️','🎨','🗨️','🌈','👥']
        actions = {'🏷️':'displayname','👤':'pronouns','📝':'description','🖼️':'avatar','🎨':'banner','🗨️':'proxy','🌈':'color','👥':'proxy_avatar'}
        embed = create_embed(
            title=f"⚙️ Edit {actual}",
            description="React with emoji for field:"
        )
        names = {'🏷️':'Display Name','👤':'Pronouns','📝':'Description','🖼️':'Avatar','🎨':'Banner','🗨️':'Proxy Tag','🌈':'Color','👥':'Proxy Avatar'}
        for em in options: embed.add_field(name=em, value=names[em], inline=True)
        msg = await ctx.send(embed=embed)
        for em in options: await msg.add_reaction(em)

        def check(r,u): return u==ctx.author and r.message.id==msg.id and str(r.emoji) in options
        try:
            r,_ = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
            field = actions[str(r.emoji)]
            await self._edit_field(ctx, user_id, actual, field)
        except asyncio.TimeoutError:
            await ctx.send("⏰ Edit timed out.")

    async def _edit_field(self, ctx, user_id: str, alter: str, field: str):
        prompts = {
            'displayname':'Enter new display name:',
            'pronouns':'Enter new pronouns:',
            'description':'Enter new description:',
            'avatar':'Enter new avatar URL:',
            'banner':'Enter new banner URL:',
            'proxy':'Enter new proxy tag:',
            'color':'Enter new color (hex):',
            'proxy_avatar':'Enter new proxy avatar URL:'
        }
        await ctx.send(prompts[field])
        def mcheck(m): return m.author.id==int(user_id) and m.channel==ctx.channel
        try:
            m = await self.bot.wait_for('message', timeout=60.0, check=mcheck)
            profile = db.get_profile(user_id)
            data = profile['alters'][alter]
            val = m.content.strip()
            if field=='color':
                if not val.startswith('#'): val='#'+val
                if len(val)!=7 or not all(c in '0123456789abcdefABCDEF' for c in val[1:]):
                    return await ctx.send("❌ Invalid hex color.")
            data[field] = val
            db.save_profile(user_id, profile)
            await ctx.send(f"✅ {field.title()} updated.")
        except asyncio.TimeoutError:
            await ctx.send("⏰ Update timed out.")

    @commands.command(name="delete")
    async def delete_alter(self, ctx, *, query: str):
        """Delete an alter permanently."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        if not profile:
            return await ctx.send("❌ No alters to delete.")
        actual = find_alter_by_name(profile, query)
        if not actual:
            return await ctx.send(f"❌ Alter '{query}' not found.")

        embed = create_embed(
            title="⚠️ Delete Alter",
            description=f"React ✅ to confirm deletion of **{actual}**, or ❌ to cancel."
        )
        msg = await ctx.send(embed=embed)
        await msg.add_reaction('✅'); await msg.add_reaction('❌')
        def c(r,u): return u==ctx.author and r.message.id==msg.id and str(r.emoji) in ['✅','❌']
        try:
            r,_ = await self.bot.wait_for('reaction_add', timeout=60.0, check=c)
            if str(r.emoji)=='✅':
                del profile['alters'][actual]
                db.save_profile(user_id, profile)
                await ctx.send(f"✅ Alter **{actual}** deleted.")
            else:
                await ctx.send("❌ Deletion cancelled.")
        except asyncio.TimeoutError:
            await ctx.send("⏰ Timed out.")

    @commands.command(name="alias")
    async def add_alias(self, ctx, query: str, *, alias: str):
        """Add an alias to an alter."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        actual = find_alter_by_name(profile, query) if profile else None
        if not actual:
            return await ctx.send(f"❌ Alter '{query}' not found.")
        aliases = profile['alters'][actual].setdefault('aliases', [])
        if alias in aliases:
            return await ctx.send(f"❌ Alias '{alias}' already exists.")
        aliases.append(alias)
        db.save_profile(user_id, profile)
        await ctx.send(f"✅ Alias '{alias}' added to **{actual}**.")

    @commands.command(name="remove_alias")
    async def remove_alias(self, ctx, query: str, *, alias: str):
        """Remove an alias from an alter."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        actual = find_alter_by_name(profile, query) if profile else None
        if not actual:
            return await ctx.send(f"❌ Alter '{query}' not found.")
        aliases = profile['alters'][actual].get('aliases', [])
        if alias not in aliases:
            return await ctx.send(f"❌ Alias '{alias}' not found.")
        aliases.remove(alias)
        db.save_profile(user_id, profile)
        await ctx.send(f"✅ Alias '{alias}' removed from **{actual}**.")

    @commands.command(name="proxyavatar")
    async def set_proxy_avatar(self, ctx, query: str, *, url: str = None):
        """Set or clear a proxy avatar for an alter."""
        user_id = str(ctx.author.id)
        profile = db.get_profile(user_id)
        actual = find_alter_by_name(profile, query) if profile else None
        if not actual:
            return await ctx.send(f"❌ Alter '{query}' not found.")
        profile['alters'][actual]['proxy_avatar'] = url.strip() if url else None
        db.save_profile(user_id, profile)
        action = 'Set' if url else 'Cleared'
        await ctx.send(f"✅ {action} proxy avatar for **{actual}**.")

async def setup(bot):
    await bot.add_cog(AlterCommands(bot))
