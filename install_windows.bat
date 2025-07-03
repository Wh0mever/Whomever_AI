@echo off
chcp 65001 > nul

echo 🚀 Установка WHOMEVER AI Bot на Windows
echo =======================================

echo 🐍 Создание виртуального окружения...
if not exist "venv" (
    python -m venv venv
)

echo 🔄 Активация виртуального окружения...
call venv\Scripts\activate.bat

echo ⬆️ Обновление pip...
python -m pip install --upgrade pip setuptools wheel

echo 📚 Установка Python зависимостей...
pip install -r requirements-windows.txt

echo ✅ Установка завершена!
echo.
echo 🎯 Для запуска бота:
echo 1. Убедитесь что .env файл настроен с токенами
echo 2. Активируйте виртуальное окружение: venv\Scripts\activate.bat
echo 3. Запустите бота: python run_bot.py
echo.
echo 📝 ВАЖНО: Убедитесь что установлен FFmpeg:
echo https://ffmpeg.org/download.html
echo.
pause 