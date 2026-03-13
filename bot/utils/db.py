import asyncpg
import os

pool = None

async def init_db():
    global pool
    pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
    
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                discord_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                reputation INT DEFAULT 100,
                total_trials INT DEFAULT 0,
                guilty_count INT DEFAULT 0,
                innocent_count INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(discord_id, guild_id)
            );
            
            CREATE TABLE IF NOT EXISTS trials (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                accuser_id BIGINT NOT NULL,
                accused_id BIGINT NOT NULL,
                reason TEXT NOT NULL,
                law_id INT,
                status TEXT DEFAULT 'en_cours',
                votes_guilty INT DEFAULT 0,
                votes_innocent INT DEFAULT 0,
                verdict TEXT,
                channel_id BIGINT,
                message_id BIGINT,
                created_at TIMESTAMP DEFAULT NOW(),
                ended_at TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS casier (
                id SERIAL PRIMARY KEY,
                discord_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                trial_id INT REFERENCES trials(id),
                offense TEXT NOT NULL,
                punishment TEXT,
                rep_change INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            );
            
            CREATE TABLE IF NOT EXISTS laws (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                punishment TEXT,
                rep_penalty INT DEFAULT 10,
                created_by BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            );
            
            CREATE TABLE IF NOT EXISTS votes (
                id SERIAL PRIMARY KEY,
                trial_id INT REFERENCES trials(id),
                voter_id BIGINT NOT NULL,
                vote TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(trial_id, voter_id)
            );
        """)
    print("✅ Base de données initialisée")

async def get_pool():
    if pool is None:
        await init_db()
    return pool
