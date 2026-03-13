from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Plaid API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Mettre votre domaine Vercel en prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pool = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))

@app.get("/")
async def root():
    return {"name": "Plaid API", "version": "2.0", "status": "⚖️ En service"}

@app.get("/api/stats/{guild_id}")
async def get_stats(guild_id: int):
    async with pool.acquire() as conn:
        users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE guild_id=$1", guild_id)
        trials = await conn.fetchval("SELECT COUNT(*) FROM trials WHERE guild_id=$1", guild_id)
        laws = await conn.fetchval("SELECT COUNT(*) FROM laws WHERE guild_id=$1", guild_id)
        quests = await conn.fetchval("SELECT COUNT(*) FROM quests WHERE guild_id=$1 AND active=TRUE", guild_id)
        guildes = await conn.fetchval("SELECT COUNT(*) FROM guilds_rpg WHERE guild_id=$1", guild_id)
        bounties = await conn.fetchval("SELECT COUNT(*) FROM bounties WHERE guild_id=$1 AND active=TRUE", guild_id)
    return {"users": users, "trials": trials, "laws": laws, "quests": quests, "guildes": guildes, "bounties": bounties}

@app.get("/api/leaderboard/{guild_id}")
async def get_leaderboard(guild_id: int, sort: str = "best", limit: int = 10):
    async with pool.acquire() as conn:
        order = {"best": "reputation DESC", "worst": "reputation ASC", "gold": "gold DESC", "trials": "total_trials DESC"}.get(sort, "reputation DESC")
        rows = await conn.fetch(f"SELECT * FROM users WHERE guild_id=$1 ORDER BY {order} LIMIT $2", guild_id, limit)
    return [dict(r) for r in rows]

@app.get("/api/user/{guild_id}/{discord_id}")
async def get_user(guild_id: int, discord_id: int):
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE guild_id=$1 AND discord_id=$2", guild_id, discord_id)
        cases = await conn.fetch("SELECT * FROM casier WHERE guild_id=$1 AND discord_id=$2 ORDER BY created_at DESC", guild_id, discord_id)
        oaths = await conn.fetch("SELECT * FROM oaths WHERE guild_id=$1 AND discord_id=$2 ORDER BY created_at DESC LIMIT 5", guild_id, discord_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": dict(user), "casier": [dict(c) for c in cases], "serments": [dict(o) for o in oaths]}

@app.get("/api/trials/{guild_id}")
async def get_trials(guild_id: int, limit: int = 20):
    async with pool.acquire() as conn:
        trials = await conn.fetch("SELECT * FROM trials WHERE guild_id=$1 ORDER BY created_at DESC LIMIT $2", guild_id, limit)
    return [dict(t) for t in trials]

@app.get("/api/laws/{guild_id}")
async def get_laws(guild_id: int):
    async with pool.acquire() as conn:
        laws = await conn.fetch("SELECT * FROM laws WHERE guild_id=$1 ORDER BY id", guild_id)
    return [dict(l) for l in laws]

@app.get("/api/quests/{guild_id}")
async def get_quests(guild_id: int):
    async with pool.acquire() as conn:
        quests = await conn.fetch("SELECT * FROM quests WHERE guild_id=$1 AND active=TRUE ORDER BY created_at DESC", guild_id)
    return [dict(q) for q in quests]

@app.get("/api/guildes/{guild_id}")
async def get_guildes(guild_id: int):
    async with pool.acquire() as conn:
        guildes = await conn.fetch("SELECT * FROM guilds_rpg WHERE guild_id=$1 ORDER BY array_length(members,1) DESC", guild_id)
    return [dict(g) for g in guildes]

@app.get("/api/bounties/{guild_id}")
async def get_bounties(guild_id: int):
    async with pool.acquire() as conn:
        bounties = await conn.fetch("SELECT * FROM bounties WHERE guild_id=$1 AND active=TRUE ORDER BY amount DESC", guild_id)
    return [dict(b) for b in bounties]
