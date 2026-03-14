import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from utils.db import init_db

load_dotenv()

class PlaidBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await init_db()
        cogs = [
            "cogs.tribunal",
            "cogs.reputation",
            "cogs.casier",
            "cogs.lois",
            "cogs.leaderboard",
            "cogs.prime",
            "cogs.guildes",
            "cogs.quetes",
            "cogs.serment",
            "cogs.rehabilitation",
            "cogs.admin",
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                print(f"✅ {cog} chargé")
            except Exception as e:
                print(f"❌ Erreur {cog}: {e}")
        await self.tree.sync()
        print("✅ Commandes synchronisées")

    async def on_ready(self):
        print(f"⚖️ PLAID connecté en tant que {self.user}")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="⚖️ La justice"
            )
        )

bot = PlaidBot()
bot.run(os.getenv("DISCORD_TOKEN"))
