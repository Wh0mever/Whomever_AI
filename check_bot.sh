#!/bin/bash

echo "🔍 ПРОВЕРКА СОСТОЯНИЯ WHOMEVER AI BOT"
echo "====================================="

# Проверка статуса сервиса
echo "📊 Статус systemd сервиса:"
systemctl status whomever-bot.service --no-pager -l

echo ""
echo "📝 Последние 10 строк логов:"
journalctl -u whomever-bot.service -n 10 --no-pager

echo ""
echo "🔧 Проверка .env файла:"
if [ -f ".env" ]; then
    echo "✅ Файл .env существует"
    if grep -q "your_telegram_bot_token_here\|your_openai_api_key_here\|your_telegram_admin_id_here" .env 2>/dev/null; then
        echo "⚠️ ВНИМАНИЕ: В .env файле есть шаблонные значения - нужно настроить токены!"
        echo "Запустите: nano .env"
    else
        echo "✅ Файл .env настроен"
    fi
else
    echo "❌ Файл .env не найден!"
fi

echo ""
echo "🐍 Проверка виртуального окружения:"
if [ -d "venv" ]; then
    echo "✅ Виртуальное окружение существует"
    
    # Проверка основных пакетов
    if ./venv/bin/python -c "import aiogram; print('✅ aiogram:', aiogram.__version__)" 2>/dev/null; then
        :
    else
        echo "❌ aiogram не установлен"
    fi
    
    if ./venv/bin/python -c "import openai; print('✅ openai:', openai.__version__)" 2>/dev/null; then
        :
    else
        echo "❌ openai не установлен"
    fi
else
    echo "❌ Виртуальное окружение не найдено!"
fi

echo ""
echo "🔧 Проверка системных зависимостей:"
if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg установлен: $(ffmpeg -version 2>&1 | head -n1)"
else
    echo "❌ FFmpeg не найден"
fi

if command -v python3 &> /dev/null; then
    echo "✅ Python3: $(python3 --version)"
else
    echo "❌ Python3 не найден"
fi

echo ""
echo "📋 Команды управления:"
echo "• Перезапустить: sudo systemctl restart whomever-bot.service"
echo "• Посмотреть логи: sudo journalctl -u whomever-bot.service -f"
echo "• Остановить: sudo systemctl stop whomever-bot.service"
echo "• Запустить: sudo systemctl start whomever-bot.service"
echo "• Настроить .env: nano .env" 