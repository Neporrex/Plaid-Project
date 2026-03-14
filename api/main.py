from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
import os
import traceback
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Plaid API", version="2.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

pool = None

TABLES = [
    ("users", """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            discord_id BIGINT NOT NULL,
            reputation INTEGER DEFAULT 100,
            total_trials INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            gold INTEGER DEFAULT 0,
            badges TEXT[] DEFAULT '{}',
            title TEXT DEFAULT 'Citoyen',
            guild_name TEXT,
            UNIQUE(guild_id, discord_id)
        )
    """),
    ("trials", """
        CREATE TABLE IF NOT EXISTS trials (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            accused_id BIGINT NOT NULL,
            accuser_id BIGINT NOT NULL,
            reason TEXT NOT NULL,
            verdict TEXT,
            votes_guilty INTEGER DEFAULT 0,
            votes_innocent INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT NOW(),
            ended_at TIMESTAMP
        )
    """),
    ("casier", """
        CREATE TABLE IF NOT EXISTS casier (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            discord_id BIGINT NOT NULL,
            infraction TEXT NOT NULL,
            verdict TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """),
    ("laws", """
        CREATE TABLE IF NOT EXISTS laws (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            penalty TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """),
    ("bounties", """
        CREATE TABLE IF NOT EXISTS bounties (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            target_id BIGINT NOT NULL,
            issuer_id BIGINT NOT NULL,
            amount INTEGER NOT NULL,
            reason TEXT,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """),
    ("guilds_rpg", """
        CREATE TABLE IF NOT EXISTS guilds_rpg (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            leader_id BIGINT NOT NULL,
            members BIGINT[] DEFAULT '{}',
            emblem TEXT DEFAULT '⚔️',
            reputation INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(guild_id, name)
        )
    """),
    ("quests", """
        CREATE TABLE IF NOT EXISTS quests (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            reward_rep INTEGER DEFAULT 0,
            reward_gold INTEGER DEFAULT 0,
            reward_badge TEXT,
            reward_role_id BIGINT,
            created_by BIGINT NOT NULL,
            active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """),
    ("quest_completions", """
        CREATE TABLE IF NOT EXISTS quest_completions (
            id SERIAL PRIMARY KEY,
            quest_id INTEGER,
            guild_id BIGINT NOT NULL,
            discord_id BIGINT NOT NULL,
            completed_at TIMESTAMP DEFAULT NOW(),
            validated_by BIGINT,
            UNIQUE(quest_id, discord_id)
        )
    """),
    ("oaths", """
        CREATE TABLE IF NOT EXISTS oaths (
            id SERIAL PRIMARY KEY,
            guild_id BIGINT NOT NULL,
            discord_id BIGINT NOT NULL,
            oath_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """),
]

@app.on_event("startup")
async def startup():
    global pool
    print("🔌 Connexion à la DB...")
    try:
        pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
        print("✅ Pool créé")
    except Exception as e:
        print(f"❌ ERREUR POOL: {e}")
        traceback.print_exc()
        raise

    async with pool.acquire() as conn:
        for table_name, sql in TABLES:
            try:
                await conn.execute(sql)
                print(f"✅ Table '{table_name}' OK")
            except Exception as e:
                print(f"❌ ERREUR table '{table_name}': {e}")
                traceback.print_exc()

    print("🎉 Toutes les tables initialisées")

@app.get("/")
async def root():
    return {"name": "Plaid API", "version": "2.1", "status": "⚖️ En service"}

