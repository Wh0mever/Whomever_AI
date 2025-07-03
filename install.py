#!/usr/bin/env python3
"""
Универсальный скрипт установки WHOMEVER AI Bot
Поддерживает Windows, Linux, macOS
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

def run_command(command, shell=False):
    """Выполнить команду и вернуть результат"""
    try:
        result = subprocess.run(
            command.split() if not shell else command, 
            shell=shell, 
            capture_output=True, 
            text=True, 
            check=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def check_python_version():
    """Проверить версию Python"""
    version = sys.version_info
    print(f"🐍 Python версия: {version.major}.{version.minor}.{version.micro}")
    
    if version < (3, 9):
        print("❌ Требуется Python 3.9 или выше!")
        return False
    return True

def detect_platform():
    """Определить платформу"""
    system = platform.system().lower()
    print(f"💻 Операционная система: {system}")
    
    if system == "windows":
        return "windows"
    elif system == "linux":
        return "linux"
    elif system == "darwin":
        return "macos"
    else:
        print(f"⚠️ Неизвестная платформа: {system}, буду использовать Linux конфигурацию")
        return "linux"

def install_system_dependencies(platform_name):
    """Установить системные зависимости"""
    if platform_name == "linux":
        print("🔧 Установка системных зависимостей для Linux...")
        commands = [
            "sudo apt-get update -y",
            "sudo apt-get install -y python3-dev build-essential ffmpeg libmagic1 libmagic-dev libportaudio2 portaudio19-dev libasound2-dev libsndfile1"
        ]
        
        for cmd in commands:
            print(f"Выполняю: {cmd}")
            success, stdout, stderr = run_command(cmd, shell=True)
            if not success:
                print(f"⚠️ Предупреждение: {cmd} завершился с ошибкой: {stderr}")
    
    elif platform_name == "windows":
        print("🔧 Для Windows убедитесь что установлены:")
        print("   - FFmpeg: https://ffmpeg.org/download.html")
        print("   - Microsoft C++ Build Tools (для компиляции пакетов)")
    
    elif platform_name == "macos":
        print("🔧 Установка системных зависимостей для macOS...")
        if shutil.which("brew"):
            commands = [
                "brew install ffmpeg libmagic portaudio"
            ]
            for cmd in commands:
                print(f"Выполняю: {cmd}")
                run_command(cmd, shell=True)
        else:
            print("⚠️ Homebrew не найден. Установите FFmpeg и libmagic вручную")

def create_venv():
    """Создать виртуальное окружение"""
    if not Path("venv").exists():
        print("🐍 Создание виртуального окружения...")
        success, stdout, stderr = run_command("python -m venv venv")
        if not success:
            print(f"❌ Ошибка создания venv: {stderr}")
            return False
    else:
        print("✅ Виртуальное окружение уже существует")
    return True

def get_pip_command(platform_name):
    """Получить команду pip для платформы"""
    if platform_name == "windows":
        return "venv\\Scripts\\python.exe -m pip"
    else:
        return "venv/bin/python -m pip"

def install_requirements(platform_name):
    """Установить Python зависимости"""
    pip_cmd = get_pip_command(platform_name)
    
    # Определить файл requirements
    if platform_name == "windows":
        req_file = "requirements-windows.txt"
    else:
        req_file = "requirements-linux.txt"
    
    if not Path(req_file).exists():
        print(f"❌ Файл {req_file} не найден!")
        return False
    
    print("⬆️ Обновление pip...")
    success, stdout, stderr = run_command(f"{pip_cmd} install --upgrade pip setuptools wheel", shell=True)
    if not success:
        print(f"⚠️ Предупреждение при обновлении pip: {stderr}")
    
    print(f"📚 Установка Python зависимостей из {req_file}...")
    success, stdout, stderr = run_command(f"{pip_cmd} install -r {req_file}", shell=True)
    
    if success:
        print("✅ Зависимости установлены успешно!")
        return True
    else:
        print(f"❌ Ошибка установки зависимостей: {stderr}")
        return False

def main():
    """Основная функция"""
    print("🚀 Установка WHOMEVER AI Bot")
    print("=" * 40)
    
    # Проверки
    if not check_python_version():
        return 1
    
    platform_name = detect_platform()
    
    # Установка системных зависимостей
    install_system_dependencies(platform_name)
    
    # Создание venv
    if not create_venv():
        return 1
    
    # Установка Python пакетов
    if not install_requirements(platform_name):
        return 1
    
    print("\n🎉 Установка завершена успешно!")
    print("\n🎯 Для запуска бота:")
    print("1. Настройте .env файл с токенами")
    
    if platform_name == "windows":
        print("2. Активируйте виртуальное окружение: venv\\Scripts\\activate.bat")
    else:
        print("2. Активируйте виртуальное окружение: source venv/bin/activate")
    
    print("3. Запустите бота: python run_bot.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 