import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_pool
from typing import Optional

class Quetes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    quete_group = app_commands.Group(name="quete", description="📜 Système de quêtes")

    @quete_group.command(name="creer", description="📜 Créer une nouvelle quête (Admin)")
    @app_commands.describe(
        titre="Titre de la quête",
        description="Description et objectif",
        or_recompense="Or accordé à la completion",
        rep_recompense="Réputation accordée",
        badge="Badge emoji accordé (ex: 🗡️)",
        role="Rôle Discord accordé"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def quete_creer(
        self,
        interaction: discord.Interaction,
        titre: str,
        description: str,
        rep_recompense: int = 0,
        or_recompense: int = 0,
        badge: Optional[str] = None,
        role: Optional[discord.Role] = None
    ):
        pool = await get_pool()
        async with pool.acquire() as conn:
            q = await conn.fetchrow(
                """INSERT INTO quests (guild_id, title, description, reward_rep, reward_gold, reward_badge, reward_role_id, created_by)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8) RETURNING id""",
                interaction.guild.id, titre, description, rep_recompense, or_recompense,
                badge, role.id if role else None, interaction.user.id
            )

        embed = discord.Embed(
            title="📜 NOUVELLE QUÊTE AFFICHÉE !",
            description=f"*Un nouveau parchemin apparaît sur le tableau des quêtes...*",
            color=0xC8A96E
        )
        embed.add_field(name="⚔️ Titre", value=titre, inline=False)
        embed.add_field(name="📋 Objectif", value=description, inline=False)
        rewards = []
        if rep_recompense: rewards.append(f"⚖️ {rep_recompense} réputation")
        if or_recompense: rewards.append(f"🪙 {or_recompense} or")
        if badge: rewards.append(f"Badge : {badge}")
        if role: rewards.append(f"Rôle : {role.mention}")
        embed.add_field(name="🎁 Récompenses", value="\n".join(rewards) if rewards else "Aucune", inline=False)
        embed.set_footer(text=f"Quête #{q['id']} • Créée par {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @quete_group.command(name="liste", description="📋 Voir toutes les quêtes actives")
    async def quete_liste(self, interaction: discord.Interaction):
        pool = await get_pool()
        async with pool.acquire() as conn:
            quests = await conn.fetch(
                "SELECT * FROM quests WHERE guild_id=$1 AND active=TRUE ORDER BY created_at DESC",
                interaction.guild.id
            )
            # Quêtes déjà complétées par l'utilisateur
            completed = await conn.fetch(
                "SELECT quest_id FROM quest_completions WHERE guild_id=$1 AND discord_id=$2",
                interaction.guild.id, interaction.user.id
            )
        completed_ids = {r['quest_id'] for r in completed}

        if not quests:
            return await interaction.response.send_message("📜 Aucune quête disponible pour l'instant !", ephemeral=True)

        embed = discord.Embed(
            title="📜 TABLEAU DES QUÊTES",
            description="*Les parchemins s'agitent dans la brise du destin...*",
            color=0xC8A96E
        )

        for q in quests:
            done = "✅" if q['id'] in completed_ids else "🔲"
            rewards = []
            if q['reward_rep']: rewards.append(f"⚖️{q['reward_rep']} rép")
            if q['reward_gold']: rewards.append(f"🪙{q['reward_gold']} or")
            if q['reward_badge']: rewards.append(q['reward_badge'])
            reward_str = " • ".join(rewards) if rewards else "—"
            embed.add_field(
                name=f"{done} #{q['id']} — {q['title']}",
                value=f"{q['description']}\n*Récompenses : {reward_str}*",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

    @quete_group.command(name="valider", description="✅ Valider la complétion d'une quête pour un membre (Admin)")
    @app_commands.describe(quest_id="ID de la quête", membre="Membre qui a complété la quête")
    @app_commands.checks.has_permissions(administrator=True)
    async def quete_valider(self, interaction: discord.Interaction, quest_id: int, membre: discord.Member):
        pool = await get_pool()
        async with pool.acquire() as conn:
            quest = await conn.fetchrow("SELECT * FROM quests WHERE id=$1 AND guild_id=$2", quest_id, interaction.guild.id)
            if not quest:
                return await interaction.response.send_message("❌ Quête introuvable !", ephemeral=True)

            already = await conn.fetchrow(
                "SELECT id FROM quest_completions WHERE quest_id=$1 AND discord_id=$2",
                quest_id, membre.id
            )
            if already:
                return await interaction.response.send_message("❌ Ce membre a déjà complété cette quête !", ephemeral=True)

            await conn.execute(
                "INSERT INTO quest_completions (quest_id, guild_id, discord_id, validated_by) VALUES ($1,$2,$3,$4)",
                quest_id, interaction.guild.id, membre.id, interaction.user.id
            )
            await conn.execute(
                "INSERT INTO users (guild_id, discord_id) VALUES ($1,$2) ON CONFLICT DO NOTHING",
                interaction.guild.id, membre.id
            )
            if quest['reward_rep']:
                await conn.execute(
                    "UPDATE users SET reputation=reputation+$1 WHERE guild_id=$2 AND discord_id=$3",
                    quest['reward_rep'], interaction.guild.id, membre.id
                )
            if quest['reward_gold']:
                await conn.execute(
                    "UPDATE users SET gold=gold+$1 WHERE guild_id=$2 AND discord_id=$3",
                    quest['reward_gold'], interaction.guild.id, membre.id
                )
            if quest['reward_badge']:
                await conn.execute(
                    "UPDATE users SET badges=array_append(badges,$1) WHERE guild_id=$2 AND discord_id=$3",
                    quest['reward_badge'], interaction.guild.id, membre.id
                )

        # Attribuer le rôle si configuré
        if quest['reward_role_id']:
            try:
                role = interaction.guild.get_role(quest['reward_role_id'])
                if role:
                    await membre.add_roles(role)
            except:
                pass

        embed = discord.Embed(
            title="✅ QUÊTE ACCOMPLIE !",
            description=f"*Les dieux ont reconnu la valeur de {membre.mention} !*",
            color=0x2ECC71
        )
        embed.add_field(name="📜 Quête", value=quest['title'], inline=False)
        rewards = []
        if quest['reward_rep']: rewards.append(f"⚖️ +{quest['reward_rep']} réputation")
        if quest['reward_gold']: rewards.append(f"🪙 +{quest['reward_gold']} or")
        if quest['reward_badge']: rewards.append(f"Badge {quest['reward_badge']} obtenu !")
        if quest['reward_role_id']: rewards.append("Nouveau rôle attribué !")
        embed.add_field(name="🎁 Récompenses reçues", value="\n".join(rewards) if rewards else "—", inline=False)
        await interaction.response.send_message(embed=embed)

    @quete_group.command(name="supprimer", description="🗑️ Désactiver une quête (Admin)")
    @app_commands.describe(quest_id="ID de la quête à supprimer")
    @app_commands.checks.has_permissions(administrator=True)
    async def quete_supprimer(self, interaction: discord.Interaction, quest_id: int):
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE quests SET active=FALSE WHERE id=$1 AND guild_id=$2",
                quest_id, interaction.guild.id
            )
        if result == "UPDATE 0":
            return await interaction.response.send_message("❌ Quête introuvable !", ephemeral=True)
        await interaction.response.send_message(f"🗑️ Quête #{quest_id} retirée du tableau.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Quetes(bot))
