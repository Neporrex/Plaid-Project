import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_pool

class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="classement", description="🏆 Voir le classement du serveur")
    @app_commands.describe(type="Type de classement")
    @app_commands.choices(type=[
        app_commands.Choice(name="🏅 Meilleure réputation", value="best"),
        app_commands.Choice(name="💀 Pire réputation", value="worst"),
        app_commands.Choice(name="⚖️ Plus jugés", value="trials"),
    ])
    async def classement(self, interaction: discord.Interaction, type: str = "best"):
        pool = await get_pool()

        async with pool.acquire() as conn:
            if type == "best":
                rows = await conn.fetch("""
                    SELECT * FROM users WHERE guild_id=$1
                    ORDER BY reputation DESC LIMIT 10
                """, interaction.guild.id)
                title = "🏅 Meilleurs citoyens"
            elif type == "worst":
                rows = await conn.fetch("""
                    SELECT * FROM users WHERE guild_id=$1
                    ORDER BY reputation ASC LIMIT 10
                """, interaction.guild.id)
                title = "💀 Pires criminels"
            else:
                rows = await conn.fetch("""
                    SELECT * FROM users WHERE guild_id=$1
                    ORDER BY total_trials DESC LIMIT 10
                """, interaction.guild.id)
                title = "⚖️ Les plus jugés"

        if not rows:
            await interaction.response.send_message("📊 Aucune donnée pour le moment !")
            return

        embed = discord.Embed(title=title, color=0xFFD700)
        
        medals = ["🥇", "🥈", "🥉"]
        description = ""
        
        for i, row in enumerate(rows):
            try:
                member = await interaction.guild.fetch_member(row['discord_id'])
                name = member.display_name
            except:
                name = f"User#{row['discord_id']}"
            
            medal = medals[i] if i < 3 else f"**{i+1}.**"
            description += f"{medal} {name} — 📊 {row['reputation']} rep | ⚖️ {row['total_trials']} procès\n"

        embed.description = description
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
