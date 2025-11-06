"""Точка входа для веб-сайта"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv

from src.web.routes import router

# Загружаем переменные окружения
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Startup
    print("Веб-сервер запущен")
    yield
    # Shutdown
    print("Веб-сервер остановлен")


# Создаем приложение
app = FastAPI(
    title="VPN Link Converter",
    description="Конвертер VPN ссылок в конфигурации sing-box",
    version="0.1.0",
    lifespan=lifespan
)

# Подключаем роуты
app.include_router(router)


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("WEB_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_PORT", "8000"))
    
    uvicorn.run(app, host=host, port=port)

