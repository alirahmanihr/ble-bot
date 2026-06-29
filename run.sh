#!/bin/bash
if [ ! -f .env ]; then
    cp .env.example .env
    echo "فایل .env ایجاد شد - توکن را وارد کنید"
    nano .env
fi
pip3 install -r requirements.txt
python3 bot.py
