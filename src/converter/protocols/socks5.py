"""Парсер протокола SOCKS5"""
from typing import Dict, Any, Optional
from urllib.parse import unquote

from .base import BaseProtocol


class SOCKS5Protocol(BaseProtocol):
    """Парсер для протокола SOCKS5 (socks5://)"""
    
    def parse(self) -> Dict[str, Any]:
        """Парсинг ссылки SOCKS5"""
        # Формат: socks5://[username:password@]server:port#tag
        netloc = self.parsed_url.netloc
        
        username = None
        password = None
        
        if '@' in netloc:
            auth, server_port = netloc.rsplit('@', 1)
            if ':' in auth:
                username, password = auth.split(':', 1)
                username = unquote(username)
                password = unquote(password)
        else:
            server_port = netloc
        
        if ':' in server_port:
            server, port_str = server_port.rsplit(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 1080
        else:
            server = server_port
            port = 1080
        
        tag = self._get_tag() or f"socks5-{server}"
        
        return {
            'protocol': 'socks',
            'server': server,
            'port': port,
            'username': username,
            'password': password,
            'tag': tag,
        }
    
    def to_singbox_outbound(self) -> Dict[str, Any]:
        """Конвертация в sing-box outbound для SOCKS5"""
        parsed = self.parse()
        
        outbound = {
            'type': 'socks',
            'tag': parsed['tag'],
            'server': parsed['server'],
            'server_port': parsed['port'],
        }
        
        if parsed['username'] and parsed['password']:
            outbound['username'] = parsed['username']
            outbound['password'] = parsed['password']
        
        return outbound

