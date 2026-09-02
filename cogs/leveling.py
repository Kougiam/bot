import json
import os
import random
import time
import discord
from discord.ext import commands

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "leveling.json")

XP_COOLDOWN_SECONDS = 60
XP_MIN = 15
XP_MAX = 25
LEVEL_UP_CHANNEL_ID = None


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
        json.dump(data, f, indent=2)


def xp_for_level(level: int) -> int:
    return 5 * (level ** 2) + 50 * level + 100


def level_from_xp(xp: int) -> int:
    level = 0
    while xp >= xp_for_level(level + 1):
        level += 1
    return level


class Leveling(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data: dict = load_data()
        self.cooldowns: dict[tuple[int, int], float] = {}

    def _user_entry(self, guild_id: int, user_id: int) -> dict:
        g = self.data.setdefault(str(guild_id), {})
        return g.setdefault(str(user_id), {"xp": 0, "level": 0})

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if message.content.startswith(self.bot.command_prefix):
            return  # δεν δίνουμε XP για μηνύματα-εντολές

        key = (message.guild.id, message.author.id)
        now = time.time()
        last = self.cooldowns.get(key, 0)
        if now - last < XP_COOLDOWN_SECONDS:
            return
        self.cooldowns[key] = now

        entry = self._user_entry(message.guild.id, message.author.id)
        entry["xp"] += random.randint(XP_MIN, XP_MAX)
        new_level = level_from_xp(entry["xp"])

        if new_level > entry["level"]:
            entry["level"] = new_level
            channel = message.channel
            if LEVEL_UP_CHANNEL_ID:
                lvl_channel = message.guild.get_channel(LEVEL_UP_CHANNEL_ID)
                if lvl_channel:
                    channel = lvl_channel
            try:
                await channel.send(f"🎉 Συγχαρητήρια {message.author.mention}! Έφτασες στο **Level {new_level}**!")
            except discord.Forbidden:
                pass

        save_data(self.data)

    @commands.command(name="rank", help="Level/XP κάποιου μέλους. Χρήση: !rank [@μέλος]")
    async def rank(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        entry = self._user_entry(ctx.guild.id, target.id)
        xp = entry["xp"]
        level = entry["level"]
        next_level_xp = xp_for_level(level + 1)
        current_level_xp = xp_for_level(level)
        progress = xp - current_level_xp
        needed = next_level_xp - current_level_xp

        embed = discord.Embed(title=f"📊 Rank του {target.display_name}", color=discord.Color.blurple())
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="Συνολικό XP", value=str(xp), inline=True)
        embed.add_field(name="Πρόοδος στο επόμενο level", value=f"{progress}/{needed} XP", inline=False)
        embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="leaderboard-xp", help="Top μέλη σε XP. Χρήση: !leaderboard-xp [αριθμός]")
    async def leaderboard_xp(self, ctx: commands.Context, top: int = 10):
        top = max(1, min(top, 25))
        guild_data = self.data.get(str(ctx.guild.id), {})
        if not guild_data:
            return await ctx.send("Δεν υπάρχουν ακόμα δεδομένα XP.")

        ranked = sorted(guild_data.items(), key=lambda x: x[1]["xp"], reverse=True)[:top]
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, (user_id, entry) in enumerate(ranked):
            member = ctx.guild.get_member(int(user_id))
            name = member.display_name if member else f"(αποχώρησε) {user_id}"
            prefix = medals[i] if i < 3 else f"**{i + 1}.**"
            lines.append(f"{prefix} {name} — Level {entry['level']} ({entry['xp']} XP)")

        embed = discord.Embed(title="🏆 XP Leaderboard", description="\n".join(lines), color=discord.Color.gold())
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Leveling(bot))
