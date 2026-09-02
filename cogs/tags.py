import json
import os
import discord
from discord.ext import commands

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tags.json")


def load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_data(data: dict):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class Tags(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data: dict = load_data()

    def _guild_tags(self, guild_id: int) -> dict:
        return self.data.setdefault(str(guild_id), {})

    @commands.group(name="tag", invoke_without_command=True, help='Δείχνει tag. Χρήση: !tag <όνομα>')
    async def tag(self, ctx: commands.Context, name: str = None):
        if name is None:
            return await ctx.send('Χρήση: `!tag <όνομα>` ή `!tag add/edit/remove/list`')
        name = name.lower().strip()
        tags = self._guild_tags(ctx.guild.id)
        if name not in tags:
            return await ctx.send(f"Δεν βρέθηκε tag `{name}`.")
        await ctx.send(tags[name])

    @tag.command(name="add", help='Δημιουργεί tag. Χρήση: !tag add <όνομα> <περιεχόμενο>')
    @commands.has_permissions(manage_messages=True)
    async def tag_add(self, ctx: commands.Context, name: str, *, content: str):
        name = name.lower().strip()
        tags = self._guild_tags(ctx.guild.id)
        if name in tags:
            return await ctx.send(f"Το tag `{name}` υπάρχει ήδη. Χρησιμοποίησε `!tag edit`.")
        tags[name] = content
        save_data(self.data)
        await ctx.send(f"✅ Δημιουργήθηκε το tag `{name}`.")

    @tag.command(name="edit", help='Επεξεργάζεται tag. Χρήση: !tag edit <όνομα> <νέο περιεχόμενο>')
    @commands.has_permissions(manage_messages=True)
    async def tag_edit(self, ctx: commands.Context, name: str, *, content: str):
        name = name.lower().strip()
        tags = self._guild_tags(ctx.guild.id)
        if name not in tags:
            return await ctx.send(f"Δεν βρέθηκε tag `{name}`.")
        tags[name] = content
        save_data(self.data)
        await ctx.send(f"✅ Ενημερώθηκε το tag `{name}`.")

    @tag.command(name="remove", help='Διαγράφει tag. Χρήση: !tag remove <όνομα>')
    @commands.has_permissions(manage_messages=True)
    async def tag_remove(self, ctx: commands.Context, name: str):
        name = name.lower().strip()
        tags = self._guild_tags(ctx.guild.id)
        if name not in tags:
            return await ctx.send(f"Δεν βρέθηκε tag `{name}`.")
        del tags[name]
        save_data(self.data)
        await ctx.send(f"🗑️ Διαγράφηκε το tag `{name}`.")

    @tag.command(name="list", help="Λίστα με όλα τα tags.")
    async def tag_list(self, ctx: commands.Context):
        tags = self._guild_tags(ctx.guild.id)
        if not tags:
            return await ctx.send("Δεν υπάρχουν tags ακόμα.")
        names = ", ".join(f"`{n}`" for n in sorted(tags.keys()))
        embed = discord.Embed(title="📌 Διαθέσιμα Tags", description=names, color=discord.Color.blurple())
        await ctx.send(embed=embed)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Χρειάζεσαι δικαίωμα Manage Messages.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Λείπει παράμετρος. Δες: `!help {ctx.command}`")
        else:
            await ctx.send(f"Σφάλμα: {error}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Tags(bot))
