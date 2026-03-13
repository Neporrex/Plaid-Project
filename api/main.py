from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Plaid API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    return {"name": "Plaid API", "status": "⚖️ En service"}

@app.get("/api/stats/{guild_id}")
async def get_stats(guild_id: int):
    async with pool.acquire() as conn:
        users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE guild_id=$1", guild_id)
        trials = await conn.fetchval("SELECT COUNT(*) FROM trials WHERE guild_id=$1", guild_id)
        laws = await conn.fetchval("SELECT COUNT(*) FROM laws WHERE guild_id=$1", guild_id)
    return {"users": users, "trials": trials, "laws": laws}

@app.get("/api/leaderboard/{guild_id}")
async def get_leaderboard(guild_id: int, sort: str = "best", limit: int = 10):
    async with pool.acquire() as conn:
        if sort == "best":
            rows = await conn.fetch(
                "SELECT * FROM users WHERE guild_id=$1 ORDER BY reputation DESC LIMIT $2",
                guild_id, limit
            )
        elif sort == "worst":
            rows = await conn.fetch(
                "SELECT * FROM users WHERE guild_id=$1 ORDER BY reputation ASC LIMIT $2",
                guild_id, limit
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM users WHERE guild_id=$1 ORDER BY total_trials DESC LIMIT $2",
                guild_id, limit
            )
    return [dict(r) for r in rows]

@app.get("/api/user/{guild_id}/{discord_id}")
async def get_user(guild_id: int, discord_id: int):
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE guild_id=$1 AND discord_id=$2",
            guild_id, discord_id
        )
        cases = await conn.fetch(
            "SELECT * FROM casier WHERE guild_id=$1 AND discord_id=$2 ORDER BY created_at DESC",
            guild_id, discord_id
        )
    if not user:
        return {"error": "User not found"}
    return {"user": dict(user), "casier": [dict(c) for c in cases]}

@app.get("/api/trials/{guild_id}")
async def get_trials(guild_id: int, limit: int = 20):
    async with pool.acquire() as conn:
        trials = await conn.fetch(
            "SELECT * FROM trials WHERE guild_id=$1 ORDER BY created_at DESC LIMIT $2",
            guild_id, limit
        )
    return [dict(t) for t in trials]

@app.get("/api/laws/{guild_id}")
async def get_laws(guild_id: int):
    async with pool.acquire() as conn:
        laws = await conn.fetch(
            "SELECT * FROM laws WHERE guild_id=$1 ORDER BY id",
            guild_id
        )
    return [dict(l) for l in laws]
