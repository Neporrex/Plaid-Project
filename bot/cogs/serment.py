import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_pool

class Serment(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="serment", description="🤝 Prêter serment solennel devant le tribunal")
    @app_commands.describe(serment="Votre serment (public, gravé à jamais)")
    async def serment(self, interaction: discord.Interaction, serment: str):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO oaths (guild_id, discord_id, oath_text) VALUES ($1,$2,$3)",
                interaction.guild.id, interaction.user.id, serment
            )

        embed = discord.Embed(
            title="🤝 SERMENT SOLENNEL",
            description=f"*Sous le regard des dieux et des hommes, {interaction.user.mention} prononce ces mots :*",
            color=0x3498DB
        )
        embed.add_field(name="📜 Serment", value=f"*« {serment} »*", inline=False)
        embed.set_footer(text="Ce serment est gravé dans les archives du royaume pour l'éternité.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serments", description="📜 Voir les serments d'un membre")
    @app_commands.describe(membre="Le membre dont voir les serments")
    async def serments(self, interaction: discord.Interaction, membre: discord.Member = None):
        target = membre or interaction.user
        pool = await get_pool()
        async with pool.acquire() as conn:
            oaths = await conn.fetch(
                "SELECT * FROM oaths WHERE guild_id=$1 AND discord_id=$2 ORDER BY created_at DESC LIMIT 5",
                interaction.guild.id, target.id
            )
        if not oaths:
            return await interaction.response.send_message(f"📜 {target.display_name} n'a prononcé aucun serment.", ephemeral=True)

        embed = discord.Embed(
            title=f"📜 SERMENTS DE {target.display_name.upper()}",
            color=0x3498DB
        )
        for o in oaths:
            embed.add_field(
                name=o['created_at'].strftime("%d/%m/%Y"),
                value=f"*« {o['oath_text']} »*",
                inline=False
            )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Serment(bot))
