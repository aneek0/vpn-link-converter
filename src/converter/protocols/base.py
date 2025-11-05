"""Базовый класс для протоколов VPN"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs, unquote


class BaseProtocol(ABC):
    """Базовый класс для парсинга VPN протоколов"""
    
    def __init__(self, url: str):
        self.url = url
        self.parsed_url = urlparse(url)
        self.query_params = parse_qs(self.parsed_url.query)
        
    def _get_query_param(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Получить параметр из query string"""
        values = self.query_params.get(key)
        if values:
            return values[0]
        return default
    
    def _get_tag(self) -> Optional[str]:
        """Получить тег из фрагмента URL"""
        if self.parsed_url.fragment:
            return unquote(self.parsed_url.fragment)
        return None
    
    @abstractmethod
    def parse(self) -> Dict[str, Any]:
        """Парсинг ссылки протокола"""
        pass
    
    @abstractmethod
    def to_singbox_outbound(self) -> Dict[str, Any]:
        """Конвертация в формат sing-box outbound"""
        pass

