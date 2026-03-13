import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_pool

class Casier(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="casier", description="📋 Voir le casier judiciaire d'un membre")
    @app_commands.describe(membre="Le membre à consulter (vous par défaut)")
    async def casier(self, interaction: discord.Interaction, membre: discord.Member = None):
        target = membre or interaction.user
        pool = await get_pool()
        async with pool.acquire() as conn:
            records = await conn.fetch(
                "SELECT * FROM casier WHERE guild_id=$1 AND discord_id=$2 ORDER BY created_at DESC LIMIT 10",
                interaction.guild.id, target.id
            )

        if not records:
            embed = discord.Embed(
                title=f"📋 CASIER DE {target.display_name.upper()}",
                description="*Ce citoyen possède un casier vierge. La justice lui sourit.*",
                color=0x2ECC71
            )
            return await interaction.response.send_message(embed=embed)

        embed = discord.Embed(
            title=f"📋 CASIER JUDICIAIRE — {target.display_name.upper()}",
            description=f"*{len(records)} infraction(s) enregistrée(s)*",
            color=0xE74C3C
        )
        for r in records:
            verdict_emoji = "⚔️" if r['verdict'] == 'coupable' else "🕊️"
            embed.add_field(
                name=f"{verdict_emoji} {r['created_at'].strftime('%d/%m/%Y')} — {r['verdict'].upper() if r['verdict'] else 'En cours'}",
                value=f"*{r['infraction']}*",
                inline=False
            )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Casier(bot))
