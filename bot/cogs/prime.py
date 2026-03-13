import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_pool

class Prime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="prime", description="💰 Mettre une prime sur la tête de quelqu'un")
    @app_commands.describe(membre="La cible", montant="Montant en or", raison="Raison de la prime")
    async def prime(self, interaction: discord.Interaction, membre: discord.Member, montant: int, raison: str = "Non précisée"):
        if montant <= 0:
            return await interaction.response.send_message("❌ Le montant doit être positif !", ephemeral=True)
        if membre.id == interaction.user.id:
            return await interaction.response.send_message("❌ Vous ne pouvez pas vous mettre une prime !", ephemeral=True)

        pool = await get_pool()
        async with pool.acquire() as conn:
            issuer = await conn.fetchrow(
                "SELECT gold FROM users WHERE guild_id=$1 AND discord_id=$2",
                interaction.guild.id, interaction.user.id
            )
            if not issuer or issuer['gold'] < montant:
                return await interaction.response.send_message(f"❌ Pas assez d'or ! Vous avez {issuer['gold'] if issuer else 0} 🪙", ephemeral=True)

            await conn.execute(
                "UPDATE users SET gold=gold-$1 WHERE guild_id=$2 AND discord_id=$3",
                montant, interaction.guild.id, interaction.user.id
            )
            await conn.execute(
                "INSERT INTO bounties (guild_id, target_id, issuer_id, amount, reason) VALUES ($1,$2,$3,$4,$5)",
                interaction.guild.id, membre.id, interaction.user.id, montant, raison
            )

        embed = discord.Embed(
            title="💰 AVIS DE RECHERCHE",
            description=f"*Un parchemin est cloué sur le tableau de la taverne...*",
            color=0xE74C3C
        )
        embed.add_field(name="🎯 Cible", value=membre.mention, inline=True)
        embed.add_field(name="💰 Prime", value=f"{montant} 🪙", inline=True)
        embed.add_field(name="📋 Raison", value=raison, inline=False)
        embed.add_field(name="⚠️ Commanditaire", value=interaction.user.mention, inline=True)
        embed.set_footer(text="Que les chasseurs de primes soient prévenus !")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="primes", description="📋 Voir les primes actives du serveur")
    async def primes(self, interaction: discord.Interaction):
        pool = await get_pool()
        async with pool.acquire() as conn:
            bounties = await conn.fetch(
                "SELECT * FROM bounties WHERE guild_id=$1 AND active=TRUE ORDER BY amount DESC LIMIT 10",
                interaction.guild.id
            )
        if not bounties:
            return await interaction.response.send_message("📋 Aucune prime active !")

        embed = discord.Embed(title="💰 PRIMES ACTIVES", color=0xE74C3C)
        for b in bounties:
            try:
                target = await interaction.guild.fetch_member(b['target_id'])
                name = target.display_name
            except:
                name = f"#{b['target_id']}"
            embed.add_field(
                name=f"🎯 {name}",
                value=f"💰 {b['amount']} or\n📋 {b['reason']}",
                inline=True
            )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Prime(bot))
