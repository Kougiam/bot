import discord
from discord.ext import commands

WELCOME_ROLE_ID = 1182074779298168893
WELCOME_CHANNEL_ID = 1538950021733679195


class RoleButton(discord.ui.Button):
    def __init__(self, role_id: int, label: str, emoji: str = None, style=discord.ButtonStyle.secondary):
        super().__init__(label=label, emoji=emoji, style=style, custom_id=f"autorole:{role_id}")
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(self.role_id)
        if role is None:
            return await interaction.response.send_message("Ο ρόλος δεν βρέθηκε πια.", ephemeral=True)

        member = interaction.user
        if role in member.roles:
            await member.remove_roles(role)
            await interaction.response.send_message(f"➖ Αφαιρέθηκε ο ρόλος **{role.name}**.", ephemeral=True)
        else:
            await member.add_roles(role)
            await interaction.response.send_message(f"➕ Πήρες τον ρόλο **{role.name}**.", ephemeral=True)


class RolePanelView(discord.ui.View):
    def __init__(self, roles: list[tuple[int, str, str]] = None):
        super().__init__(timeout=None)
        if roles:
            for role_id, label, emoji in roles:
                self.add_item(RoleButton(role_id, label, emoji))


class AutoRole(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if WELCOME_ROLE_ID:
            role = member.guild.get_role(WELCOME_ROLE_ID)
            if role:
                try:
                    await member.add_roles(role, reason="Auto-role νέου μέλους")
                except discord.Forbidden:
                    pass

        if WELCOME_CHANNEL_ID:
            channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
            if channel:
                embed = discord.Embed(
                    description=f"👋 Καλωσόρισες {member.mention} στο **{member.guild.name}**!",
                    color=discord.Color.green(),
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=embed)

    @commands.command(
        name="role-panel",
        help="Δημιουργεί panel self-roles. Χρήση: !role-panel \"Τίτλος\" @ρόλος1 \"Ετικέτα1\" [@ρόλος2 \"Ετικέτα2\" ...]",
    )
    @commands.has_permissions(manage_roles=True)
    async def role_panel(self, ctx: commands.Context, title: str, *args):
        if len(args) < 2 or len(args) % 2 != 0:
            return await ctx.send(
                'Χρήση: `!role-panel "Τίτλος" @ρόλος1 "Ετικέτα1" @ρόλος2 "Ετικέτα2" ...` (μέχρι 3 ρόλους)'
            )

        pairs = list(zip(args[0::2], args[1::2]))[:3]
        roles = []
        converter = commands.RoleConverter()
        for role_mention, label in pairs:
            try:
                role = await converter.convert(ctx, role_mention)
            except commands.RoleNotFound:
                return await ctx.send(f"Δεν βρέθηκε ρόλος: {role_mention}")
            roles.append((role.id, label, None))

        embed = discord.Embed(title=title, description="Πάτησε ένα κουμπί για να πάρεις/αφαιρέσεις τον ρόλο.", color=discord.Color.blurple())
        view = RolePanelView(roles)
        await ctx.send(embed=embed, view=view)
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Χρειάζεσαι δικαίωμα Manage Roles.")
        elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.NotFound):
            pass
        else:
            await ctx.send(f"Σφάλμα: {error}")


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRole(bot))