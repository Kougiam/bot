import discord
from discord.ext import commands

class SayCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="say")
    @commands.has_permissions(administrator=True) 
    async def say(self, ctx, *, message: str):
        
        # 1. Διαγραφή του αρχικού μηνύματος του χρήστη (ώστε να μη φαίνεται το !say)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass # Αν το bot δεν έχει άδεια διαγραφής, απλά το προσπερνάει

        # 2. Έλεγχος αν ο server έχει logo (icon)
        icon_url = ctx.guild.icon.url if ctx.guild.icon else None

        # 3. Δημιουργία του Embed
        embed = discord.Embed(
            description=message, 
            color=discord.Color.blue() # Μπορείς να αλλάξεις το χρώμα του πλαισίου
        )
        
        # Αν υπάρχει logo, το βάζουμε ως "thumbnail" πάνω δεξιά στο μήνυμα
        if icon_url:
            embed.set_thumbnail(url=icon_url),
        #   embed.set_image(url=icon_url)
            
            # ΕΝΑΛΛΑΚΤΙΚΑ: Αν θέλεις το logo να είναι μεγάλο στο κάτω μέρος, σβήσε την από πάνω γραμμή και βάλε:
            # embed.set_image(url=icon_url)

        # 4. Αποστολή του Embed
        await ctx.send(embed=embed)

# Συνάρτηση φόρτωσης του Cog
async def setup(bot):
    await bot.add_cog(SayCommand(bot))