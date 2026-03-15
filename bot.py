"""
RE:ALITY — Telegram Bot
Отправляет кнопку для открытия Mini App
"""

import os
import logging
from telegram import Update, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start — отправить кнопку Mini App"""
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton(
            text="🎮 Открыть RE:ALITY",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )]],
        resize_keyboard=True
    )
    await update.message.reply_text(
        "⚔️ *RE:ALITY: Профессии*\n\n"
        "🎮 Пиксельная RPG-игра для профориентации!\n\n"
        "📱 Нажми кнопку ниже, чтобы начать:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(
        "📖 *RE:ALITY: Профессии*\n\n"
        "🎯 Тапай персонажа — зарабатывай монеты и XP\n"
        "🎫 Получай токены за уровни\n"
        "🏢 Открывай профессии и решай реальные кейсы\n"
        "⬆️ Покупай улучшения\n\n"
        "Нажми кнопку «Открыть RE:ALITY» для игры!",
        parse_mode="Markdown"
    )


def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен!")
        return
    if not WEBAPP_URL:
        logger.error("WEBAPP_URL не установлен!")
        return

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))

    logger.info("Бот запущен!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
