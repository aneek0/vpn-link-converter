"""Парсер подписок VPN серверов"""
import base64
import re
from typing import List, Optional
from urllib.parse import urlparse

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


async def download_subscription(url: str) -> str:
    """Загружает содержимое подписки по URL"""
    if not HAS_HTTPX:
        raise ImportError("httpx не установлен. Установите: pip install httpx")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


def parse_subscription(url_or_content: str, async_mode: bool = False) -> List[str]:
    """
    Парсит подписку VPN серверов и возвращает список ссылок
    
    Поддерживает:
    - Прямые ссылки на подписки (http/https)
    - Base64 закодированный контент
    - Простой текст с ссылками
    """
    content = url_or_content.strip()
    
    # Проверяем, является ли это URL подписки
    parsed = urlparse(content)
    if parsed.scheme in ['http', 'https']:
        if async_mode and HAS_HTTPX:
            # В async режиме можно загрузить, но функция должна быть async
            # Пока возвращаем пустой список, загрузка должна быть вызвана отдельно
            return []
        else:
            # В sync режиме возвращаем ссылку, загрузка должна быть вызвана отдельно
            return [content]
    
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


def extract_vpn_links(text: str) -> List[str]:
    """Извлекает все VPN ссылки из текста (включая HTML)"""
    # Паттерны для различных VPN протоколов
    # ВАЖНО: более длинные протоколы должны быть первыми, чтобы избежать ложных срабатываний
    # (например, 'ss://' может быть найдено внутри 'vless://' или 'vmess://')
    protocols = [
        'hysteria2://',
        'shadowsocks://',
        'socks5://',
        'wireguard://',
        'hy2://',
        'vless://',
        'vmess://',
        'trojan://',
        'socks://',
        'tuic://',
        'hysteria://',
        'ss://',
        'wg://',
    ]
    
    links = []
    
    # Если это HTML, извлекаем текст из HTML
    if '<html' in text.lower() or '<body' in text.lower() or '<div' in text.lower():
        try:
            # Пробуем использовать BeautifulSoup если доступен
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(text, 'html.parser')
                # Извлекаем текст из всех тегов
                text_from_html = soup.get_text()
                # Также ищем ссылки в атрибутах href и data-*
                for tag in soup.find_all(['a', 'div', 'span', 'pre', 'code', 'textarea', 'p', 'button']):
                    # Текст из тега
                    if tag.string:
                        text_from_html += '\n' + tag.string
                    # Атрибуты с ссылками
                    for attr in ['href', 'data-url', 'data-link', 'data-subscription']:
                        if tag.get(attr):
                            text_from_html += '\n' + tag.get(attr)
                text = text_from_html
            except ImportError:
                # Если BeautifulSoup недоступен, используем простой regex для удаления HTML тегов
                text = re.sub(r'<[^>]+>', '\n', text)
        except Exception:
            # Если парсинг HTML не удался, продолжаем с исходным текстом
            pass
    
    # Сначала пробуем декодировать base64 если содержимое похоже на base64
    # (длинная строка без пробелов и переносов строк, и не начинается с известных протоколов)
    text_stripped = text.strip()
    is_base64_like = (
        len(text_stripped) > 20 and 
        not ' ' in text_stripped and 
        '\n' not in text_stripped and 
        not text_stripped.startswith(('http://', 'https://', 'vless://', 'vmess://', 'trojan://', 'ss://', 'hy2://'))
    )
    
    if is_base64_like:
        try:
            import base64
            # Пробуем разные варианты padding
            for padding in ['', '=', '==', '===']:
                try:
                    decoded_bytes = base64.b64decode(text_stripped + padding)
                    decoded = decoded_bytes.decode('utf-8', errors='ignore')
                    # Если декодирование успешно и содержит VPN ссылки, используем декодированный контент
                    if any(proto in decoded for proto in protocols):
                        text = decoded
                        break
                except Exception:
                    continue
        except Exception:
            pass
    
    # Ищем ссылки в тексте с помощью regex (ищем не только в начале строк)
    # Используем word boundary для более точного поиска
    for protocol in protocols:
        # Паттерн для поиска ссылок протокола в тексте
        # Используем более точный паттерн - протокол должен быть отдельным словом
        # Для протоколов начинающихся с букв используем word boundary
        if protocol[0].isalpha():
            pattern = r'\b' + re.escape(protocol) + r'[^\s<>"\'`\n\r]+'
        else:
            pattern = re.escape(protocol) + r'[^\s<>"\'`\n\r]+'
        found_links = re.findall(pattern, text, re.MULTILINE)
        for link in found_links:
            # Очищаем ссылку от возможных символов в конце
            link = link.rstrip('.,;:!?)').strip()
            if link and link not in links:
                links.append(link)
    
    # Также проверяем построчно для точного совпадения (чтобы не пропустить ссылки)
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Проверяем, начинается ли строка с протокола VPN
        for protocol in protocols:
            if line.startswith(protocol):
                # Находим конец ссылки (до следующего пробела или конца строки)
                if protocol == 'vmess://':
                    # VMess ссылки обычно заканчиваются на перенос строки или пробел
                    link = line.split()[0] if ' ' in line else line
                else:
                    # Для остальных протоколов ищем до пробела, табуляции или конца строки
                    link = re.split(r'[\s\t<>"\'`\n\r]', line)[0]
                
                # Очищаем ссылку
                link = link.rstrip('.,;:!?)').strip()
                # Проверяем что это действительно ссылка (содержит @ или /)
                if link and ('@' in link or '://' in link) and link not in links:
                    links.append(link)
                break
    
    return links


def is_subscription_url(text: str) -> bool:
    """Проверяет, является ли текст ссылкой на подписку"""
    text = text.strip()
    
    # Проверяем, является ли это HTTP/HTTPS ссылкой
    parsed = urlparse(text)
    if parsed.scheme in ['http', 'https']:
        return True
    
    # Проверяем, является ли это base64 закодированной подпиской
    # (обычно длинная строка без пробелов и переносов строк)
    text_stripped = text.strip()
    is_base64_like = (
        len(text_stripped) > 20 and 
        not ' ' in text_stripped and 
        '\n' not in text_stripped and 
        not text_stripped.startswith(('http://', 'https://', 'vless://', 'vmess://', 'trojan://', 'ss://', 'hy2://'))
    )
    
    if is_base64_like:
        try:
            import base64
            # Пробуем разные варианты padding
            for padding in ['', '=', '==', '===']:
                try:
                    decoded_bytes = base64.b64decode(text_stripped + padding)
                    decoded = decoded_bytes.decode('utf-8', errors='ignore')
                    # Если декодированный текст содержит VPN ссылки
                    if any(proto in decoded for proto in ['vless://', 'vmess://', 'trojan://', 'ss://', 'hy2://', 'tuic://']):
                        return True
                except Exception:
                    continue
        except Exception:
            pass
    
    # Проверяем, содержит ли текст несколько VPN ссылок
    vpn_links = extract_vpn_links(text)
    if len(vpn_links) > 1:
        return True
    
    return False

