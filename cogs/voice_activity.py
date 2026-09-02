import json
import os
import time
import discord
from discord.ext import commands, tasks

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "voice_activity.json")


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


def format_duration(seconds: int) -> str:
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}ω {minutes}λ"
    if minutes:
        return f"{minutes}λ {secs}δ"
    return f"{secs}δ"


class VoiceActivity(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.sessions: dict[tuple[int, int], float] = {}
        self.data: dict = load_data()

    async def cog_load(self):
        for guild in self.bot.guilds:
            for channel in guild.voice_channels:
                for member in channel.members:
                    if not member.bot:
                        self.sessions[(guild.id, member.id)] = time.time()
        self.autosave.start()

    async def cog_unload(self):
        self.autosave.cancel()
        self._flush_all_sessions()
        save_data(self.data)

    @tasks.loop(minutes=5)
    async def autosave(self):
        save_data(self.data)

    def _add_time(self, guild_id: int, user_id: int, seconds: float):
        g = self.data.setdefault(str(guild_id), {})
        g[str(user_id)] = g.get(str(user_id), 0) + seconds

    def _flush_all_sessions(self):
        now = time.time()
        for (guild_id, user_id), start in list(self.sessions.items()):
            self._add_time(guild_id, user_id, now - start)
        self.sessions.clear()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return
        key = (member.guild.id, member.id)
        if before.channel is None and after.channel is not None:
            self.sessions[key] = time.time()
            return
        if before.channel is not None and after.channel is None:
            start = self.sessions.pop(key, None)
            if start is not None:
                self._add_time(member.guild.id, member.id, time.time() - start)
                save_data(self.data)
            return

    def _current_total(self, guild_id: int, user_id: int) -> float:
        stored = self.data.get(str(guild_id), {}).get(str(user_id), 0)
        session_start = self.sessions.get((guild_id, user_id))
        if session_start is not None:
            stored += time.time() - session_start
        return stored

    @commands.command(name="voice-time", help="Χρόνος σε voice. Χρήση: !voice-time [@μέλος]")
    async def voice_time(self, ctx: commands.Context, member: discord.Member = None):
        target = member or ctx.author
        total = self._current_total(ctx.guild.id, target.id)
        await ctx.send(f"🎙️ **{target.display_name}** έχει περάσει **{format_duration(total)}** σε voice κανάλια.")

    @commands.command(name="voice-leaderboard", help="Top μέλη σε voice. Χρήση: !voice-leaderboard [αριθμός]")
    async def voice_leaderboard(self, ctx: commands.Context, top: int = 10):
        top = max(1, min(top, 25))
        guild_data = self.data.get(str(ctx.guild.id), {})
        totals: dict[int, float] = {int(uid): secs for uid, secs in guild_data.items()}
        for (guild_id, user_id), start in self.sessions.items():
            if guild_id == ctx.guild.id:
                totals[user_id] = totals.get(user_id, 0) + (time.time() - start)

        if not totals:
            return await ctx.send("Δεν υπάρχουν ακόμα δεδομένα voice activity.")

        ranked = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:top]
        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for i, (user_id, secs) in enumerate(ranked):
            member = ctx.guild.get_member(user_id)
            name = member.display_name if member else f"(αποχώρησε) {user_id}"
            prefix = medals[i] if i < 3 else f"**{i + 1}.**"
            lines.append(f"{prefix} {name} — {format_duration(secs)}")

        embed = discord.Embed(title="🏆 Voice Activity Leaderboard", description="\n".join(lines), color=discord.Color.blurple())
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceActivity(bot))
