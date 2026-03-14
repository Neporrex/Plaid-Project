import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_pool
from typing import Optional

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    admin_group = app_commands.Group(name="admin", description="🔧 Commandes d'administration PLAID")

    def is_admin(self, interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_guild

    # ── RÉPUTATION ────────────────────────────────────────────────────
    @admin_group.command(name="rep-add", description="➕ Ajouter de la réputation à un membre")
    @app_commands.describe(membre="La cible", montant="Montant à ajouter", raison="Raison")
    @app_commands.checks.has_permissions(administrator=True)
    async def rep_add(self, interaction: discord.Interaction, membre: discord.Member, montant: int, raison: str = "Décision admin"):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO users (guild_id, discord_id) VALUES ($1,$2) ON CONFLICT DO NOTHING", interaction.guild.id, membre.id)
            new_rep = await conn.fetchval(
                "UPDATE users SET reputation=reputation+$1 WHERE guild_id=$2 AND discord_id=$3 RETURNING reputation",
                montant, interaction.guild.id, membre.id
            )
        embed = discord.Embed(title="➕ Réputation accordée", color=0x2ECC71)
        embed.add_field(name="Membre", value=membre.mention, inline=True)
        embed.add_field(name="Ajout", value=f"+{montant} ⚖️", inline=True)
        embed.add_field(name="Total", value=f"{new_rep} ⚖️", inline=True)
        embed.add_field(name="Raison", value=raison, inline=False)
        embed.set_footer(text=f"Par {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @admin_group.command(name="rep-remove", description="➖ Retirer de la réputation à un membre")
    @app_commands.describe(membre="La cible", montant="Montant à retirer", raison="Raison")
    @app_commands.checks.has_permissions(administrator=True)
    async def rep_remove(self, interaction: discord.Interaction, membre: discord.Member, montant: int, raison: str = "Décision admin"):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO users (guild_id, discord_id) VALUES ($1,$2) ON CONFLICT DO NOTHING", interaction.guild.id, membre.id)
            new_rep = await conn.fetchval(
                "UPDATE users SET reputation=reputation-$1 WHERE guild_id=$2 AND discord_id=$3 RETURNING reputation",
                montant, interaction.guild.id, membre.id
            )
        embed = discord.Embed(title="➖ Réputation retirée", color=0xE74C3C)
        embed.add_field(name="Membre", value=membre.mention, inline=True)
        embed.add_field(name="Retrait", value=f"-{montant} ⚖️", inline=True)
        embed.add_field(name="Total", value=f"{new_rep} ⚖️", inline=True)
        embed.add_field(name="Raison", value=raison, inline=False)
        embed.set_footer(text=f"Par {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    # ── OR ────────────────────────────────────────────────────────────
    @admin_group.command(name="or-add", description="🪙 Donner de l'or à un membre")
    @app_commands.describe(membre="La cible", montant="Montant d'or")
    @app_commands.checks.has_permissions(administrator=True)
    async def or_add(self, interaction: discord.Interaction, membre: discord.Member, montant: int):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO users (guild_id, discord_id) VALUES ($1,$2) ON CONFLICT DO NOTHING", interaction.guild.id, membre.id)
            new_gold = await conn.fetchval(
                "UPDATE users SET gold=gold+$1 WHERE guild_id=$2 AND discord_id=$3 RETURNING gold",
                montant, interaction.guild.id, membre.id
            )
        await interaction.response.send_message(
            f"🪙 **{montant} or** accordé à {membre.mention} ! Total : **{new_gold} 🪙**"
        )

    @admin_group.command(name="or-remove", description="🪙 Retirer de l'or à un membre")
    @app_commands.checks.has_permissions(administrator=True)
    async def or_remove(self, interaction: discord.Interaction, membre: discord.Member, montant: int):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO users (guild_id, discord_id) VALUES ($1,$2) ON CONFLICT DO NOTHING", interaction.guild.id, membre.id)
            new_gold = await conn.fetchval(
                "UPDATE users SET gold=GREATEST(0, gold-$1) WHERE guild_id=$2 AND discord_id=$3 RETURNING gold",
                montant, interaction.guild.id, membre.id
            )
        await interaction.response.send_message(
            f"🪙 **{montant} or** retiré à {membre.mention}. Reste : **{new_gold} 🪙**"
        )

    # ── BADGE ─────────────────────────────────────────────────────────
    @admin_group.command(name="badge-add", description="🏅 Ajouter un badge à un membre")
    @app_commands.describe(membre="La cible", badge="L'emoji badge (ex: 🗡️)")
    @app_commands.checks.has_permissions(administrator=True)
    async def badge_add(self, interaction: discord.Interaction, membre: discord.Member, badge: str):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO users (guild_id, discord_id) VALUES ($1,$2) ON CONFLICT DO NOTHING", interaction.guild.id, membre.id)
            await conn.execute(
                "UPDATE users SET badges=array_append(badges,$1) WHERE guild_id=$2 AND discord_id=$3",
                badge, interaction.guild.id, membre.id
            )
        await interaction.response.send_message(f"🏅 Badge **{badge}** accordé à {membre.mention} !")

    @admin_group.command(name="badge-remove", description="🗑️ Retirer un badge à un membre")
    @app_commands.checks.has_permissions(administrator=True)
    async def badge_remove(self, interaction: discord.Interaction, membre: discord.Member, badge: str):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET badges=array_remove(badges,$1) WHERE guild_id=$2 AND discord_id=$3",
                badge, interaction.guild.id, membre.id
            )
        await interaction.response.send_message(f"🗑️ Badge **{badge}** retiré à {membre.mention}.", ephemeral=True)

    # ── TITRE ─────────────────────────────────────────────────────────
    @admin_group.command(name="titre", description="✦ Définir le titre d'un membre")
    @app_commands.describe(membre="La cible", titre="Le titre à attribuer")
    @app_commands.checks.has_permissions(administrator=True)
    async def titre(self, interaction: discord.Interaction, membre: discord.Member, titre: str):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("INSERT INTO users (guild_id, discord_id) VALUES ($1,$2) ON CONFLICT DO NOTHING", interaction.guild.id, membre.id)
            await conn.execute(
                "UPDATE users SET title=$1 WHERE guild_id=$2 AND discord_id=$3",
                titre, interaction.guild.id, membre.id
            )
        await interaction.response.send_message(f"✦ Titre **{titre}** attribué à {membre.mention} !")

    # ── RESET ─────────────────────────────────────────────────────────
    @admin_group.command(name="reset-user", description="♻️ Réinitialiser un membre (stats + casier)")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_user(self, interaction: discord.Interaction, membre: discord.Member):
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET reputation=100, total_trials=0, wins=0, losses=0, gold=0, badges='{}', title='Citoyen', guild_name=NULL WHERE guild_id=$1 AND discord_id=$2",
                interaction.guild.id, membre.id
            )
            await conn.execute("DELETE FROM casier WHERE guild_id=$1 AND discord_id=$2", interaction.guild.id, membre.id)
        await interaction.response.send_message(f"♻️ {membre.mention} a été réinitialisé·e.", ephemeral=True)

    # ── PRIME FERMER ──────────────────────────────────────────────────
    @admin_group.command(name="prime-fermer", description="🔒 Fermer une prime active")
    @app_commands.describe(prime_id="ID de la prime")
    @app_commands.checks.has_permissions(administrator=True)
    async def prime_fermer(self, interaction: discord.Interaction, prime_id: int):
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE bounties SET active=FALSE WHERE id=$1 AND guild_id=$2",
                prime_id, interaction.guild.id
            )
        if result == "UPDATE 0":
            return await interaction.response.send_message("❌ Prime introuvable.", ephemeral=True)
        await interaction.response.send_message(f"🔒 Prime #{prime_id} fermée.", ephemeral=True)

    # ── SYNC ──────────────────────────────────────────────────────────
    @admin_group.command(name="sync", description="🔄 Re-synchroniser les slash commands (owner)")
    @app_commands.checks.has_permissions(administrator=True)
    async def sync(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        synced = await interaction.client.tree.sync()
        await interaction.followup.send(f"🔄 {len(synced)} commande(s) synchronisée(s).", ephemeral=True)

    # ── INFO SERVEUR ──────────────────────────────────────────────────
    @admin_group.command(name="stats", description="📊 Voir les statistiques PLAID du serveur")
    @app_commands.checks.has_permissions(administrator=True)
    async def stats(self, interaction: discord.Interaction):
        pool = await get_pool()
        async with pool.acquire() as conn:
            users    = await conn.fetchval("SELECT COUNT(*) FROM users WHERE guild_id=$1", interaction.guild.id) or 0
            trials   = await conn.fetchval("SELECT COUNT(*) FROM trials WHERE guild_id=$1", interaction.guild.id) or 0
            laws     = await conn.fetchval("SELECT COUNT(*) FROM laws WHERE guild_id=$1", interaction.guild.id) or 0
            quests   = await conn.fetchval("SELECT COUNT(*) FROM quests WHERE guild_id=$1 AND active=TRUE", interaction.guild.id) or 0
            guildes  = await conn.fetchval("SELECT COUNT(*) FROM guilds_rpg WHERE guild_id=$1", interaction.guild.id) or 0
            bounties = await conn.fetchval("SELECT COUNT(*) FROM bounties WHERE guild_id=$1 AND active=TRUE", interaction.guild.id) or 0

        embed = discord.Embed(title="📊 Stats PLAID du serveur", color=0xC8A96E)
        embed.add_field(name="👥 Citoyens", value=str(users), inline=True)
        embed.add_field(name="⚖️ Procès",   value=str(trials), inline=True)
        embed.add_field(name="📖 Lois",     value=str(laws), inline=True)
        embed.add_field(name="📜 Quêtes",   value=str(quests), inline=True)
        embed.add_field(name="⚔️ Guildes",  value=str(guildes), inline=True)
        embed.add_field(name="💰 Primes",   value=str(bounties), inline=True)
        embed.set_footer(text=interaction.guild.name)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Admin(bot))
