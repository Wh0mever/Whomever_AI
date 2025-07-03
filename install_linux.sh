#!/bin/bash

echo "🚀 Полная автоматическая установка WHOMEVER AI Bot на Linux VPS"
echo "=============================================================="

# Проверка что скрипт запущен с правами root или sudo
if [ "$EUID" -ne 0 ]; then
    echo "❌ Этот скрипт нужно запускать с правами root или sudo"
    echo "Используйте: sudo bash install_linux.sh"
    exit 1
fi

# Получить текущую директорию (где находится скрипт)
CURRENT_DIR=$(pwd)
echo "📍 Рабочая директория: $CURRENT_DIR"

echo "📦 Обновление системных пакетов..."
apt-get update -y

echo "🔧 Установка системных зависимостей..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    ffmpeg \
    libmagic1 \
    libmagic-dev \
    git \
    wget \
    curl \
    libportaudio2 \
    libportaudiocpp0 \
    portaudio19-dev \
    libasound2-dev \
    libsndfile1 \
    nano

echo "🐍 Создание виртуального окружения..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

echo "🔄 Активация виртуального окружения..."
source venv/bin/activate

echo "⬆️ Обновление pip..."
pip install --upgrade pip setuptools wheel

echo "📚 Установка Python зависимостей..."
pip install -r requirements-linux.txt

echo "🛠️ Создание systemd сервиса..."

# Создать файл сервиса
cat > /etc/systemd/system/whomever-bot.service << EOF
[Unit]
Description=WHOMEVER AI Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$CURRENT_DIR
Environment=PATH=$CURRENT_DIR/venv/bin
ExecStart=$CURRENT_DIR/venv/bin/python run_bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Systemd сервис создан: /etc/systemd/system/whomever-bot.service"

echo "🔄 Перезагрузка systemd и включение сервиса..."
systemctl daemon-reload
systemctl enable whomever-bot.service

echo "⚙️ Проверка .env файла..."
if [ ! -f ".env" ]; then
    echo "📝 Создание шаблона .env файла..."
    cat > .env << EOF
# Токены API - ОБЯЗАТЕЛЬНО ЗАПОЛНИТЕ!
TELEGRAM_BOT_TOKEN=7946779330:AAEB6vg5AKgqJ249yn1hKCI3JRisYkPT8lo
OPENAI_API_KEY=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
BOT_ADMIN_ID=1914567632
EOF
    echo "⚠️ ВНИМАНИЕ: Необходимо настроить .env файл с вашими токенами!"
    echo "Отредактируйте файл: nano .env"
    echo ""
    read -p "❓ Хотите отредактировать .env файл сейчас? (y/n): " edit_env
    if [[ $edit_env =~ ^[Yy]$ ]]; then
        nano .env
    fi
else
    echo "✅ Файл .env уже существует"
fi

echo ""
echo "🚀 Запуск бота..."
systemctl start whomever-bot.service

# Ждем немного чтобы сервис запустился
sleep 3

echo "📊 Проверка статуса сервиса..."
systemctl status whomever-bot.service --no-pager -l

echo ""
echo "🎉 Установка завершена!"
echo "===================="
echo ""
echo "📋 Управление ботом:"
echo "• Запустить:     sudo systemctl start whomever-bot.service"
echo "• Остановить:    sudo systemctl stop whomever-bot.service"
echo "• Перезапустить: sudo systemctl restart whomever-bot.service"
echo "• Посмотреть логи: sudo journalctl -u whomever-bot.service -f"
echo "• Статус:        sudo systemctl status whomever-bot.service"
echo ""
echo "📝 Настройка:"
echo "• Редактировать .env: nano .env"
echo "• После изменения .env: sudo systemctl restart whomever-bot.service"
echo ""
echo "🔍 Проверить логи запуска:"
echo "sudo journalctl -u whomever-bot.service -f --since='1 minute ago'" 