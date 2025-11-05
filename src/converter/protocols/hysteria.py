"""Парсер протокола Hysteria (v1)"""
from typing import Dict, Any, Optional
from urllib.parse import unquote

from .base import BaseProtocol


class HysteriaProtocol(BaseProtocol):
    """Парсер для протокола Hysteria v1 (hysteria://)"""
    
    def parse(self) -> Dict[str, Any]:
        """Парсинг ссылки Hysteria v1"""
        # Формат: hysteria://server:port?params#tag
        netloc = self.parsed_url.netloc
        
        if ':' in netloc:
            server, port_str = netloc.rsplit(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 443
        else:
            server = netloc
            port = 443
        
        # Параметры
        protocol = self._get_query_param('protocol', 'udp')
        auth = self._get_query_param('auth')
        upmbps = self._get_query_param('upmbps')
        downmbps = self._get_query_param('downmbps')
        obfs = self._get_query_param('obfs')
        obfs_param = self._get_query_param('obfsParam')
        insecure = self._get_query_param('insecure', 'false') == 'true'
        peer = self._get_query_param('peer')
        alpn = self._get_query_param('alpn')
        
        tag = self._get_tag() or f"hysteria-{server}"
        
        return {
            'protocol': 'hysteria',
            'server': server,
            'port': port,
            'auth': auth,
            'upmbps': int(upmbps) if upmbps else None,
            'downmbps': int(downmbps) if downmbps else None,
            'obfs': obfs,
            'obfsParam': obfs_param,
            'insecure': insecure,
            'peer': peer,
            'alpn': alpn,
            'tag': tag,
        }
    
    def to_singbox_outbound(self) -> Dict[str, Any]:
        """Конвертация в sing-box outbound для Hysteria v1"""
        parsed = self.parse()
        
        outbound = {
            'type': 'hysteria',
            'tag': parsed['tag'],
            'server': parsed['server'],
            'server_port': parsed['port'],
        }
        
        if parsed['auth']:
            outbound['auth_str'] = parsed['auth']
        
        if parsed['upmbps']:
            outbound['up_mbps'] = parsed['upmbps']
        
        if parsed['downmbps']:
            outbound['down_mbps'] = parsed['downmbps']
        
        if parsed['obfs']:
            outbound['obfs'] = parsed['obfs']
            if parsed['obfsParam']:
                outbound['obfs_password'] = parsed['obfsParam']
        
        # TLS настройки
        tls_config = {
            'enabled': True,
        }
        
        if parsed['peer']:
            tls_config['server_name'] = parsed['peer']
        elif parsed['server']:
            tls_config['server_name'] = parsed['server']
        
        if parsed['insecure']:
            tls_config['insecure'] = True
        
        if parsed['alpn']:
            tls_config['alpn'] = parsed['alpn'].split(',')
        
        outbound['tls'] = tls_config
        
        return outbound

