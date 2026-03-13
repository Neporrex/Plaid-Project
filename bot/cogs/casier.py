import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_pool

class Casier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="casier", description="📜 Voir le casier judiciaire complet")
    @app_commands.describe(membre="Le membre dont tu veux voir le casier")
    async def casier(self, interaction: discord.Interaction, membre: discord.Member = None):
        membre = membre or interaction.user
        pool = await get_pool()

        async with pool.acquire() as conn:
            cases = await conn.fetch("""
                SELECT c.*, t.accuser_id, t.verdict 
                FROM casier c
                LEFT JOIN trials t ON c.trial_id = t.id
                WHERE c.discord_id=$1 AND c.guild_id=$2
                ORDER BY c.created_at DESC
            """, membre.id, interaction.guild.id)

        if not cases:
            embed = discord.Embed(
                title=f"📜 Casier de {membre.display_name}",
                description="✨ Ce citoyen a un casier vierge !",
                color=0x00FF00
            )
            embed.set_thumbnail(url=membre.display_avatar.url)
            await interaction.response.send_message(embed=embed)
            return

        embed = discord.Embed(
            title=f"📜 Casier de {membre.display_name}",
            description=f"**{len(cases)} infraction(s) au total**",
            color=0xFF0000
        )
        embed.set_thumbnail(url=membre.display_avatar.url)

        for i, case in enumerate(cases[:10], 1):
            accuser = await interaction.guild.fetch_member(case['accuser_id']) if case['accuser_id'] else None
            accuser_name = accuser.display_name if accuser else "Inconnu"
            
            embed.add_field(
                name=f"#{i} — Procès #{case['trial_id']}",
                value=f"**Offense:** {case['offense']}\n**Accusé par:** {accuser_name}\n**Verdict:** {case['verdict']}\n**Rep:** {case['rep_change']:+d}",
                inline=False
            )

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Casier(bot))
