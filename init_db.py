import aiosqlite

async def init_db():
    async with aiosqlite.connect('user.db') as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS user (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL,
                last_login DATETIME
            )
        ''')
        await db.commit()

# To run the init_db function
import asyncio
asyncio.run(init_db())