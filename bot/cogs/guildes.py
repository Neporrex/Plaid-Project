import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_pool
from typing import Optional

class Guildes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    guilde_group = app_commands.Group(name="guilde", description="⚔️ Système de guildes")

    @guilde_group.command(name="creer", description="⚔️ Fonder une nouvelle guilde")
    @app_commands.describe(nom="Nom de votre guilde", description="Description", embleme="Emoji emblème (ex: 🐉)")
    async def guilde_creer(self, interaction: discord.Interaction, nom: str, description: str = "", embleme: str = "⚔️"):
        pool = await get_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT id FROM guilds_rpg WHERE guild_id=$1 AND name=$2",
                interaction.guild.id, nom
            )
            if existing:
                return await interaction.response.send_message("❌ Une guilde avec ce nom existe déjà !", ephemeral=True)

            # Vérifier si déjà dans une guilde
            user = await conn.fetchrow(
                "SELECT guild_name FROM users WHERE guild_id=$1 AND discord_id=$2",
                interaction.guild.id, interaction.user.id
            )
            if user and user['guild_name']:
                return await interaction.response.send_message(f"❌ Vous êtes déjà dans la guilde **{user['guild_name']}** !", ephemeral=True)

            await conn.execute(
                """INSERT INTO guilds_rpg (guild_id, name, description, leader_id, members, emblem)
                   VALUES ($1,$2,$3,$4,$5,$6)""",
                interaction.guild.id, nom, description, interaction.user.id, [interaction.user.id], embleme
            )
            await conn.execute(
                "INSERT INTO users (guild_id, discord_id) VALUES ($1,$2) ON CONFLICT DO NOTHING",
                interaction.guild.id, interaction.user.id
            )
            await conn.execute(
                "UPDATE users SET guild_name=$1 WHERE guild_id=$2 AND discord_id=$3",
                nom, interaction.guild.id, interaction.user.id
            )

        embed = discord.Embed(
            title=f"{embleme} GUILDE FONDÉE : {nom}",
            description=f"*Un nouveau clan s'élève dans le royaume !*\n\n{description}",
            color=0xC8A96E
        )
        embed.add_field(name="👑 Fondateur", value=interaction.user.mention)
        embed.set_footer(text="Utilisez /guilde rejoindre pour recruter des membres")
        await interaction.response.send_message(embed=embed)

    @guilde_group.command(name="rejoindre", description="🤝 Rejoindre une guilde existante")
    @app_commands.describe(nom="Nom de la guilde à rejoindre")
    async def guilde_rejoindre(self, interaction: discord.Interaction, nom: str):
        pool = await get_pool()
        async with pool.acquire() as conn:
            guilde = await conn.fetchrow(
                "SELECT * FROM guilds_rpg WHERE guild_id=$1 AND name=$2",
                interaction.guild.id, nom
            )
            if not guilde:
                return await interaction.response.send_message("❌ Guilde introuvable !", ephemeral=True)

            user = await conn.fetchrow(
                "SELECT guild_name FROM users WHERE guild_id=$1 AND discord_id=$2",
                interaction.guild.id, interaction.user.id
            )
            if user and user['guild_name']:
                return await interaction.response.send_message(f"❌ Quittez votre guilde actuelle d'abord !", ephemeral=True)

            await conn.execute(
                "UPDATE guilds_rpg SET members=array_append(members,$1) WHERE guild_id=$2 AND name=$3",
                interaction.user.id, interaction.guild.id, nom
            )
            await conn.execute(
                "INSERT INTO users (guild_id, discord_id) VALUES ($1,$2) ON CONFLICT DO NOTHING",
                interaction.guild.id, interaction.user.id
            )
            await conn.execute(
                "UPDATE users SET guild_name=$1 WHERE guild_id=$2 AND discord_id=$3",
                nom, interaction.guild.id, interaction.user.id
            )

        embed = discord.Embed(
            title=f"{guilde['emblem']} NOUVEL ADHÉRENT",
            description=f"{interaction.user.mention} a rejoint la guilde **{nom}** !",
            color=0x2ECC71
        )
        await interaction.response.send_message(embed=embed)

    @guilde_group.command(name="quitter", description="🚪 Quitter votre guilde actuelle")
    async def guilde_quitter(self, interaction: discord.Interaction):
        pool = await get_pool()
        async with pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT guild_name FROM users WHERE guild_id=$1 AND discord_id=$2",
                interaction.guild.id, interaction.user.id
            )
            if not user or not user['guild_name']:
                return await interaction.response.send_message("❌ Vous n'êtes dans aucune guilde !", ephemeral=True)

            guild_name = user['guild_name']
            guilde = await conn.fetchrow(
                "SELECT * FROM guilds_rpg WHERE guild_id=$1 AND name=$2",
                interaction.guild.id, guild_name
            )
            if guilde and guilde['leader_id'] == interaction.user.id:
                return await interaction.response.send_message("❌ Vous êtes le chef ! Dissoudre avec `/guilde dissoudre`.", ephemeral=True)

            await conn.execute(
                "UPDATE guilds_rpg SET members=array_remove(members,$1) WHERE guild_id=$2 AND name=$3",
                interaction.user.id, interaction.guild.id, guild_name
            )
            await conn.execute(
                "UPDATE users SET guild_name=NULL WHERE guild_id=$1 AND discord_id=$2",
                interaction.guild.id, interaction.user.id
            )

        await interaction.response.send_message(f"🚪 Vous avez quitté la guilde **{guild_name}**.", ephemeral=True)

    @guilde_group.command(name="info", description="📋 Voir les infos d'une guilde")
    @app_commands.describe(nom="Nom de la guilde")
    async def guilde_info(self, interaction: discord.Interaction, nom: str):
        pool = await get_pool()
        async with pool.acquire() as conn:
            guilde = await conn.fetchrow(
                "SELECT * FROM guilds_rpg WHERE guild_id=$1 AND name=$2",
                interaction.guild.id, nom
            )
        if not guilde:
            return await interaction.response.send_message("❌ Guilde introuvable !", ephemeral=True)

        embed = discord.Embed(
            title=f"{guilde['emblem']} {guilde['name']}",
            description=guilde['description'] or "*Aucune description.*",
            color=0xC8A96E
        )
        try:
            leader = await interaction.guild.fetch_member(guilde['leader_id'])
            embed.add_field(name="👑 Chef", value=leader.mention, inline=True)
        except:
            embed.add_field(name="👑 Chef", value=f"#{guilde['leader_id']}", inline=True)

        embed.add_field(name="⚔️ Membres", value=str(len(guilde['members'])), inline=True)
        embed.add_field(name="📅 Fondée le", value=guilde['created_at'].strftime("%d/%m/%Y"), inline=True)
        await interaction.response.send_message(embed=embed)

    @guilde_group.command(name="liste", description="📜 Voir toutes les guildes du serveur")
    async def guilde_liste(self, interaction: discord.Interaction):
        pool = await get_pool()
        async with pool.acquire() as conn:
            guildes = await conn.fetch(
                "SELECT * FROM guilds_rpg WHERE guild_id=$1 ORDER BY array_length(members,1) DESC",
                interaction.guild.id
            )
        if not guildes:
            return await interaction.response.send_message("📜 Aucune guilde dans ce royaume !")

        embed = discord.Embed(title="⚔️ GUILDES DU ROYAUME", color=0xC8A96E)
        for g in guildes[:10]:
            embed.add_field(
                name=f"{g['emblem']} {g['name']}",
                value=f"👥 {len(g['members'])} membres\n{g['description'][:60] if g['description'] else '—'}",
                inline=True
            )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Guildes(bot))
