import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_pool
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import os
import math

RANKS = [
    (500, "👑 Légende", 0xFFD700),
    (300, "⚔️ Chevalier", 0xC0C0C0),
    (200, "🛡️ Gardien", 0x4169E1),
    (100, "⚖️ Citoyen", 0x228B22),
    (0,   "🔗 Banni", 0x8B0000),
]

def get_rank(rep):
    for threshold, name, color in RANKS:
        if rep >= threshold:
            return name, color
    return "🔗 Banni", 0x8B0000

def draw_parchment_bg(draw, width, height):
    # Fond parchemin
    for y in range(height):
        ratio = y / height
        r = int(245 - ratio * 30 + (hash(y*7) % 10 - 5))
        g = int(220 - ratio * 20 + (hash(y*13) % 8 - 4))
        b = int(170 - ratio * 10 + (hash(y*17) % 6 - 3))
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

def draw_border(draw, width, height):
    # Bordure ornementale
    border_color = (101, 67, 33)
    border_color2 = (160, 120, 60)
    # Bordure externe
    draw.rectangle([0, 0, width-1, height-1], outline=border_color, width=6)
    draw.rectangle([8, 8, width-9, height-9], outline=border_color2, width=2)
    draw.rectangle([12, 12, width-13, height-13], outline=border_color, width=1)
    # Coins ornementaux
    corners = [(15, 15), (width-35, 15), (15, height-35), (width-35, height-35)]
    for cx, cy in corners:
        draw.ellipse([cx, cy, cx+18, cy+18], outline=border_color, width=2)
        draw.ellipse([cx+4, cy+4, cx+14, cy+14], fill=border_color2)

async def generate_leaderboard_image(rows, title, guild_name):
    width, height = 800, 120 + len(rows) * 72 + 60
    img = Image.new("RGB", (width, height), (245, 220, 170))
    draw = ImageDraw.Draw(img)

    draw_parchment_bg(draw, width, height)
    draw_border(draw, width, height)

    # Essayer de charger une font, sinon font par défaut
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 32)
        font_subtitle = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 16)
        font_name = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 20)
        font_stats = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 16)
        font_rank_num = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 24)
    except:
        font_title = ImageFont.load_default()
        font_subtitle = font_title
        font_name = font_title
        font_stats = font_title
        font_rank_num = font_title

    dark_brown = (60, 30, 10)
    medium_brown = (101, 67, 33)
    gold = (180, 140, 20)
    red_dark = (139, 0, 0)

    # Titre principal
    title_text = "⚖ REGISTRE DES ÂMES ⚖"
    bbox = draw.textbbox((0,0), title_text, font=font_title)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, 20), title_text, fill=dark_brown, font=font_title)

    # Sous-titre
    sub_text = f"Serveur : {guild_name}  •  {title}"
    bbox2 = draw.textbbox((0,0), sub_text, font=font_subtitle)
    sw = bbox2[2] - bbox2[0]
    draw.text(((width - sw) // 2, 60), sub_text, fill=medium_brown, font=font_subtitle)

    # Ligne de séparation ornementée
    draw.line([(40, 90), (width-40, 90)], fill=medium_brown, width=2)
    draw.ellipse([(width//2 - 6, 84), (width//2 + 6, 96)], fill=gold)

    medals = ["👑", "⚔️", "🛡️"]
    medal_colors = [(180, 140, 20), (150, 150, 160), (140, 100, 50)]

    y_offset = 108
    for i, row in enumerate(rows):
        # Fond de ligne alternée
        if i % 2 == 0:
            draw.rectangle([20, y_offset - 4, width - 20, y_offset + 56], fill=(235, 208, 155, 180))
        else:
            draw.rectangle([20, y_offset - 4, width - 20, y_offset + 56], fill=(245, 220, 170, 100))

        # Numéro / médaille
        if i < 3:
            num_color = medal_colors[i]
            num_text = medals[i]
        else:
            num_color = medium_brown
            num_text = f"#{i+1}"

        draw.text((30, y_offset + 10), num_text, fill=num_color, font=font_rank_num)

        # Nom
        name = row.get('username', f"User#{row['discord_id']}")[:20]
        draw.text((80, y_offset + 6), name, fill=dark_brown, font=font_name)

        # Rang
        rank_name, _ = get_rank(row['reputation'])
        draw.text((80, y_offset + 30), rank_name, fill=medium_brown, font=font_stats)

        # Stats à droite
        stats = f"⚖ {row['reputation']} rép  •  {row['total_trials']} procès  •  🪙 {row.get('gold', 0)}"
        bbox_s = draw.textbbox((0,0), stats, font=font_stats)
        sw = bbox_s[2] - bbox_s[0]
        draw.text((width - sw - 35, y_offset + 18), stats, fill=medium_brown, font=font_stats)

        # Ligne séparatrice légère
        draw.line([(40, y_offset + 60), (width - 40, y_offset + 60)], fill=(180, 150, 100), width=1)

        y_offset += 72

    # Pied de page
    footer = "✦ Que la justice du royaume soit éternelle ✦"
    bbox_f = draw.textbbox((0,0), footer, font=font_subtitle)
    fw = bbox_f[2] - bbox_f[0]
    draw.text(((width - fw) // 2, height - 38), footer, fill=medium_brown, font=font_subtitle)

    # Légère texture de vieillissement (taches)
    import random
    random.seed(42)
    for _ in range(80):
        x = random.randint(0, width)
        y = random.randint(0, height)
        r = random.randint(1, 4)
        alpha = random.randint(15, 40)
        draw.ellipse([x-r, y-r, x+r, y+r], fill=(101, 67, 33, alpha))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="classement", description="📜 Voir le classement du serveur en image")
    @app_commands.describe(type="Type de classement")
    @app_commands.choices(type=[
        app_commands.Choice(name="👑 Meilleure réputation", value="best"),
        app_commands.Choice(name="💀 Pire réputation", value="worst"),
        app_commands.Choice(name="⚖️ Plus jugés", value="trials"),
        app_commands.Choice(name="🪙 Plus riches", value="gold"),
    ])
    async def classement(self, interaction: discord.Interaction, type: str = "best"):
        await interaction.response.defer()
        pool = await get_pool()

        async with pool.acquire() as conn:
            if type == "best":
                rows = await conn.fetch("SELECT * FROM users WHERE guild_id=$1 ORDER BY reputation DESC LIMIT 10", interaction.guild.id)
                title = "Meilleurs citoyens"
            elif type == "worst":
                rows = await conn.fetch("SELECT * FROM users WHERE guild_id=$1 ORDER BY reputation ASC LIMIT 10", interaction.guild.id)
                title = "Pires criminels"
            elif type == "gold":
                rows = await conn.fetch("SELECT * FROM users WHERE guild_id=$1 ORDER BY gold DESC LIMIT 10", interaction.guild.id)
                title = "Les plus fortunés"
            else:
                rows = await conn.fetch("SELECT * FROM users WHERE guild_id=$1 ORDER BY total_trials DESC LIMIT 10", interaction.guild.id)
                title = "Les plus jugés"

        if not rows:
            return await interaction.followup.send("📊 Aucune donnée pour le moment !")

        rows_dicts = []
        for row in rows:
            d = dict(row)
            try:
                member = await interaction.guild.fetch_member(d['discord_id'])
                d['username'] = member.display_name
            except:
                d['username'] = f"Inconnu#{d['discord_id']}"
            rows_dicts.append(d)

        image_buf = await generate_leaderboard_image(rows_dicts, title, interaction.guild.name)
        file = discord.File(image_buf, filename="classement.png")
        await interaction.followup.send(file=file)


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
