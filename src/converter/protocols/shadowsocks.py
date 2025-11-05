"""Парсер протокола Shadowsocks"""
import base64
from typing import Dict, Any, Optional
from urllib.parse import unquote

from .base import BaseProtocol


class ShadowsocksProtocol(BaseProtocol):
    """Парсер для протокола Shadowsocks (ss://)"""
    
    def parse(self) -> Dict[str, Any]:
        """Парсинг ссылки Shadowsocks"""
        # Формат: ss://method:password@server:port#tag
        # или ss://base64(method:password@server:port)#tag
        netloc = self.parsed_url.netloc
        
        # Пытаемся декодировать base64
        try:
            decoded = base64.b64decode(netloc + '==').decode('utf-8')
            if '@' in decoded:
                method_password, server_port = decoded.rsplit('@', 1)
                if ':' in method_password:
                    method, password = method_password.split(':', 1)
                else:
                    method = method_password
                    password = ''
            else:
                raise ValueError("Неверный формат")
        except Exception:
            # Пробуем обычный формат
            if '@' in netloc:
                method_password, server_port = netloc.rsplit('@', 1)
                if ':' in method_password:
                    method, password = method_password.split(':', 1)
                    method = unquote(method)
                    password = unquote(password)
                else:
                    method = unquote(method_password)
                    password = ''
            else:
                raise ValueError("Неверный формат Shadowsocks ссылки")
        
        if ':' in server_port:
            server, port_str = server_port.rsplit(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 8388
        else:
            server = server_port
            port = 8388
        
        # Параметры
        plugin = self._get_query_param('plugin')
        tag = self._get_tag() or f"shadowsocks-{server}"
        
        return {
            'protocol': 'shadowsocks',
            'method': method,
            'password': password,
            'server': server,
            'port': port,
            'plugin': plugin,
            'tag': tag,
        }
    
    def to_singbox_outbound(self) -> Dict[str, Any]:
        """Конвертация в sing-box outbound для Shadowsocks"""
        parsed = self.parse()
        
        outbound = {
            'type': 'shadowsocks',
            'tag': parsed['tag'],
            'server': parsed['server'],
            'server_port': parsed['port'],
            'method': parsed['method'],
            'password': parsed['password'],
        }
        
        # Плагин (например, obfs)
        if parsed['plugin']:
            # Простой парсинг plugin параметров
            plugin_parts = parsed['plugin'].split(';')
            plugin_name = plugin_parts[0] if plugin_parts else None
            
            if plugin_name == 'obfs-local':
                # Обработка obfs параметров
                pass
        
        return outbound

