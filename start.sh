#!/bin/bash
# Запускаем и бота, и веб-сервер

python bot.py &
uvicorn main:app --host 0.0.0.0 --port $PORT
