import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_pool
from PIL import Image, ImageDraw, ImageFont
import io

RANKS = [
    (500, "👑 Légende du Royaume", 0xFFD700),
    (300, "⚔️ Chevalier Émérite", 0xC0C0C0),
    (200, "🛡️ Gardien de la Loi", 0x4169E1),
    (100, "⚖️ Citoyen Honorable", 0x228B22),
    (50,  "🧑 Citoyen Lambda", 0x808080),
    (0,   "⛓️ Âme Condamnée", 0x8B0000),
]

def get_rank(rep):
    for threshold, name, color in RANKS:
        if rep >= threshold:
            return name, color
    return "⛓️ Âme Condamnée", 0x8B0000

def rep_to_bar(rep, max_rep=500):
    rep = max(0, min(rep, max_rep))
    return rep / max_rep

async def generate_profile_image(user_data, username, avatar_bytes=None):
    width, height = 700, 340
    img = Image.new("RGB", (width, height), (245, 220, 170))
    draw = ImageDraw.Draw(img)

    # Fond parchemin
    for y in range(height):
        ratio = y / height
        r = int(245 - ratio * 25 + (hash(y*7) % 8))
        g = int(218 - ratio * 18 + (hash(y*11) % 6))
        b = int(165 - ratio * 8 + (hash(y*13) % 5))
        draw.line([(0, y), (width, y)], fill=(min(255,r), min(255,g), min(255,b)))

    dark_brown = (60, 30, 10)
    medium_brown = (101, 67, 33)
    gold_color = (180, 140, 20)

    # Bordures
    draw.rectangle([0, 0, width-1, height-1], outline=(60,30,10), width=5)
    draw.rectangle([7, 7, width-8, height-8], outline=(160,120,60), width=2)

    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 26)
        font_med = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 18)
        font_sm  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 15)
        font_xs  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 12)
    except:
        font_big = font_med = font_sm = font_xs = ImageFont.load_default()

    # Avatar
    avatar_x, avatar_y, avatar_size = 30, 30, 90
    if avatar_bytes:
        try:
            av_img = Image.open(io.BytesIO(avatar_bytes)).resize((avatar_size, avatar_size))
            mask = Image.new("L", (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, avatar_size, avatar_size], fill=255)
            img.paste(av_img, (avatar_x, avatar_y), mask)
        except:
            draw.ellipse([avatar_x, avatar_y, avatar_x+avatar_size, avatar_y+avatar_size], fill=medium_brown)
    else:
        draw.ellipse([avatar_x, avatar_y, avatar_x+avatar_size, avatar_y+avatar_size], fill=medium_brown)
        initial = username[0].upper() if username else "?"
        draw.text((avatar_x + 30, avatar_y + 25), initial, fill=(245,220,170), font=font_big)

    # Cercle autour avatar
    draw.ellipse([avatar_x-3, avatar_y-3, avatar_x+avatar_size+3, avatar_y+avatar_size+3], outline=gold_color, width=3)

    # Nom
    draw.text((145, 32), username, fill=dark_brown, font=font_big)

    # Titre / rang
    rank_name, _ = get_rank(user_data['reputation'])
    draw.text((145, 64), rank_name, fill=medium_brown, font=font_med)

    # Titre personnalisé
    if user_data.get('title'):
        draw.text((145, 90), f"✦ {user_data['title']} ✦", fill=gold_color, font=font_sm)

    # Guilde
    if user_data.get('guild_name'):
        draw.text((145, 112), f"⚔️ Guilde : {user_data['guild_name']}", fill=medium_brown, font=font_sm)

    # Ligne séparatrice
    draw.line([(20, 140), (width-20, 140)], fill=medium_brown, width=2)
    draw.ellipse([(width//2-5, 134), (width//2+5, 146)], fill=gold_color)

    # Stats en 3 colonnes
    stats = [
        ("⚖️ Réputation", str(user_data['reputation'])),
        ("⚔️ Victoires", str(user_data['wins'])),
        ("💀 Défaites", str(user_data['losses'])),
        ("📋 Procès", str(user_data['total_trials'])),
        ("🪙 Or", str(user_data.get('gold', 0))),
        ("🏅 Badges", str(len(user_data.get('badges', [])))),
    ]

    col_w = (width - 60) // 3
    for i, (label, value) in enumerate(stats):
        col = i % 3
        row = i // 3
        x = 30 + col * col_w
        y = 158 + row * 55
        # Fond case
        draw.rectangle([x, y, x+col_w-10, y+45], fill=(230, 200, 145), outline=medium_brown, width=1)
        draw.text((x + 8, y + 4), label, fill=medium_brown, font=font_xs)
        draw.text((x + 8, y + 22), value, fill=dark_brown, font=font_med)

    # Barre de réputation
    bar_y = height - 55
    bar_x, bar_w = 30, width - 60
    draw.text((bar_x, bar_y - 20), "Progression de réputation", fill=medium_brown, font=font_xs)
    draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + 18], outline=medium_brown, width=2, fill=(200, 170, 110))
    fill_w = int(bar_w * rep_to_bar(user_data['reputation']))
    if fill_w > 0:
        draw.rectangle([bar_x+2, bar_y+2, bar_x+fill_w-2, bar_y+16], fill=gold_color)
    draw.text((bar_x + bar_w + 8, bar_y), f"{user_data['reputation']}/500", fill=medium_brown, font=font_xs)

    # Badges
    if user_data.get('badges'):
        badge_text = "  ".join(user_data['badges'][:8])
        draw.text((30, height - 28), f"Badges : {badge_text}", fill=dark_brown, font=font_xs)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


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
            user = await conn.fetchrow(
                "SELECT * FROM users WHERE guild_id=$1 AND discord_id=$2",
                interaction.guild.id, target.id
            )
            if not user:
                await conn.execute(
                    "INSERT INTO users (guild_id, discord_id) VALUES ($1,$2) ON CONFLICT DO NOTHING",
                    interaction.guild.id, target.id
                )
                user = await conn.fetchrow(
                    "SELECT * FROM users WHERE guild_id=$1 AND discord_id=$2",
                    interaction.guild.id, target.id
                )

        user_data = dict(user)

        avatar_bytes = None
        try:
            avatar_bytes = await target.display_avatar.read()
        except:
            pass

        image_buf = await generate_profile_image(user_data, target.display_name, avatar_bytes)
        file = discord.File(image_buf, filename="profil.png")
        await interaction.followup.send(file=file)


async def setup(bot):
    await bot.add_cog(Reputation(bot))
