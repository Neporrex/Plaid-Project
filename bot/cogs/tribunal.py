import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from utils.db import get_pool

class VoteView(discord.ui.View):
    def __init__(self, trial_id: int, timeout_seconds: int = 120):
        super().__init__(timeout=timeout_seconds)
        self.trial_id = trial_id

    @discord.ui.button(label="⚖️ Coupable", style=discord.ButtonStyle.danger)
    async def guilty(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cast_vote(interaction, "guilty")

    @discord.ui.button(label="😇 Innocent", style=discord.ButtonStyle.success)
    async def innocent(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cast_vote(interaction, "innocent")

    async def cast_vote(self, interaction: discord.Interaction, vote: str):
        pool = await get_pool()
        async with pool.acquire() as conn:
            existing = await conn.fetchrow(
                "SELECT * FROM votes WHERE trial_id=$1 AND voter_id=$2",
                self.trial_id, interaction.user.id
            )
            if existing:
                await interaction.response.send_message("❌ Tu as déjà voté !", ephemeral=True)
                return

            trial = await conn.fetchrow(
                "SELECT * FROM trials WHERE id=$1", self.trial_id
            )
            if interaction.user.id in [trial['accuser_id'], trial['accused_id']]:
                await interaction.response.send_message("❌ Tu ne peux pas voter dans ton propre procès !", ephemeral=True)
                return

            await conn.execute(
                "INSERT INTO votes (trial_id, voter_id, vote) VALUES ($1, $2, $3)",
                self.trial_id, interaction.user.id, vote
            )

            if vote == "guilty":
                await conn.execute(
                    "UPDATE trials SET votes_guilty = votes_guilty + 1 WHERE id=$1",
                    self.trial_id
                )
            else:
                await conn.execute(
                    "UPDATE trials SET votes_innocent = votes_innocent + 1 WHERE id=$1",
                    self.trial_id
                )

            trial = await conn.fetchrow("SELECT * FROM trials WHERE id=$1", self.trial_id)
            emoji = "🔴" if vote == "guilty" else "🟢"
            await interaction.response.send_message(
                f"{emoji} Vote enregistré ! (Coupable: {trial['votes_guilty']} | Innocent: {trial['votes_innocent']})",
                ephemeral=True
            )


class Tribunal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="accuser", description="⚖️ Ouvrir un procès contre quelqu'un")
    @app_commands.describe(
        accusé="La personne à juger",
        raison="Pourquoi tu l'accuses",
        durée="Durée du vote en minutes (défaut: 2)"
    )
    async def accuser(
        self, 
        interaction: discord.Interaction, 
        accusé: discord.Member, 
        raison: str,
        durée: int = 2
    ):
        if accusé.id == interaction.user.id:
            await interaction.response.send_message("❌ Tu ne peux pas t'accuser toi-même !", ephemeral=True)
            return

        if accusé.bot:
            await interaction.response.send_message("❌ Tu ne peux pas accuser un bot !", ephemeral=True)
            return

        pool = await get_pool()
        async with pool.acquire() as conn:
            for uid in [interaction.user.id, accusé.id]:
                await conn.execute("""
                    INSERT INTO users (discord_id, guild_id)
                    VALUES ($1, $2) ON CONFLICT DO NOTHING
                """, uid, interaction.guild.id)

            trial = await conn.fetchrow("""
                INSERT INTO trials (guild_id, accuser_id, accused_id, reason, channel_id)
                VALUES ($1, $2, $3, $4, $5) RETURNING id
            """, interaction.guild.id, interaction.user.id, accusé.id, raison, interaction.channel.id)

        trial_id = trial['id']
        timeout = durée * 60

        embed = discord.Embed(
            title=f"⚖️ PROCÈS #{trial_id}",
            description=f"**{interaction.user.display_name}** accuse **{accusé.display_name}**",
            color=0xFF6B6B
        )
        embed.add_field(name="📋 Chef d'accusation", value=raison, inline=False)
        embed.add_field(name="⏱️ Durée du vote", value=f"{durée} minute(s)", inline=True)
        embed.add_field(name="📊 Votes", value="Coupable: 0 | Innocent: 0", inline=True)
        embed.set_thumbnail(url=accusé.display_avatar.url)
        embed.set_footer(text="Cliquez sur les boutons pour voter !")

        view = VoteView(trial_id, timeout)
        await interaction.response.send_message(embed=embed, view=view)

        msg = await interaction.original_response()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE trials SET message_id=$1 WHERE id=$2",
                msg.id, trial_id
            )

        await asyncio.sleep(timeout)
        await self.end_trial(interaction, trial_id, msg)

    async def end_trial(self, interaction, trial_id, message):
        pool = await get_pool()
        async with pool.acquire() as conn:
            trial = await conn.fetchrow("SELECT * FROM trials WHERE id=$1", trial_id)

            if trial['status'] != 'en_cours':
                return

            guilty = trial['votes_guilty']
            innocent = trial['votes_innocent']
            total = guilty + innocent

            if total == 0:
                verdict = "annulé"
                color = 0x95A5A6
            elif guilty > innocent:
                verdict = "coupable"
                color = 0xFF0000
            elif innocent > guilty:
                verdict = "innocent"
                color = 0x00FF00
            else:
                verdict = "égalité"
                color = 0xFFFF00

            await conn.execute("""
                UPDATE trials SET status='terminé', verdict=$1, ended_at=NOW() WHERE id=$2
            """, verdict, trial_id)

            if verdict == "coupable":
                await conn.execute("""
                    UPDATE users SET reputation = GREATEST(reputation - 15, 0),
                    total_trials = total_trials + 1, guilty_count = guilty_count + 1
                    WHERE discord_id=$1 AND guild_id=$2
                """, trial['accused_id'], trial['guild_id'])

                await conn.execute("""
                    INSERT INTO casier (discord_id, guild_id, trial_id, offense, punishment, rep_change)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, trial['accused_id'], trial['guild_id'], trial_id, trial['reason'], 'Reconnu coupable', -15)

            elif verdict == "innocent":
                await conn.execute("""
                    UPDATE users SET reputation = LEAST(reputation + 5, 200),
                    total_trials = total_trials + 1, innocent_count = innocent_count + 1
                    WHERE discord_id=$1 AND guild_id=$2
                """, trial['accused_id'], trial['guild_id'])

            accused = await interaction.guild.fetch_member(trial['accused_id'])

            embed = discord.Embed(
                title=f"⚖️ VERDICT — PROCÈS #{trial_id}",
                color=color
            )
            embed.add_field(name="👤 Accusé", value=accused.display_name, inline=True)
            embed.add_field(name="📋 Raison", value=trial['reason'], inline=True)
            embed.add_field(name="📊 Résultat", value=f"Coupable: {guilty} | Innocent: {innocent}", inline=False)

            verdict_text = {
                "coupable": "🔴 **COUPABLE** — Réputation -15",
                "innocent": "🟢 **INNOCENT** — Réputation +5",
                "égalité": "🟡 **ÉGALITÉ** — Aucune sanction",
                "annulé": "⚪ **ANNULÉ** — Personne n'a voté"
            }
            embed.add_field(name="⚖️ Verdict", value=verdict_text[verdict], inline=False)

            try:
                await message.edit(embed=embed, view=None)
            except:
                channel = interaction.channel
                await channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Tribunal(bot))
