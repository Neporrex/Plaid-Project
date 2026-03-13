import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_pool

class Rehabilitation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="rehabilitation", description="✨ Réhabiliter un membre (Admin) — efface son casier")
    @app_commands.describe(membre="Le membre à réhabiliter", raison="Raison de la réhabilitation")
    @app_commands.checks.has_permissions(administrator=True)
    async def rehabilitation(self, interaction: discord.Interaction, membre: discord.Member, raison: str = "Décision du tribunal"):
        pool = await get_pool()
        async with pool.acquire() as conn:
            deleted = await conn.execute(
                "DELETE FROM casier WHERE guild_id=$1 AND discord_id=$2",
                interaction.guild.id, membre.id
            )
            await conn.execute(
                "UPDATE users SET reputation=100 WHERE guild_id=$1 AND discord_id=$2",
                interaction.guild.id, membre.id
            )

        embed = discord.Embed(
            title="✨ RÉHABILITATION OFFICIELLE",
            description=f"*Par décret du tribunal, {membre.mention} est déclaré·e réhabilité·e.*",
            color=0xF1C40F
        )
        embed.add_field(name="📋 Raison", value=raison, inline=False)
        embed.add_field(name="📊 Réputation restaurée", value="100 ⚖️", inline=True)
        embed.add_field(name="🗑️ Casier", value="Effacé", inline=True)
        embed.set_footer(text=f"Prononcé par {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Rehabilitation(bot))
