"""Парсер протокола Hysteria2"""
from typing import Dict, Any, Optional
from urllib.parse import unquote

from .base import BaseProtocol


class Hysteria2Protocol(BaseProtocol):
    """Парсер для протокола Hysteria2 (hy2://)"""
    
    def parse(self) -> Dict[str, Any]:
        """Парсинг ссылки Hysteria2"""
        # Формат: hy2://password@server:port?params#tag
        netloc = self.parsed_url.netloc
        if '@' in netloc:
            password, server_port = netloc.rsplit('@', 1)
            password = unquote(password)
        else:
            password = None
            server_port = netloc
        
        if ':' in server_port:
            server, port_str = server_port.rsplit(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 443
        else:
            server = server_port
            port = 443
        
        insecure = self._get_query_param('insecure', '0') == '1'
        sni = self._get_query_param('sni')
        tag = self._get_tag() or f"hysteria2-{server}"
        
        return {
            'protocol': 'hysteria2',
            'password': password,
            'server': server,
            'port': port,
            'insecure': insecure,
            'sni': sni,
            'tag': tag,
        }
    
    def to_singbox_outbound(self) -> Dict[str, Any]:
        """Конвертация в sing-box outbound для Hysteria2"""
        parsed = self.parse()
        
        outbound = {
            'type': 'hysteria2',
            'tag': parsed['tag'],
            'server': parsed['server'],
            'server_port': parsed['port'],
        }
        
        if parsed['password']:
            outbound['password'] = parsed['password']
        
        # TLS настройки
        tls_config = {}
        if parsed['sni']:
            tls_config['enabled'] = True
            tls_config['server_name'] = parsed['sni']
            if parsed['insecure']:
                tls_config['insecure'] = True
        elif parsed['insecure']:
            tls_config['enabled'] = True
            tls_config['insecure'] = True
        
        if tls_config:
            outbound['tls'] = tls_config
        
        return outbound

