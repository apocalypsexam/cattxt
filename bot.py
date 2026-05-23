import asyncio
import os
from datetime import datetime

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = "8782578238:AAE74KCzODZRAzstGlYv0ahYnIrtyBfJzVc"
DB_NAME = "quotes.db"

if not TOKEN:
    raise RuntimeError("TOKEN environment variable is not set")

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
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
        await db.commit()


async def add_quote(chat_id: int, user_id: int, username: str, quote: str, created_at: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT INTO quotes (chat_id, user_id, username, quote, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (chat_id, user_id, username, quote, created_at),
        )
        await db.commit()


async def get_quotes_by_chat_and_user(chat_id: int, user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT id, quote, created_at
            FROM quotes
            WHERE chat_id = ? AND user_id = ?
            ORDER BY id DESC
            """,
            (chat_id, user_id),
        )
        return await cursor.fetchall()


async def get_quote_by_id(chat_id: int, quote_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            """
            SELECT username, quote, created_at
            FROM quotes
            WHERE chat_id = ? AND id = ?
            """,
            (chat_id, quote_id),
        )
        return await cursor.fetchone()


@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Бот запущен.\n\n"
        "Команды:\n"
        "/save — сохранить reply-сообщение\n"
        "/list — показать сохранённые сообщения кнопками\n"
        "/exp — показать случайную сохранённую цитату\n"
    )


@dp.message(Command("save"))
async def save_quote(message: Message):
    if not message.reply_to_message:
        await message.answer("Ответь командой /save на нужное сообщение.")
        return

    target_message = message.reply_to_message
    if not target_message.text:
        await message.answer("Можно сохранять только текстовые сообщения.")
        return

    user = target_message.from_user
    if not user:
        await message.answer("Пользователь не найден.")
        return

    created_at = datetime.now().strftime("%d.%m.%Y %H:%M")

    await add_quote(
        chat_id=message.chat.id,
        user_id=user.id,
        username=user.username or user.full_name,
        quote=target_message.text,
        created_at=created_at,
    )

    await message.answer(
        f"Сообщение от @{user.username or user.full_name} сохранено только в этом чате."
    )


@dp.message(Command("list"))
async def list_quotes(message: Message):
    if not message.reply_to_message:
        await message.answer("Ответь командой /list на сообщение пользователя.")
        return

    user = message.reply_to_message.from_user
    if not user:
        await message.answer("Пользователь не найден.")
        return

    quotes = await get_quotes_by_chat_and_user(message.chat.id, user.id)
    if not quotes:
        await message.answer("В этом чате сохранённых сообщений нет.")
        return

    builder = InlineKeyboardBuilder()
    for quote_id, quote_text, created_at in quotes:
        short_text = quote_text[:25] + ("..." if len(quote_text) > 25 else "")
        builder.button(
            text=f"{created_at} | {short_text}",
            callback_data=f"quote:{message.chat.id}:{quote_id}",
        )

    builder.adjust(1)

    await message.answer(
        f"Сохранённые сообщения для @{user.username or user.full_name} в этом чате:",
        reply_markup=builder.as_markup(),
    )


@dp.callback_query(F.data.startswith("quote:"))
async def show_quote(callback: CallbackQuery):
    if not callback.data:
        await callback.answer("Ошибка данных", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Ошибка данных", show_alert=True)
        return

    chat_id = int(parts[1])
    quote_id = int(parts[2])

    data = await get_quote_by_id(chat_id, quote_id)
    if not data:
        await callback.answer("Сообщение не найдено", show_alert=True)
        return

    username, quote, created_at = data
    await callback.message.answer(
        f"@{username}\n\n"
        f"📅 {created_at}\n\n"
        f"💬 {quote}"
    )
    await callback.answer()


async def main():
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())