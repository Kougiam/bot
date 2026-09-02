import datetime
import discord
from discord.ext import commands

# Κανάλι όπου θα στέλνονται όλα τα logs. Βάλε εδώ το ID σου.
LOG_CHANNEL_ID = 1538453025708838922


class Logging(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send(self, guild: discord.Guild, embed: discord.Embed):
        if not LOG_CHANNEL_ID:
            return
        channel = guild.get_channel(LOG_CHANNEL_ID)
        if channel:
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                pass

    def _base_embed(self, title: str, color: discord.Color) -> discord.Embed:
        return discord.Embed(title=title, color=color, timestamp=datetime.datetime.now(datetime.timezone.utc))

    # ---------- BANS ----------
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        embed = self._base_embed("🔨 Ban", discord.Color.red())
        embed.description = f"**{user}** ({user.id}) έκανε ban."
        await self._send(guild, embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        embed = self._base_embed("♻️ Unban", discord.Color.green())
        embed.description = f"**{user}** ({user.id}) έγινε unban."
        await self._send(guild, embed)

    # ---------- MEMBERS ----------
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        embed = self._base_embed("👋 Αποχώρηση Μέλους", discord.Color.orange())
        embed.description = f"**{member}** ({member.id}) έφυγε ή έγινε kick από τον server."
        await self._send(member.guild, embed)

    # ---------- MESSAGES ----------
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        embed = self._base_embed("🗑️ Διαγραμμένο Μήνυμα", discord.Color.dark_grey())
        content = message.content or "*(χωρίς κείμενο — πιθανόν embed/αρχείο)*"
        embed.description = (
            f"**Χρήστης:** {message.author.mention}\n"
            f"**Κανάλι:** {message.channel.mention}\n"
            f"**Περιεχόμενο:** {content[:1000]}"
        )
        await self._send(message.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        embed = self._base_embed("✏️ Επεξεργασμένο Μήνυμα", discord.Color.gold())
        embed.description = (
            f"**Χρήστης:** {before.author.mention}\n"
            f"**Κανάλι:** {before.channel.mention}\n"
            f"**Πριν:** {before.content[:500] or '*(κενό)*'}\n"
            f"**Μετά:** {after.content[:500] or '*(κενό)*'}"
        )
        await self._send(before.guild, embed)

    # ---------- INVITES ----------
    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        embed = self._base_embed("📨 Νέα Πρόσκληση", discord.Color.blue())
        creator = invite.inviter.mention if invite.inviter else "Άγνωστος"
        embed.description = (
            f"**Κωδικός:** {invite.code}\n"
            f"**Δημιουργός:** {creator}\n"
            f"**Κανάλι:** {invite.channel.mention if invite.channel else '—'}\n"
            f"**Λήγει:** {'Ποτέ' if invite.max_age == 0 else f'{invite.max_age}s'}"
        )
        await self._send(invite.guild, embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        embed = self._base_embed("🚫 Διαγραμμένη Πρόσκληση", discord.Color.dark_grey())
        embed.description = f"**Κωδικός:** {invite.code}"
        await self._send(invite.guild, embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Logging(bot))
