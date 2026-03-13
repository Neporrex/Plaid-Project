# ⚖️ PLAID — Bot Discord Tribunal

## Structure
```
plaid/
├── bot/          → Discord bot (Python + discord.py)
├── api/          → API REST (FastAPI)
└── web/          → Site web (HTML/CSS/JS)
```

## Setup

### 1. Variables d'environnement
Copie `.env.example` en `.env` et remplis :
- `DISCORD_TOKEN` → Token de ton bot Discord
- `DATABASE_URL` → URL PostgreSQL (Render)
- `API_URL` → URL de ton API déployée

### 2. Déploiement Render — Base de données
1. New → PostgreSQL
2. Copie l'Internal Database URL → c'est ton `DATABASE_URL`

### 3. Déploiement Render — Bot
1. New → Background Worker
2. Root directory: `bot`
3. Build command: `pip install -r requirements.txt`
4. Start command: `python main.py`
5. Ajoute les variables d'env

### 4. Déploiement Render — API
1. New → Web Service
2. Root directory: `api`
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Ajoute les variables d'env

### 5. Déploiement Vercel — Site web
1. New Project → import le dossier `web`
2. Framework: Other
3. Output directory: `.`
4. Dans `web/js/app.js` et les pages HTML, remplace l'URL API par celle de ton service Render

## Commandes Discord
- `/accuser @user raison` — Ouvrir un procès
- `/profil [@user]` — Voir le profil judiciaire
- `/casier [@user]` — Voir le casier complet
- `/classement` — Classement du serveur
- `/lois` — Code pénal du serveur
- `/loi-creer` — Créer une loi (Admin)
- `/loi-supprimer` — Supprimer une loi (Admin)
