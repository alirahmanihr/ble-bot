@echo off
chcp 65001 > nul
title Hamrakar Bot
if not exist ".env" (
    copy .env.example .env
    notepad .env
    pause
)
pip install --default-timeout=300 aiohttp jdatetime python-dotenv
python bot.py
pause
