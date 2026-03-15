#!/bin/bash
# Запускаем Telegram бота в фоне
python bot.py &

# Запускаем FastAPI сервер (основной процесс)
python main.py
