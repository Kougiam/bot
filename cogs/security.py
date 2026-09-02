import re
import datetime
import discord
from discord.ext import commands

SECURITY_LOG_CHANNEL_ID = 1538453550550753290

ANTI_LINK_ENABLED = True
ANTI_LINK_EXEMPT_ROLE_IDS: list[int] = []
ANTI_LINK_EXEMPT_CHANNEL_IDS: list[int] = []

LINK_REGEX = re.compile(r"(https?://|www\.|discord\.gg/)\S+", re.IGNORECASE)

ANTI_ALT_ENABLED = True
MIN_ACCOUNT_AGE_DAYS = 7
ANTI_ALT_ACTION = "alert"  # "kick" ή "alert"


class Security(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _log(self, guild: discord.Guild, embed: discord.Embed):
        if not SECURITY_LOG_CHANNEL_ID:
            return
        channel = guild.get_channel(SECURITY_LOG_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not ANTI_LINK_ENABLED or message.author.bot or not message.guild:
            return
        # Μην μπλοκάρεις τις ίδιες τις εντολές του bot (π.χ. !ticket-panel κ.λπ.)
        if message.content.startswith(self.bot.command_prefix):
            return
        if message.channel.id in ANTI_LINK_EXEMPT_CHANNEL_IDS:
            return

        member = message.author
        if isinstance(member, discord.Member):
            if member.guild_permissions.manage_messages:
                return
            if any(r.id in ANTI_LINK_EXEMPT_ROLE_IDS for r in member.roles):
                return

        if LINK_REGEX.search(message.content):
            try:
                await message.delete()
            except discord.Forbidden:
                return
            try:
                await message.channel.send(f"🔗 {member.mention}, δεν επιτρέπονται links σε αυτό το κανάλι.", delete_after=6)
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not ANTI_ALT_ENABLED or member.bot:
            return
        account_age = datetime.datetime.now(datetime.timezone.utc) - member.created_at
        if account_age.days < MIN_ACCOUNT_AGE_DAYS:
            embed = discord.Embed(
                title="🚨 Πιθανός Alt Λογαριασμός",
                description=(
                    f"**{member}** ({member.id}) μπήκε στον server.\n"
                    f"Ο λογαριασμός δημιουργήθηκε πριν από **{account_age.days} ημέρες** "
                    f"(ελάχιστο απαιτούμενο: {MIN_ACCOUNT_AGE_DAYS})."
                ),
                color=discord.Color.red(),
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
            await self._log(member.guild, embed)

            if ANTI_ALT_ACTION == "kick":
                try:
                    await member.send(
                        f"Έγινες kick από **{member.guild.name}** επειδή ο λογαριασμός σου "
                        f"είναι πολύ πρόσφατος (λιγότερο από {MIN_ACCOUNT_AGE_DAYS} ημέρες)."
                    )
                except discord.Forbidden:
                    pass
                try:
                    await member.kick(reason=f"Anti-alt: λογαριασμός {account_age.days} ημερών")
                except discord.Forbidden:
                    pass

    @commands.command(name="security-status", help="Δείχνει τις ρυθμίσεις ασφαλείας.")
    @commands.has_permissions(manage_guild=True)
    async def security_status(self, ctx: commands.Context):
        embed = discord.Embed(title="🛡️ Ρυθμίσεις Ασφαλείας", color=discord.Color.blurple())
        embed.add_field(name="Anti-link", value="✅ Ενεργό" if ANTI_LINK_ENABLED else "❌ Ανενεργό", inline=True)
        embed.add_field(
            name="Anti-alt",
            value=f"{'✅ Ενεργό' if ANTI_ALT_ENABLED else '❌ Ανενεργό'} ({ANTI_ALT_ACTION}, min {MIN_ACCOUNT_AGE_DAYS}d)",
            inline=True,
        )
        await ctx.send(embed=embed)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Χρειάζεσαι δικαίωμα Manage Guild.")
        else:
            await ctx.send(f"Σφάλμα: {error}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Security(bot))
