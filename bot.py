import os
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎮 Играть", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    await update.message.reply_text(
        "👋 Добро пожаловать в *REALITY: Профессии*!\n\n"
        "Тапай, прокачивайся и открывай профессии будущего.\n"
        "Нажми кнопку ниже, чтобы начать:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *REALITY: Профессии*\n\n"
        "• Тапай экран — зарабатывай монеты и XP\n"
        "• Повышай уровень — получай токены\n"
        "• Открывай профессии из 4 сфер: IT, Engineering, Medicine, Science\n"
        "• Улучшай клик, выносливость и регенерацию\n"
        "• Проходи симуляции профессий\n\n"
        "Команды:\n"
        "/start — запустить игру\n"
        "/help — это сообщение",
        parse_mode="Markdown",
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.run_polling()


if __name__ == "__main__":
    main()
