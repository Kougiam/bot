import json
import os
import discord
from discord.ext import commands

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reaction_roles.json")


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


class ReactionRoles(commands.Cog):
    """Δομή δεδομένων: { "message_id": { "emoji": role_id, ... }, ... }"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data: dict = load_data()

    @commands.group(name="reaction-role", invoke_without_command=True, help="Διαχείριση reaction roles.")
    async def reaction_role(self, ctx: commands.Context):
        await ctx.send('Χρήση: `!reaction-role add <message_id> <emoji> @ρόλος` ή `!reaction-role remove <message_id> <emoji>`')

    @reaction_role.command(name="add", help="Χρήση: !reaction-role add <message_id> <emoji> @ρόλος")
    @commands.has_permissions(manage_roles=True)
    async def rr_add(self, ctx: commands.Context, message_id: int, emoji: str, role: discord.Role):
        target_message = None
        for channel in ctx.guild.text_channels:
            try:
                target_message = await channel.fetch_message(message_id)
                break
            except (discord.NotFound, discord.Forbidden):
                continue

        if target_message is None:
            return await ctx.send("Δεν βρέθηκε μήνυμα με αυτό το ID σε κανάλι που μπορώ να διαβάσω.")

        try:
            await target_message.add_reaction(emoji)
        except discord.HTTPException:
            return await ctx.send("Μη έγκυρο emoji, ή δεν μπόρεσα να το προσθέσω.")

        self.data.setdefault(str(message_id), {})[emoji] = role.id
        save_data(self.data)
        await ctx.send(f"✅ Συνδέθηκε το {emoji} με τον ρόλο **{role.name}** στο μήνυμα `{message_id}`.")

    @reaction_role.command(name="remove", help="Χρήση: !reaction-role remove <message_id> <emoji>")
    @commands.has_permissions(manage_roles=True)
    async def rr_remove(self, ctx: commands.Context, message_id: int, emoji: str):
        mapping = self.data.get(str(message_id), {})
        if emoji not in mapping:
            return await ctx.send("Δεν βρέθηκε αυτή η σύνδεση.")
        del mapping[emoji]
        if not mapping:
            del self.data[str(message_id)]
        save_data(self.data)
        await ctx.send("🗑️ Αφαιρέθηκε.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.member is None or payload.member.bot:
            return
        mapping = self.data.get(str(payload.message_id))
        if not mapping:
            return
        role_id = mapping.get(str(payload.emoji))
        if not role_id:
            return
        role = payload.member.guild.get_role(role_id)
        if role:
            try:
                await payload.member.add_roles(role, reason="Reaction role")
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        mapping = self.data.get(str(payload.message_id))
        if not mapping:
            return
        role_id = mapping.get(str(payload.emoji))
        if not role_id:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        role = guild.get_role(role_id)
        if member and role and not member.bot:
            try:
                await member.remove_roles(role, reason="Reaction role αφαιρέθηκε")
            except discord.Forbidden:
                pass

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Χρειάζεσαι δικαίωμα Manage Roles.")
        elif isinstance(error, commands.RoleNotFound):
            await ctx.send("Δεν βρέθηκε αυτός ο ρόλος.")
        else:
            await ctx.send(f"Σφάλμα: {error}")


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionRoles(bot))
