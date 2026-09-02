import discord
from discord.ext import commands
from datetime import timedelta


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------- KICK ----------
    @commands.command(name="kick", help="Κάνει kick έναν χρήστη. Χρήση: !kick @χρήστης [λόγος]")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Δεν δόθηκε λόγος"):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("Δεν μπορείς να κάνεις kick κάποιον με ίσο ή υψηλότερο ρόλο.")
        try:
            await member.send(f"Έκανες kick από **{ctx.guild.name}**.\nΛόγος: {reason}")
        except discord.Forbidden:
            pass
        await member.kick(reason=reason)
        embed = discord.Embed(
            title="👢 Kick",
            description=f"**{member}** έκανε kick.\n**Λόγος:** {reason}",
            color=discord.Color.orange(),
        )
        await ctx.send(embed=embed)

    # ---------- BAN ----------
    @commands.command(name="ban", help="Κάνει ban έναν χρήστη. Χρήση: !ban @χρήστης [λόγος]")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "Δεν δόθηκε λόγος"):
        if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
            return await ctx.send("Δεν μπορείς να κάνεις ban κάποιον με ίσο ή υψηλότερο ρόλο.")
        try:
            await member.send(f"Έκανες ban από **{ctx.guild.name}**.\nΛόγος: {reason}")
        except discord.Forbidden:
            pass
        await member.ban(reason=reason)
        embed = discord.Embed(
            title="🔨 Ban",
            description=f"**{member}** έκανε ban.\n**Λόγος:** {reason}",
            color=discord.Color.red(),
        )
        await ctx.send(embed=embed)

    # ---------- UNBAN ----------
    @commands.command(name="unban", help="Αίρει ban. Χρήση: !unban <user_id>")
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx: commands.Context, user_id: int):
        try:
            user = await self.bot.fetch_user(user_id)
            await ctx.guild.unban(user)
            await ctx.send(f"✅ Έγινε unban ο/η **{user}**.")
        except discord.NotFound:
            await ctx.send("Δεν βρέθηκε χρήστης με αυτό το ID σε ban list.")

    # ---------- MUTE / TIMEOUT ----------
    @commands.command(name="mute", help="Κάνει timeout. Χρήση: !mute @χρήστης <λεπτά> [λόγος]")
    @commands.has_permissions(moderate_members=True)
    async def mute(self, ctx: commands.Context, member: discord.Member, minutes: int, *, reason: str = "Δεν δόθηκε λόγος"):
        if minutes <= 0 or minutes > 40320:
            return await ctx.send("Η διάρκεια πρέπει να είναι 1-40320 λεπτά (28 μέρες).")
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        embed = discord.Embed(
            title="🔇 Mute",
            description=f"**{member}** έκανε mute για **{minutes} λεπτά**.\n**Λόγος:** {reason}",
            color=discord.Color.yellow(),
        )
        await ctx.send(embed=embed)

    @commands.command(name="unmute", help="Αφαιρεί timeout. Χρήση: !unmute @χρήστης")
    @commands.has_permissions(moderate_members=True)
    async def unmute(self, ctx: commands.Context, member: discord.Member):
        await member.timeout(None)
        await ctx.send(f"🔊 Το mute αφαιρέθηκε από **{member}**.")

    # ---------- WARN ----------
    @commands.command(name="warn", help="Προειδοποίηση. Χρήση: !warn @χρήστης <λόγος>")
    @commands.has_permissions(moderate_members=True)
    async def warn(self, ctx: commands.Context, member: discord.Member, *, reason: str):
        try:
            await member.send(f"⚠️ Έλαβες προειδοποίηση στο **{ctx.guild.name}**.\nΛόγος: {reason}")
        except discord.Forbidden:
            pass
        embed = discord.Embed(
            title="⚠️ Προειδοποίηση",
            description=f"**{member}** προειδοποιήθηκε από {ctx.author.mention}.\n**Λόγος:** {reason}",
            color=discord.Color.gold(),
        )
        await ctx.send(embed=embed)

    # ---------- CLEAR ----------
    @commands.command(name="clear", help="Διαγράφει μηνύματα. Χρήση: !clear <αριθμός 1-100>")
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx: commands.Context, amount: int):
        if amount < 1 or amount > 100:
            return await ctx.send("Ο αριθμός πρέπει να είναι 1-100.")
        await ctx.message.delete()
        deleted = await ctx.channel.purge(limit=amount)
        msg = await ctx.send(f"🧹 Διαγράφηκαν **{len(deleted)}** μηνύματα.")
        await msg.delete(delay=4)

    # ---------- Error handling ----------
    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Δεν έχεις τα απαραίτητα δικαιώματα για αυτή την εντολή.")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send("Δεν βρέθηκε αυτό το μέλος.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Λείπει παράμετρος. Δες: `!help {ctx.command}`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Μη έγκυρη τιμή σε κάποια παράμετρο.")
        else:
            await ctx.send(f"Παρουσιάστηκε σφάλμα: {error}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Moderation(bot))
