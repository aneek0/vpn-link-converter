"""Точка входа для веб-сайта"""
import os
from fastapi import FastAPI
from dotenv import load_dotenv

from src.web.routes import router

# Загружаем переменные окружения
load_dotenv()

# Создаем приложение
app = FastAPI(
    title="VPN Link Converter",
    description="Конвертер VPN ссылок в конфигурации sing-box",
    version="0.1.0"
)

# Подключаем роуты
app.include_router(router)


@app.on_event("startup")
async def startup():
    """Действия при запуске"""
    print("Веб-сервер запущен")


@app.on_event("shutdown")
async def shutdown():
    """Действия при остановке"""
    print("Веб-сервер остановлен")


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("WEB_HOST", "0.0.0.0")
    port = int(os.getenv("WEB_PORT", "8000"))
    
    uvicorn.run(app, host=host, port=port)

