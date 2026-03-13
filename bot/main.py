import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv

load_dotenv()

class PlaidBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.load_extension("cogs.tribunal")
        await self.load_extension("cogs.reputation")
        await self.load_extension("cogs.casier")
        await self.load_extension("cogs.lois")
        await self.load_extension("cogs.leaderboard")
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
