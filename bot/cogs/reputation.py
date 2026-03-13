import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_pool

class Reputation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_rank(self, rep):
        if rep >= 180: return "👑 Légende"
        if rep >= 150: return "⭐ Exemplaire"
        if rep >= 120: return "✅ Bon citoyen"
        if rep >= 80: return "😐 Neutre"
        if rep >= 50: return "⚠️ Suspect"
        if rep >= 20: return "🔴 Criminel"
        return "💀 Paria"

    def get_rep_bar(self, rep):
        filled = min(rep // 10, 20)
        empty = 20 - filled
        return f"{'🟩' * filled}{'⬛' * empty} {rep}/200"

    @app_commands.command(name="profil", description="📊 Voir le profil judiciaire de quelqu'un")
    @app_commands.describe(membre="Le membre dont tu veux voir le profil")
    async def profil(self, interaction: discord.Interaction, membre: discord.Member = None):
        membre = membre or interaction.user
        pool = await get_pool()

        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO users (discord_id, guild_id)
                VALUES ($1, $2) ON CONFLICT DO NOTHING
            """, membre.id, interaction.guild.id)

            user = await conn.fetchrow("""
                SELECT * FROM users WHERE discord_id=$1 AND guild_id=$2
            """, membre.id, interaction.guild.id)

            cases = await conn.fetch("""
                SELECT * FROM casier WHERE discord_id=$1 AND guild_id=$2
                ORDER BY created_at DESC LIMIT 5
            """, membre.id, interaction.guild.id)

        rank = self.get_rank(user['reputation'])
        bar = self.get_rep_bar(user['reputation'])

        embed = discord.Embed(
            title=f"📋 Profil de {membre.display_name}",
            color=0x5865F2
        )
        embed.set_thumbnail(url=membre.display_avatar.url)
        embed.add_field(name="🏅 Rang", value=rank, inline=True)
        embed.add_field(name="📊 Réputation", value=bar, inline=False)
        embed.add_field(name="⚖️ Procès", value=f"Total: {user['total_trials']}", inline=True)
        embed.add_field(name="🔴 Coupable", value=str(user['guilty_count']), inline=True)
        embed.add_field(name="🟢 Innocent", value=str(user['innocent_count']), inline=True)

        if cases:
            casier_text = ""
            for c in cases[:5]:
                casier_text += f"• {c['offense']} ({c['rep_change']:+d} rep)\n"
            embed.add_field(name="📜 Casier récent", value=casier_text, inline=False)
        else:
            embed.add_field(name="📜 Casier", value="✨ Casier vierge !", inline=False)

        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Reputation(bot))
