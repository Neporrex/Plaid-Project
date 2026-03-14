import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_pool

RANKS = [
    (500, "👑 Légende"),
    (300, "⚔️ Chevalier"),
    (200, "🛡️ Gardien"),
    (100, "⚖️ Citoyen"),
    (50,  "🧑 Lambda"),
    (0,   "⛓️ Banni"),
]

def get_rank(rep):
    for threshold, name in RANKS:
        if rep >= threshold:
            return name
    return "⛓️ Banni"

def rep_bar(rep, max_rep=500):
    filled = round((max(0, min(rep, max_rep)) / max_rep) * 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"`{bar}` {rep}"

MEDALS = ["🥇", "🥈", "🥉"]

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="classement", description="📜 Voir le classement du serveur")
    @app_commands.describe(type="Type de classement")
    @app_commands.choices(type=[
        app_commands.Choice(name="👑 Meilleure réputation", value="best"),
        app_commands.Choice(name="💀 Pire réputation",     value="worst"),
        app_commands.Choice(name="⚖️ Plus jugés",           value="trials"),
        app_commands.Choice(name="🪙 Plus riches",          value="gold"),
    ])
    async def classement(self, interaction: discord.Interaction, type: str = "best"):
        await interaction.response.defer()
        pool = await get_pool()

        async with pool.acquire() as conn:
            if type == "best":
                rows = await conn.fetch("SELECT * FROM users WHERE guild_id=$1 ORDER BY reputation DESC LIMIT 10", interaction.guild.id)
                title = "👑 Meilleurs Citoyens du Royaume"
                color = 0xFFD700
            elif type == "worst":
                rows = await conn.fetch("SELECT * FROM users WHERE guild_id=$1 ORDER BY reputation ASC LIMIT 10", interaction.guild.id)
                title = "💀 Pires Criminels du Royaume"
                color = 0x8B0000
            elif type == "gold":
                rows = await conn.fetch("SELECT * FROM users WHERE guild_id=$1 ORDER BY gold DESC LIMIT 10", interaction.guild.id)
                title = "🪙 Les Plus Fortunés du Royaume"
                color = 0xC8A96E
            else:
                rows = await conn.fetch("SELECT * FROM users WHERE guild_id=$1 ORDER BY total_trials DESC LIMIT 10", interaction.guild.id)
                title = "⚖️ Les Plus Jugés du Royaume"
                color = 0x5865F2

        if not rows:
            return await interaction.followup.send("📜 *Aucune âme n'a encore été jugée dans ce royaume...*")

        embed = discord.Embed(title=title, color=color)
        embed.description = "*Les parchemins du destin révèlent les élus...*\n\n"

        lines = []
        for i, row in enumerate(rows):
            try:
                member = await interaction.guild.fetch_member(row['discord_id'])
                name = member.display_name
            except:
                name = f"Âme#{str(row['discord_id'])[-4:]}"

            medal = MEDALS[i] if i < 3 else f"**#{i+1}**"
            rank = get_rank(row['reputation'])

            if type == "gold":
                stat = f"🪙 {row['gold']} or"
            elif type == "trials":
                stat = f"⚖️ {row['total_trials']} procès"
            else:
                stat = rep_bar(row['reputation'])

            lines.append(f"{medal} **{name}** — {rank}\n　　{stat} • 🏆 {row['wins']}V/{row['losses']}D")

        embed.description += "\n\n".join(lines)
        embed.set_footer(text=f"⚖️ PLAID • {interaction.guild.name}")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)

        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
