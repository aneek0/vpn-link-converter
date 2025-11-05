"""Точка входа для Telegram бота"""
import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from src.bot.handlers import router

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def set_bot_commands(bot: Bot) -> None:
    """Установить команды бота"""
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="help", description="Показать справку"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Команды бота установлены")


async def on_startup(bot: Bot) -> None:
    """Действия при запуске бота"""
    await set_bot_commands(bot)
    logger.info("Бот запущен")


async def on_shutdown(bot: Bot) -> None:
    """Действия при остановке бота"""
    logger.info("Бот остановлен")


async def main() -> None:
    """Главная функция"""
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN не установлен в переменных окружения")
    
    # Создаем бота
    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Создаем диспетчер
    dp = Dispatcher()
    dp.include_router(router)
    
    # Регистрируем хуки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    try:
        # Запускаем polling
        logger.info("Запуск бота...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")

