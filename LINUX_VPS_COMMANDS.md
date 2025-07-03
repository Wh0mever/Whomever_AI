# 🐧 Linux VPS - Команды для WHOMEVER AI Bot

## 🚀 Установка (1 команда)
```bash
sudo bash install_linux.sh
```

## 🔧 Управление ботом
```bash
# Запустить
sudo systemctl start whomever-bot.service

# Остановить
sudo systemctl stop whomever-bot.service

# Перезапустить
sudo systemctl restart whomever-bot.service

# Статус
sudo systemctl status whomever-bot.service

# Включить автозапуск
sudo systemctl enable whomever-bot.service

# Отключить автозапуск
sudo systemctl disable whomever-bot.service
```

## 📝 Логи
```bash
# Логи в реальном времени
sudo journalctl -u whomever-bot.service -f

# Последние 50 строк
sudo journalctl -u whomever-bot.service -n 50

# Логи за последние 10 минут
sudo journalctl -u whomever-bot.service --since='10 minutes ago'
```

## ⚙️ Настройка
```bash
# Редактировать .env
nano .env

# После изменения .env - перезапустить бота
sudo systemctl restart whomever-bot.service

# Проверить состояние всех компонентов
bash check_bot.sh
```

## 🔍 Диагностика
```bash
# Комплексная проверка
bash check_bot.sh

# Проверить процессы
ps aux | grep python

# Проверить порты
netstat -tulpn | grep python

# Проверить диск
df -h

# Проверить память
free -h
```

## 📦 Обновление
```bash
# Остановить бота
sudo systemctl stop whomever-bot.service

# Обновить код
git pull

# Установить новые зависимости (если есть)
source venv/bin/activate
pip install -r requirements-linux.txt

# Запустить бота
sudo systemctl start whomever-bot.service
```

## 🗑️ Удаление
```bash
# Остановить и отключить сервис
sudo systemctl stop whomever-bot.service
sudo systemctl disable whomever-bot.service

# Удалить сервис
sudo rm /etc/systemd/system/whomever-bot.service
sudo systemctl daemon-reload

# Удалить файлы (ОСТОРОЖНО!)
rm -rf /home/Whomever_AI
```

---

**💡 Tip:** Добавьте этот файл в закладки для быстрого доступа к командам! 