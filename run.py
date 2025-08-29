import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Добавляем текущую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

from bot.telegram_calendar_bot import TelegramCalendarBot


def setup_logging():
    """Настройка логирования"""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()

    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Главная функция"""
    print("🤖 Запуск Telegram Calendar Bot...")

    # Настройка логирования
    setup_logging()
    logger = logging.getLogger(__name__)

    # Проверка переменных окружения
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("❌ Не указан TELEGRAM_BOT_TOKEN в переменных окружения!")
        print("Создайте файл .env с токеном бота:")
        print("TELEGRAM_BOT_TOKEN=ваш_токен_здесь")
        sys.exit(1)

    # Проверка файла учетных данных Google
    if not os.path.exists('service-account-credentials.json'):
        logger.warning("⚠️  Файл credentials.json не найден!")
        print("Скачайте credentials.json из Google Cloud Console")
        print("и поместите его в директорию с ботом")

    try:
        # Создание и запуск бота
        bot = TelegramCalendarBot()
        logger.info("✅ Бот успешно инициализирован")
        bot.run()

    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
