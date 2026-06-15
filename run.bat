@echo off
chcp 65001 > nul
title Hamrakar Job Bot

if not exist ".env" (
    copy .env.example .env > nul
    echo.
    echo [!] Notepad will open - fill in BOT_TOKEN and ADMIN_IDS then SAVE and CLOSE.
    echo.
    start /wait notepad.exe .env
)

echo Installing packages...
echo.

REM Try primary mirror first
echo Attempting to install from official PyPI...
pip install --default-timeout=1000 aiohttp jdatetime python-dotenv

if errorlevel 1 (
    echo.
    echo Retrying with alternative mirror...
    pip install --default-timeout=1000 -i https://pypi.org/simple/ aiohttp jdatetime python-dotenv
)

if errorlevel 1 (
    echo.
    echo ERROR: Could not install packages.
    echo Please check your internet connection and try again.
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ Packages installed successfully!
echo.
echo Starting bot...
echo.

python bot.py

pause
