# 🚀 Быстрый старт на VPS (ПОЛНОСТЬЮ АВТОМАТИЧЕСКИЙ)

## 📝 Сверх-простая установка в 4 команды

### 1. Подключитесь к VPS
```bash
ssh root@your_vps_ip
```

### 2. Клонируйте репозиторий
```bash
cd /home
git clone https://github.com/yourusername/Whomever_AI.git
cd Whomever_AI
```

### 3. Запустите автоматическую установку
```bash
sudo bash install_linux.sh
```
**ЭТО ВСЁ!** Скрипт автоматически:
- ✅ Установит все системные зависимости
- ✅ Создаст виртуальное окружение
- ✅ Установит Python пакеты  
- ✅ Создаст systemd сервис
- ✅ Запустит бота
- ✅ Предложит настроить .env файл

### 4. Настройте токены (если нужно)
```bash
nano .env
```

Добавьте ваши токены:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
OPENAI_API_KEY=your_openai_key_here
BOT_ADMIN_ID=your_telegram_admin_id_here
```

После редактирования .env:
```bash
sudo systemctl restart whomever-bot.service
```

---

## 📋 Управление ботом

```bash
# Запустить
sudo systemctl start whomever-bot.service

# Остановить
sudo systemctl stop whomever-bot.service

# Перезапустить
sudo systemctl restart whomever-bot.service

# Посмотреть логи в реальном времени
sudo journalctl -u whomever-bot.service -f

# Посмотреть статус
sudo systemctl status whomever-bot.service

# Отключить автозапуск
sudo systemctl disable whomever-bot.service

# Включить автозапуск
sudo systemctl enable whomever-bot.service
```

---

## 🔧 Что делает автоматический скрипт?

1. **Системные зависимости:** `python3`, `ffmpeg`, `libmagic`, `portaudio`, etc.
2. **Python окружение:** Создает `venv` и устанавливает все пакеты
3. **Systemd сервис:** Автоматически создает и настраивает сервис
4. **Автозапуск:** Бот запускается автоматически при перезагрузке сервера
5. **Шаблон .env:** Создает файл с примерами токенов
6. **Запуск бота:** Сразу запускает бота как сервис

---

## 🔍 Проверка работы

### Сразу после установки:
```bash
# Быстрая проверка всего состояния бота
bash check_bot.sh

# Или отдельные команды:
# Проверить статус
sudo systemctl status whomever-bot.service

# Посмотреть последние логи
sudo journalctl -u whomever-bot.service --since='1 minute ago'
```

### Если бот не запустился:
```bash
# Проверить что .env настроен
cat .env

# Перезапустить после настройки .env
sudo systemctl restart whomever-bot.service

# Посмотреть ошибки
sudo journalctl -u whomever-bot.service -f
```

---

## 🔧 Устранение проблем

### Переустановка:
```bash
# Остановить сервис
sudo systemctl stop whomever-bot.service

# Удалить виртуальное окружение
rm -rf venv

# Запустить установку заново
sudo bash install_linux.sh
```

### Обновление бота:
```bash
# Остановить сервис
sudo systemctl stop whomever-bot.service

# Обновить код
git pull

# Обновить зависимости (если нужно)
source venv/bin/activate
pip install -r requirements-linux.txt

# Запустить сервис
sudo systemctl start whomever-bot.service
```

### Полное удаление:
```bash
# Остановить и отключить сервис
sudo systemctl stop whomever-bot.service
sudo systemctl disable whomever-bot.service

# Удалить файл сервиса
sudo rm /etc/systemd/system/whomever-bot.service
sudo systemctl daemon-reload

# Удалить папку проекта
rm -rf /home/Whomever_AI
```

---

## 🎯 Преимущества автоматической установки

✅ **Один скрипт** - всё настраивается автоматически  
✅ **Systemd сервис** - автозапуск при перезагрузке  
✅ **Логирование** - все логи через `journalctl`  
✅ **Управление** - простые команды `systemctl`  
✅ **Безопасность** - изоляция в виртуальном окружении  
✅ **Мониторинг** - автоматический перезапуск при сбоях  

**Время установки:** ~2-5 минут (в зависимости от скорости интернета)

---

## 🩺 Диагностика

### Быстрая проверка состояния бота:
```bash
bash check_bot.sh
```

Этот скрипт проверит:
- Статус systemd сервиса
- Последние логи
- Настройку .env файла
- Виртуальное окружение
- Системные зависимости

---

**Важно:** Замените `your_vps_ip`, `your_bot_token_here`, `your_openai_key_here`, `your_telegram_admin_id_here` на реальные значения! 