import asyncio
import io
import re
import discord
from discord.ext import commands

TICKET_CATEGORY_ID = 1538458066503335936
SUPPORT_ROLE_ID = 1182074655557828638
TICKET_LOG_CHANNEL_ID = 1544658651812466740

##Κατηγορίες tickets που θα εμφανίζονται στο dropdown menu.
##"ping_role_ids": λίστα με IDs ρόλων που θα γίνονται tag αυτόματα όταν ανοίγει ticket αυτής της κατηγορίας.
##Άφησε κενή λίστα [] αν δεν θες να γίνεται tag κανένας ρόλος για τη συγκεκριμένη κατηγορία.
TICKET_CATEGORIES = [
    {
        "label": "Support", "value": "support", "emoji": "🛠️",
        "description": "Γενική βοήθεια/ερωτήσεις",
        "ping_role_ids": [1182074655557828638],  # π.χ. [123456789012345678]
    },
    {
        "label": "Bug Report", "value": "bug", "emoji": "🐞",
        "description": "Ανέφερε ένα πρόβλημα/bug",
        "ping_role_ids": [1182074645239832718],
    },
    {
        "label": "Ownership", "value": "ownership", "emoji": "👑",
        "description": "Θέματα ιδιοκτησίας/staff",
        "ping_role_ids": [1182074615820988418, 1531791723980783656, 1182074618689884211],  # π.χ. [111111111111111111, 222222222222222222]
    },
    {
        "label": "Παράπονο", "value": "report", "emoji": "🚫",
        "description": "Αναφορά χρήστη/παραβίασης κανόνων",
        "ping_role_ids": [1182074655557828638],
    },
]


class TicketCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=c["label"], value=c["value"], emoji=c.get("emoji"), description=c.get("description"))
            for c in TICKET_CATEGORIES
        ]
        super().__init__(
            placeholder="Επίλεξε κατηγορία...",
            options=options,
            custom_id="ticket:category_select",
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        author = interaction.user
        category_value = self.values[0]
        category = next((c for c in TICKET_CATEGORIES if c["value"] == category_value), None)
        category_label = category["label"] if category else category_value
        ping_role_ids = category.get("ping_role_ids", []) if category else []

        channel_name = f"ticket-{author.name}".lower()
        existing = discord.utils.get(guild.text_channels, name=channel_name)
        if existing:
            return await interaction.response.send_message(
                f"Έχεις ήδη ανοιχτό ticket: {existing.mention}", ephemeral=True
            )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            author: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        if SUPPORT_ROLE_ID:
            support_role = guild.get_role(SUPPORT_ROLE_ID)
            if support_role:
                overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        # Δίνουμε πρόσβαση και στους ρόλους που θα γίνουν tag για αυτή την κατηγορία,
        # ώστε να μπορούν να δουν το κανάλι που θα αναφερθούν.
        ping_roles = []
        for role_id in ping_role_ids:
            role = guild.get_role(role_id)
            if role:
                ping_roles.append(role)
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        category = guild.get_channel(TICKET_CATEGORY_ID) if TICKET_CATEGORY_ID else None

        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Ticket ({category_label}) του {author} (ID: {author.id})",
        )

        embed = discord.Embed(
            title="🎫 Νέο Ticket",
            description=(
                f"**Κατηγορία:** {category_label}\n\n"
                f"Γεια σου {author.mention}! Περίγραψε το θέμα σου και η ομάδα support "
                f"θα σε εξυπηρετήσει σύντομα."
            ),
            color=discord.Color.blurple(),
        )

        # Στέλνουμε πρώτα το mention (αν υπάρχουν ρόλοι για αυτή την κατηγορία), μετά το embed.
        if ping_roles:
            mentions = " ".join(role.mention for role in ping_roles)
            await channel.send(
                f"{mentions} — νέο ticket κατηγορίας **{category_label}** από {author.mention}",
                allowed_mentions=discord.AllowedMentions(roles=True),
            )

        await channel.send(embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"✅ Το ticket σου δημιουργήθηκε: {channel.mention}", ephemeral=True)


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔔 Ping", style=discord.ButtonStyle.secondary, custom_id="ticket:ping")
    async def ping_creator(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Μόνο staff (Manage Channels ή ο ρόλος support) μπορεί να κάνει ping.
        if not (interaction.user.guild_permissions.manage_channels
                or (SUPPORT_ROLE_ID and any(r.id == SUPPORT_ROLE_ID for r in interaction.user.roles))):
            return await interaction.response.send_message("Μόνο η ομάδα support μπορεί να κάνει ping.", ephemeral=True)

        author_id = self._get_author_id(interaction.channel)
        if author_id is None:
            return await interaction.response.send_message(
                "Δεν μπόρεσα να βρω ποιος άνοιξε αυτό το ticket (λείπει το topic του καναλιού).", ephemeral=True
            )

        await interaction.response.send_message(f"🔔 <@{author_id}>, το staff χρειάζεται την προσοχή σου εδώ!")

    @discord.ui.button(label="🔒 Κλείσιμο Ticket", style=discord.ButtonStyle.red, custom_id="ticket:close")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Το ticket κλείνει σε 5 δευτερόλεπτα... (δημιουργείται transcript)")

        await self._save_transcript(interaction.channel, interaction.guild, interaction.user)

        await interaction.channel.edit(name=f"closed-{interaction.channel.name}")
        await interaction.channel.set_permissions(interaction.guild.default_role, view_channel=False)
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @staticmethod
    async def _save_transcript(channel: discord.TextChannel, guild: discord.Guild, closer: discord.Member):
        if not TICKET_LOG_CHANNEL_ID:
            return
        log_channel = guild.get_channel(TICKET_LOG_CHANNEL_ID)
        if not log_channel:
            return

        lines = [f"Transcript του καναλιού #{channel.name} (ID: {channel.id})",
                 f"Κλείστηκε από: {closer} ({closer.id})",
                 "=" * 60, ""]

        async for message in channel.history(limit=None, oldest_first=True):
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            content = message.content or "*(χωρίς κείμενο)*"
            lines.append(f"[{timestamp}] {message.author} ({message.author.id}): {content}")
            for attachment in message.attachments:
                lines.append(f"    📎 Συνημμένο: {attachment.url}")

        transcript_text = "\n".join(lines)
        file = discord.File(io.BytesIO(transcript_text.encode("utf-8")), filename=f"{channel.name}.txt")

        embed = discord.Embed(
            title="📄 Ticket Έκλεισε",
            description=f"**Κανάλι:** #{channel.name}\n**Έκλεισε από:** {closer.mention}",
            color=discord.Color.dark_grey(),
        )
        try:
            await log_channel.send(embed=embed, file=file)
        except discord.Forbidden:
            pass

    @staticmethod
    def _get_author_id(channel: discord.TextChannel) -> int | None:
        if not channel.topic:
            return None
        match = re.search(r"ID:\s*(\d+)", channel.topic)
        return int(match.group(1)) if match else None


class Tickets(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(TicketPanelView())
        self.bot.add_view(CloseTicketView())

    @commands.command(
        name="ticket-panel",
        help='Στέλνει το panel tickets (με dropdown κατηγοριών, logo & banner του server) σε αυτό το κανάλι. '
             'Χρήση: !ticket-panel ["Τίτλος"] ["Περιγραφή"]',
    )
    @commands.has_permissions(manage_channels=True)
    async def ticket_panel(self, ctx: commands.Context, title: str = "🎫 Support Tickets",
                            description: str = "Επίλεξε κατηγορία από το μενού παρακάτω για να ανοίξεις ένα ticket."):
        guild = ctx.guild
        embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())

        # Λογότυπο (icon) του server -> μικρή εικόνα πάνω δεξιά
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # Banner του server -> μεγάλη εικόνα κάτω από το κείμενο.
        # ΣΗΜΕΙΩΣΗ: το banner υπάρχει μόνο αν ο server έχει αρκετό Boost Level (συνήθως Level 2+)
        # ή αν έχει ενεργοποιηθεί το community feature. Αν δεν υπάρχει, απλά παραλείπεται.
        if guild.banner:
            embed.set_image(url=guild.banner.url)

        embed.set_footer(text=guild.name, icon_url=guild.icon.url if guild.icon else None)

        await ctx.send(embed=embed, view=TicketPanelView())
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("Χρειάζεσαι δικαίωμα Manage Channels.")
        elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.NotFound):
            # Το μήνυμα της εντολής είχε ήδη διαγραφεί όταν προσπαθήσαμε να το καθαρίσουμε — αγνόησέ το.
            pass
        else:
            await ctx.send(f"Σφάλμα: {error}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))