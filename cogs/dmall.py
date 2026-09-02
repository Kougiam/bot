import asyncio
import discord
from discord.ext import commands, tasks

class MassDmSender(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.members_queue = []  # Λίστα που θα κρατάει τα μέλη που περιμένουν
        self.dm_message = ""     # Το μήνυμα που θα σταλεί

    # Το loop που εκτελείται κάθε 1 λεπτό
    @tasks.loop(minutes=1)
    async def mass_dm_loop(self):
        # Αν η λίστα άδειασε, σταματάμε το loop
        if not self.members_queue:
            print("Η αποστολή ολοκληρώθηκε σε όλα τα μέλη!")
            self.mass_dm_loop.stop()
            return

        # Παίρνουμε (και αφαιρούμε από τη λίστα) τον πρώτο χρήστη της ουράς
        member = self.members_queue.pop(0)

        try:
            await member.send(self.dm_message)
            print(f"Στάλθηκε DM στον/στην {member.name}. Απομένουν: {len(self.members_queue)}")
            
        except discord.Forbidden:
            print(f"Ο/Η {member.name} έχει κλειστά τα DMs. Απομένουν: {len(self.members_queue)}")
            
        except discord.HTTPException as e:
            # Έλεγχος για Rate Limit (Κωδικός 429)
            if e.status == 429:
                # Διαβάζουμε πόσο χρόνο (σε δευτερόλεπτα) ζητάει το Discord να περιμένουμε
                retry_after = float(e.response.headers.get("Retry-After", 60))
                print(f"⚠️ RATE LIMIT! Παύση για {retry_after} δευτερόλεπτα...")
                
                # Βάζουμε τον χρήστη ξανά στην αρχή της λίστας επειδή δεν πήρε το μήνυμα
                self.members_queue.insert(0, member)
                
                # Κάνουμε παύση για τον απαραίτητο χρόνο
                await asyncio.sleep(retry_after)
            else:
                print(f"Άγνωστο σφάλμα HTTP με τον/την {member.name}: {e}")
                
        except Exception as e:
            print(f"Σφάλμα κατά την αποστολή στον/στην {member.name}: {e}")

    # Η εντολή για να ξεκινήσει η διαδικασία (!dm <μήνυμα>)
    @commands.command(name="dm")
    @commands.has_permissions(administrator=True) # Μόνο admins μπορούν να το τρέξουν
    async def dm(self, ctx, *, message: str):
        if self.mass_dm_loop.is_running():
            await ctx.send("⚠️ Η διαδικασία τρέχει ήδη! Σταμάτα την πρώτα με !stopdm.")
            return

        self.dm_message = message
        self.members_queue = []

        # Μαζεύουμε όλα τα μέλη του server (αγνοούμε τα άλλα bots)
        for member in ctx.guild.members:
            if not member.bot:
                self.members_queue.append(member)

        if not self.members_queue:
            await ctx.send("Δεν βρέθηκαν κανονικά μέλη για αποστολή.")
            return

        # Υπολογισμός του χρόνου (προαιρετικό, για να ξέρεις πόσο θα πάρει)
        total_minutes = len(self.members_queue) * 1
        hours = total_minutes // 60
        mins = total_minutes % 60

        await ctx.send(
            f"✅ Ξεκινάει η αποστολή σε **{len(self.members_queue)} μέλη**.\n"
            f"⏳ Μετράω users.\n"
            f"⏱️ Εκτιμώμενος συνολικός χρόνος: **{hours} ώρες και {mins} λεπτά**."
        )
        
        self.mass_dm_loop.start()

    # Η εντολή για άμεσο τερματισμό (!stopdm)
    @commands.command(name="stopdm")
    @commands.has_permissions(administrator=True)
    async def stopdm(self, ctx):
        if self.mass_dm_loop.is_running():
            self.mass_dm_loop.stop()
            self.members_queue.clear()
            await ctx.send("🛑 Η μαζική αποστολή διακόπηκε με επιτυχία.")
        else:
            await ctx.send("Δεν τρέχει κάποια μαζική αποστολή αυτή τη στιγμή.")

# Φόρτωση του Cog
async def setup(bot):
    await bot.add_cog(MassDmSender(bot))