"""Синхронный парсер подписок VPN серверов"""
import base64
import re
from typing import List
from urllib.parse import urlparse

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

# Импортируем функцию из основного модуля
from .subscription import is_subscription_url, extract_vpn_links


def download_subscription_sync(url: str) -> str:
    """Загружает содержимое подписки по URL (синхронно)"""
    if not HAS_HTTPX:
        raise ImportError("httpx не установлен. Установите: pip install httpx")
    
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def parse_subscription_sync(url_or_content: str) -> List[str]:
    """
    Парсит подписку VPN серверов и возвращает список ссылок (синхронно)
    
    Поддерживает:
    - Прямые ссылки на подписки (http/https) - загружает содержимое
    - Base64 закодированный контент
    - Простой текст с ссылками
    """
    content = url_or_content.strip()
    
    # Проверяем, является ли это URL подписки
    parsed = urlparse(content)
    if parsed.scheme in ['http', 'https']:
        # Загружаем содержимое подписки
        try:
            content = download_subscription_sync(content)
        except Exception as e:
            raise ValueError(f"Не удалось загрузить подписку: {e}")
    
    # Пробуем декодировать base64
    try:
        decoded = base64.b64decode(content + '==').decode('utf-8')
        # Если декодирование успешно, используем декодированный контент
        content = decoded
    except Exception:
        # Не base64, используем как есть
        pass
    
    # Извлекаем все VPN ссылки
    vpn_links = extract_vpn_links(content)
    
    return vpn_links

