import asyncpg
import os

_pool = None

async def get_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
    return _pool

async def init_db():
    global _pool
    _pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
    async with _pool.acquire() as conn:

        # ── Tables de base ─────────────────────────────────────────────
        await conn.execute("""
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
            );

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
            );

            CREATE TABLE IF NOT EXISTS casier (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                discord_id BIGINT NOT NULL,
                infraction TEXT NOT NULL,
                verdict TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS laws (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                penalty TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS bounties (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                target_id BIGINT NOT NULL,
                issuer_id BIGINT NOT NULL,
                amount INTEGER NOT NULL,
                reason TEXT,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );

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
            );

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
            );

            CREATE TABLE IF NOT EXISTS quest_completions (
                id SERIAL PRIMARY KEY,
                quest_id INTEGER,
                guild_id BIGINT NOT NULL,
                discord_id BIGINT NOT NULL,
                completed_at TIMESTAMP DEFAULT NOW(),
                validated_by BIGINT,
                UNIQUE(quest_id, discord_id)
            );

            CREATE TABLE IF NOT EXISTS oaths (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                discord_id BIGINT NOT NULL,
                oath_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # ── Migration : ajouter les colonnes manquantes si la table
        #    users existait déjà sans elles ────────────────────────────
        migrations = [
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS wins INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS losses INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS gold INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS badges TEXT[] DEFAULT '{}'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS title TEXT DEFAULT 'Citoyen'",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS guild_name TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS total_trials INTEGER DEFAULT 0",
        ]
        for sql in migrations:
            try:
                await conn.execute(sql)
            except Exception as e:
                print(f"Migration warning (ignoré): {e}")

    print("✅ Base de données initialisée")
