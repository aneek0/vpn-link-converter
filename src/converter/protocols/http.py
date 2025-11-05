"""Парсер протокола HTTP/HTTPS"""
from typing import Dict, Any, Optional
from urllib.parse import unquote

from .base import BaseProtocol


class HTTPProtocol(BaseProtocol):
    """Парсер для протокола HTTP/HTTPS (http://, https://)"""
    
    def parse(self) -> Dict[str, Any]:
        """Парсинг ссылки HTTP/HTTPS"""
        # Формат: http://[username:password@]server:port#tag
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
                port = 80 if self.parsed_url.scheme == 'http' else 443
        else:
            server = server_port
            port = 80 if self.parsed_url.scheme == 'http' else 443
        
        is_https = self.parsed_url.scheme == 'https'
        tag = self._get_tag() or f"http-{server}"
        
        return {
            'protocol': 'http',
            'server': server,
            'port': port,
            'username': username,
            'password': password,
            'tls': is_https,
            'tag': tag,
        }
    
    def to_singbox_outbound(self) -> Dict[str, Any]:
        """Конвертация в sing-box outbound для HTTP/HTTPS"""
        parsed = self.parse()
        
        outbound = {
            'type': 'http',
            'tag': parsed['tag'],
            'server': parsed['server'],
            'server_port': parsed['port'],
        }
        
        if parsed['username'] and parsed['password']:
            outbound['username'] = parsed['username']
            outbound['password'] = parsed['password']
        
        if parsed['tls']:
            outbound['tls'] = {
                'enabled': True,
            }
        
        return outbound

