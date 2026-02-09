import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Вставь свой токен сюда
BOT_TOKEN = "8315806058:AAHF4M2BXcO7D2nvnfDlzJwcqCHDQ9mBoI0"  # <-- ЗАМЕНИ

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("🎮 Добро пожаловать в RE:ALITY: Core\n\nНапиши /play чтобы начать")

@dp.message(Command("play"))
async def cmd_play(message: types.Message):
    await message.answer(
        "📊 Твой персонаж:\n💰 5000₽ | ❤️ 100% | 📅 День 1\n\nЧто делаем?",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="💼 Работать")],
                [types.KeyboardButton(text="🍜 Есть")],
                [types.KeyboardButton(text="😴 Спать")]
            ],
            resize_keyboard=True
        )
    )

@dp.message()
async def handle_text(message: types.Message):
    await message.answer(f"Ты написал: {message.text}. Пока я не понимаю команд, используй /play")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
