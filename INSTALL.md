# 🚀 Установка WHOMEVER AI Bot

Этот бот поддерживает работу на Windows, Linux (включая VPS) и macOS.

## 📋 Требования

- Python 3.9 или выше
- Git
- Интернет соединение

## 🎯 Быстрая установка

### Универсальный способ (Рекомендуется)

```bash
# Клонировать репозиторий
git clone https://github.com/wh0mever/Whomever_AI.git
cd Whomever_AI

# Запустить универсальный установщик
python install.py
```

Скрипт автоматически определит вашу платформу и установит нужные зависимости.

---

## 🖥️ Windows

### Способ 1: Автоматическая установка
```cmd
# Запустить batch файл
install_windows.bat
```

### Способ 2: Ручная установка
```cmd
# Создать виртуальное окружение
python -m venv venv

# Активировать
venv\Scripts\activate.bat

# Установить зависимости
pip install -r requirements-windows.txt
```

### Дополнительные требования для Windows:
- **FFmpeg**: Скачайте с https://ffmpeg.org/download.html и добавьте в PATH
- **Microsoft C++ Build Tools**: Для компиляции некоторых пакетов

---

## 🐧 Linux / VPS

### Способ 1: Автоматическая установка
```bash
# Запустить скрипт с правами root
sudo bash install_linux.sh
```

### Способ 2: Ручная установка

#### Системные зависимости:
```bash
# Ubuntu/Debian
sudo apt-get update -y
sudo apt-get install -y \
    python3 python3-pip python3-venv python3-dev \
    build-essential ffmpeg libmagic1 libmagic-dev \
    libportaudio2 portaudio19-dev libasound2-dev libsndfile1

# CentOS/RHEL/Fedora
sudo yum install -y python3 python3-pip python3-devel \
    gcc ffmpeg file-devel portaudio-devel alsa-lib-devel libsndfile-devel
```

#### Python зависимости:
```bash
# Создать виртуальное окружение
python3 -m venv venv

# Активировать
source venv/bin/activate

# Установить зависимости
pip install -r requirements-linux.txt
```

---

## 🍎 macOS

### Системные зависимости:
```bash
# Через Homebrew (рекомендуется)
brew install ffmpeg libmagic portaudio

# Создать виртуальное окружение
python3 -m venv venv

# Активировать
source venv/bin/activate

# Установить зависимости (используйте Linux версию)
pip install -r requirements-linux.txt
```

---

## ⚙️ Настройка

### 1. Создайте файл `.env`:
```env
# Основные токены API
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
BOT_ADMIN_ID=your_telegram_admin_id
```

### 2. Получите токены:

#### Telegram Bot Token:
1. Найдите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте токен

#### OpenAI API Key:
1. Зайдите на https://platform.openai.com/
2. Создайте API ключ в разделе API Keys
3. Скопируйте ключ

---

## 🏃 Запуск

### Windows:
```cmd
# Активировать виртуальное окружение
venv\Scripts\activate.bat

# Запустить бота
python run_bot.py
```

### Linux/macOS:
```bash
# Активировать виртуальное окружение
source venv/bin/activate

# Запустить бота
python run_bot.py
```

---

## 🛠️ Автозапуск на Linux VPS

### Создание systemd сервиса:

1. Создайте файл сервиса:
```bash
sudo nano /etc/systemd/system/whomever-bot.service
```

2. Добавьте содержимое:
```ini
[Unit]
Description=WHOMEVER AI Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/path/to/Whomever_AI
Environment=PATH=/path/to/Whomever_AI/venv/bin
ExecStart=/path/to/Whomever_AI/venv/bin/python run_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Активируйте сервис:
```bash
sudo systemctl daemon-reload
sudo systemctl enable whomever-bot.service
sudo systemctl start whomever-bot.service

# Проверить статус
sudo systemctl status whomever-bot.service
```

---

## 🔍 Решение проблем

### Проблемы с установкой на Linux:
- Убедитесь что у вас есть права sudo
- Проверьте что все системные пакеты установлены
- Попробуйте обновить pip: `pip install --upgrade pip`

### Проблемы с аудио:
- Linux: Установите `sudo apt-get install portaudio19-dev`
- Windows: Установите Microsoft C++ Build Tools
- Проверьте что FFmpeg в PATH: `ffmpeg -version`

### Проблемы с magic:
- Linux: `sudo apt-get install libmagic1 libmagic-dev`
- Windows: Пакет `python-magic-bin` должен решить проблему

### Логи:
Логи сохраняются в папке `logs/`. Проверьте файл `bot.log` для диагностики.

---

## 📞 Поддержка

Если возникли проблемы:
1. Проверьте логи в папке `logs/`
2. Убедитесь что все токены в `.env` корректны
3. Проверьте что все системные зависимости установлены
4. Создайте issue в GitHub репозитории 