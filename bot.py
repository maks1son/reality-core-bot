import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

BOT_TOKEN = os.getenv("BOT_TOKEN", "ТВОЙ_ТОКЕН")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-service.onrender.com")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(
                text="🎮 Открыть RE:ALITY", 
                web_app=types.WebAppInfo(url=WEBAPP_URL)
            )]
        ]
    )
    await message.answer(
        "Добро пожаловать в RE:ALITY: Core\n\n"
        "Нажми кнопку, чтобы начать игру:",
        reply_markup=kb
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
