async def init_db():
    db = await aiosqlite.connect(DB_NAME)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            username TEXT,
            quote TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor = await db.execute("PRAGMA table_info(quotes)")
    columns = await cursor.fetchall()
    col_names = [col[1] for col in columns]

    if "chat_id" not in col_names:
        await db.execute("ALTER TABLE quotes ADD COLUMN chat_id INTEGER")
    if "username" not in col_names:
        await db.execute("ALTER TABLE quotes ADD COLUMN username TEXT")
    if "created_at" not in col_names:
        await db.execute("ALTER TABLE quotes ADD COLUMN created_at TEXT")

    await db.commit()
    await db.close()