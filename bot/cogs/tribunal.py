import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_pool
import asyncio
from datetime import datetime

VOTE_DURATION = 60  # secondes

class VoteView(discord.ui.View):
    def __init__(self, trial_id: int, accused_id: int):
        super().__init__(timeout=VOTE_DURATION)
        self.trial_id = trial_id
        self.accused_id = accused_id
        self.voters = set()

    @discord.ui.button(label="⚔️ Coupable", style=discord.ButtonStyle.danger)
    async def guilty(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.voters:
            return await interaction.response.send_message("Vous avez déjà voté !", ephemeral=True)
        if interaction.user.id == self.accused_id:
            return await interaction.response.send_message("Vous ne pouvez pas voter pour votre propre procès !", ephemeral=True)
        self.voters.add(interaction.user.id)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE trials SET votes_guilty = votes_guilty + 1 WHERE id=$1", self.trial_id)
        await interaction.response.send_message("⚔️ Vote enregistré : **Coupable**", ephemeral=True)

    @discord.ui.button(label="🕊️ Innocent", style=discord.ButtonStyle.success)
    async def innocent(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.voters:
            return await interaction.response.send_message("Vous avez déjà voté !", ephemeral=True)
        if interaction.user.id == self.accused_id:
            return await interaction.response.send_message("Vous ne pouvez pas voter pour votre propre procès !", ephemeral=True)
        self.voters.add(interaction.user.id)
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE trials SET votes_innocent = votes_innocent + 1 WHERE id=$1", self.trial_id)
        await interaction.response.send_message("🕊️ Vote enregistré : **Innocent**", ephemeral=True)

class Tribunal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="accuser", description="⚖️ Ouvrir un procès contre un membre")
    @app_commands.describe(membre="Le membre à accuser", raison="Le chef d'accusation")
    async def accuser(self, interaction: discord.Interaction, membre: discord.Member, raison: str):
        if membre.id == interaction.user.id:
            return await interaction.response.send_message("Vous ne pouvez pas vous accuser vous-même !", ephemeral=True)

        pool = await get_pool()
        async with pool.acquire() as conn:
            trial = await conn.fetchrow(
                "INSERT INTO trials (guild_id, accused_id, accuser_id, reason, status) VALUES ($1,$2,$3,$4,'open') RETURNING id",
                interaction.guild.id, membre.id, interaction.user.id, raison
            )
            await conn.execute(
                "INSERT INTO users (guild_id, discord_id) VALUES ($1,$2) ON CONFLICT DO NOTHING",
                interaction.guild.id, membre.id
            )

        trial_id = trial['id']
        view = VoteView(trial_id, membre.id)

        embed = discord.Embed(
            title="⚖️ TRIBUNAL DE PLAID — PROCÈS OUVERT",
            description=f"*Le parchemin du destin se déroule...*",
            color=0xC8A96E
        )
        embed.add_field(name="📜 Accusé", value=membre.mention, inline=True)
        embed.add_field(name="⚔️ Accusateur", value=interaction.user.mention, inline=True)
        embed.add_field(name="📋 Chef d'accusation", value=f"*{raison}*", inline=False)
        embed.add_field(name="⏳ Durée du vote", value=f"{VOTE_DURATION} secondes", inline=True)
        embed.set_footer(text=f"Procès #{trial_id} • Que justice soit rendue")
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/⚖️")

        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()

        await asyncio.sleep(VOTE_DURATION)
        view.stop()

        async with pool.acquire() as conn:
            trial_data = await conn.fetchrow("SELECT * FROM trials WHERE id=$1", trial_id)
            guilty = trial_data['votes_guilty']
            innocent = trial_data['votes_innocent']

            if guilty > innocent:
                verdict = "coupable"
                rep_change = -20
                await conn.execute("UPDATE trials SET verdict='coupable', status='closed', ended_at=NOW() WHERE id=$1", trial_id)
                await conn.execute("UPDATE users SET reputation=reputation-20, losses=losses+1, total_trials=total_trials+1 WHERE guild_id=$1 AND discord_id=$2", interaction.guild.id, membre.id)
                await conn.execute("INSERT INTO casier (guild_id, discord_id, infraction, verdict) VALUES ($1,$2,$3,'coupable')", interaction.guild.id, membre.id, raison)
                color = 0xE74C3C
                verdict_text = "⚔️ **COUPABLE** — La sentence est prononcée !"
            else:
                verdict = "innocent"
                rep_change = +10
                await conn.execute("UPDATE trials SET verdict='innocent', status='closed', ended_at=NOW() WHERE id=$1", trial_id)
                await conn.execute("UPDATE users SET reputation=reputation+10, wins=wins+1, total_trials=total_trials+1 WHERE guild_id=$1 AND discord_id=$2", interaction.guild.id, membre.id)
                color = 0x2ECC71
                verdict_text = "🕊️ **INNOCENT** — L'accusé est libre !"

        result_embed = discord.Embed(
            title="📜 VERDICT FINAL",
            description=verdict_text,
            color=color
        )
        result_embed.add_field(name="⚔️ Votes Coupable", value=str(guilty), inline=True)
        result_embed.add_field(name="🕊️ Votes Innocent", value=str(innocent), inline=True)
        result_embed.add_field(name="📊 Impact réputation", value=f"{rep_change:+d}", inline=True)
        result_embed.set_footer(text=f"Procès #{trial_id} • PLAID a parlé")

        await msg.edit(embed=result_embed, view=None)

async def setup(bot):
    await bot.add_cog(Tribunal(bot))
