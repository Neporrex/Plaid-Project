import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_pool

RANKS = [
    (500, "👑 Légende du Royaume",   0xFFD700),
    (300, "⚔️ Chevalier Émérite",    0xC0C0C0),
    (200, "🛡️ Gardien de la Loi",    0x4169E1),
    (100, "⚖️ Citoyen Honorable",    0x2ECC71),
    (50,  "🧑 Citoyen Lambda",       0x95A5A6),
    (0,   "⛓️ Âme Condamnée",        0x8B0000),
]

def get_rank(rep):
    for threshold, name, color in RANKS:
        if rep >= threshold:
            return name, color
    return "⛓️ Âme Condamnée", 0x8B0000

def rep_bar(rep, max_rep=500):
    pct = max(0, min(rep, max_rep)) / max_rep
    filled = round(pct * 12)
    bar = "█" * filled + "░" * (12 - filled)
    pct_str = f"{int(pct*100)}%"
    return f"`{bar}` {rep}/{max_rep} ({pct_str})"


class Reputation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="profil", description="📜 Voir votre fiche de citoyen")
    @app_commands.describe(membre="Le membre dont voir le profil (vous par défaut)")
    async def profil(self, interaction: discord.Interaction, membre: discord.Member = None):
        await interaction.response.defer()
        target = membre or interaction.user
        pool = await get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (guild_id, discord_id) VALUES ($1,$2) ON CONFLICT DO NOTHING",
                interaction.guild.id, target.id
            )
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE guild_id=$1 AND discord_id=$2",
                interaction.guild.id, target.id
            )
            case_count = await conn.fetchval(
                "SELECT COUNT(*) FROM casier WHERE guild_id=$1 AND discord_id=$2",
                interaction.guild.id, target.id
            )

        rank_name, rank_color = get_rank(user['reputation'])

        embed = discord.Embed(
            title=f"📜 Fiche de {target.display_name}",
            description=f"*{rank_name}*",
            color=rank_color
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        # Réputation
        embed.add_field(
            name="⚖️ Réputation",
            value=rep_bar(user['reputation']),
            inline=False
        )

        # Stats procès
        total = user['total_trials']
        wins = user['wins']
        losses = user['losses']
        winrate = f"{int(wins/total*100)}%" if total > 0 else "—"
        embed.add_field(name="📋 Procès", value=f"{total} au total", inline=True)
        embed.add_field(name="🏆 Victoires", value=f"{wins} ({winrate})", inline=True)
        embed.add_field(name="💀 Défaites", value=str(losses), inline=True)

        # Économie
        embed.add_field(name="🪙 Or", value=str(user['gold']), inline=True)
        embed.add_field(name="🗂️ Casier", value=f"{case_count} infraction(s)", inline=True)

        # Guilde
        if user.get('guild_name'):
            embed.add_field(name="⚔️ Guilde", value=user['guild_name'], inline=True)

        # Titre
        if user.get('title'):
            embed.add_field(name="✦ Titre", value=user['title'], inline=True)

        # Badges
        badges = user.get('badges') or []
        if badges:
            embed.add_field(name="🏅 Badges", value="  ".join(badges[:10]), inline=False)

        embed.set_footer(text=f"⚖️ PLAID • {interaction.guild.name}")
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Reputation(bot))
