import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_pool

class Lois(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="loi-creer", description="📝 Créer une loi pour le serveur (Admin)")
    @app_commands.describe(nom="Nom de la loi", description="Description", punition="Punition prévue", penalite="Points de rep perdus")
    @app_commands.checks.has_permissions(administrator=True)
    async def create_law(self, interaction: discord.Interaction, nom: str, description: str, punition: str = "Aucune", penalite: int = 10):
        pool = await get_pool()
        async with pool.acquire() as conn:
            law = await conn.fetchrow("""
                INSERT INTO laws (guild_id, name, description, punishment, rep_penalty, created_by)
                VALUES ($1, $2, $3, $4, $5, $6) RETURNING id
            """, interaction.guild.id, nom, description, punition, penalite, interaction.user.id)

        embed = discord.Embed(
            title="📝 Nouvelle loi créée !",
            color=0x5865F2
        )
        embed.add_field(name="📌 Nom", value=nom, inline=True)
        embed.add_field(name="🆔 ID", value=f"#{law['id']}", inline=True)
        embed.add_field(name="📋 Description", value=description, inline=False)
        embed.add_field(name="⚖️ Punition", value=punition, inline=True)
        embed.add_field(name="📉 Pénalité rep", value=f"-{penalite}", inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="lois", description="📚 Voir toutes les lois du serveur")
    async def list_laws(self, interaction: discord.Interaction):
        pool = await get_pool()
        async with pool.acquire() as conn:
            laws = await conn.fetch(
                "SELECT * FROM laws WHERE guild_id=$1 ORDER BY id",
                interaction.guild.id
            )

        if not laws:
            await interaction.response.send_message("📚 Aucune loi n'a encore été créée ! Un admin peut utiliser `/loi-creer`")
            return

        embed = discord.Embed(
            title=f"📚 Lois de {interaction.guild.name}",
            description=f"**{len(laws)} loi(s) en vigueur**",
            color=0x5865F2
        )

        for law in laws:
            embed.add_field(
                name=f"#{law['id']} — {law['name']}",
                value=f"{law['description']}\n⚖️ {law['punishment']} | 📉 -{law['rep_penalty']} rep",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="loi-supprimer", description="🗑️ Supprimer une loi (Admin)")
    @app_commands.describe(id="L'ID de la loi à supprimer")
    @app_commands.checks.has_permissions(administrator=True)
    async def delete_law(self, interaction: discord.Interaction, id: int):
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM laws WHERE id=$1 AND guild_id=$2",
                id, interaction.guild.id
            )

        if result == "DELETE 1":
            await interaction.response.send_message(f"✅ Loi #{id} supprimée !")
        else:
            await interaction.response.send_message("❌ Loi introuvable.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Lois(bot))