@app.get("/health")
async def health():
    try:
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"db": "ok", "status": "healthy"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/api/stats/{guild_id}")
async def get_stats(guild_id: int):
    try:
        async with pool.acquire() as conn:
            users    = await conn.fetchval("SELECT COUNT(*) FROM users WHERE guild_id=$1", guild_id) or 0
            trials   = await conn.fetchval("SELECT COUNT(*) FROM trials WHERE guild_id=$1", guild_id) or 0
            laws     = await conn.fetchval("SELECT COUNT(*) FROM laws WHERE guild_id=$1", guild_id) or 0
            quests   = await conn.fetchval("SELECT COUNT(*) FROM quests WHERE guild_id=$1 AND active=TRUE", guild_id) or 0
            guildes  = await conn.fetchval("SELECT COUNT(*) FROM guilds_rpg WHERE guild_id=$1", guild_id) or 0
            bounties = await conn.fetchval("SELECT COUNT(*) FROM bounties WHERE guild_id=$1 AND active=TRUE", guild_id) or 0
        return {"users": users, "trials": trials, "laws": laws, "quests": quests, "guildes": guildes, "bounties": bounties}
    except Exception as e:
        print(f"❌ /api/stats error: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/leaderboard/{guild_id}")
async def get_leaderboard(guild_id: int, sort: str = "best", limit: int = 10):
    try:
        order = {
            "best":   "reputation DESC",
            "worst":  "reputation ASC",
            "gold":   "gold DESC",
            "trials": "total_trials DESC"
        }.get(sort, "reputation DESC")
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"SELECT * FROM users WHERE guild_id=$1 ORDER BY {order} LIMIT $2",
                guild_id, limit
            )
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"❌ /api/leaderboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/{guild_id}/{discord_id}")
async def get_user(guild_id: int, discord_id: int):
    try:
        async with pool.acquire() as conn:
            user  = await conn.fetchrow("SELECT * FROM users WHERE guild_id=$1 AND discord_id=$2", guild_id, discord_id)
            cases = await conn.fetch("SELECT * FROM casier WHERE guild_id=$1 AND discord_id=$2 ORDER BY created_at DESC", guild_id, discord_id)
            oaths = await conn.fetch("SELECT * FROM oaths WHERE guild_id=$1 AND discord_id=$2 ORDER BY created_at DESC LIMIT 5", guild_id, discord_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {"user": dict(user), "casier": [dict(c) for c in cases], "serments": [dict(o) for o in oaths]}
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ /api/user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trials/{guild_id}")
async def get_trials(guild_id: int, limit: int = 20):
    try:
        async with pool.acquire() as conn:
            trials = await conn.fetch(
                "SELECT * FROM trials WHERE guild_id=$1 ORDER BY created_at DESC LIMIT $2",
                guild_id, limit
            )
        return [dict(t) for t in trials]
    except Exception as e:
        print(f"❌ /api/trials error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/laws/{guild_id}")
async def get_laws(guild_id: int):
    try:
        async with pool.acquire() as conn:
            laws = await conn.fetch("SELECT * FROM laws WHERE guild_id=$1 ORDER BY id", guild_id)
        return [dict(l) for l in laws]
    except Exception as e:
        print(f"❌ /api/laws error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/quests/{guild_id}")
async def get_quests(guild_id: int):
    try:
        async with pool.acquire() as conn:
            quests = await conn.fetch(
                "SELECT * FROM quests WHERE guild_id=$1 AND active=TRUE ORDER BY created_at DESC",
                guild_id
            )
        return [dict(q) for q in quests]
    except Exception as e:
        print(f"❌ /api/quests error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/guildes/{guild_id}")
async def get_guildes(guild_id: int):
    try:
        async with pool.acquire() as conn:
            guildes = await conn.fetch(
                "SELECT * FROM guilds_rpg WHERE guild_id=$1 ORDER BY array_length(members,1) DESC NULLS LAST",
                guild_id
            )
        return [dict(g) for g in guildes]
    except Exception as e:
        print(f"❌ /api/guildes error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bounties/{guild_id}")
async def get_bounties(guild_id: int):
    try:
        async with pool.acquire() as conn:
            bounties = await conn.fetch(
                "SELECT * FROM bounties WHERE guild_id=$1 AND active=TRUE ORDER BY amount DESC",
                guild_id
            )
        return [dict(b) for b in bounties]
    except Exception as e:
        print(f"❌ /api/bounties error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
