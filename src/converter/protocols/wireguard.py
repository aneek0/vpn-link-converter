"""Парсер протокола Wireguard"""
from typing import Dict, Any, Optional
from urllib.parse import unquote

from .base import BaseProtocol


class WireguardProtocol(BaseProtocol):
    """Парсер для протокола Wireguard (wg://)"""
    
    def parse(self) -> Dict[str, Any]:
        """Парсинг ссылки Wireguard"""
        # Формат: wg://base64_json или wg://server:port?params#tag
        netloc = self.parsed_url.netloc
        
        # Пробуем парсить как обычный URL
        if ':' in netloc:
            server, port_str = netloc.rsplit(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 51820
        else:
            server = netloc
            port = 51820
        
        # Параметры
        public_key = self._get_query_param('public_key') or self._get_query_param('pubkey')
        private_key = self._get_query_param('private_key') or self._get_query_param('privkey')
        preshared_key = self._get_query_param('preshared_key') or self._get_query_param('psk')
        allowed_ips = self._get_query_param('allowed_ips')
        endpoint = self._get_query_param('endpoint')
        dns = self._get_query_param('dns')
        mtu = self._get_query_param('mtu')
        
        tag = self._get_tag() or f"wireguard-{server}"
        
        return {
            'protocol': 'wireguard',
            'server': server,
            'port': port,
            'public_key': public_key,
            'private_key': private_key,
            'preshared_key': preshared_key,
            'allowed_ips': allowed_ips,
            'endpoint': endpoint,
            'dns': dns,
            'mtu': int(mtu) if mtu else None,
            'tag': tag,
        }
    
    def to_singbox_outbound(self) -> Dict[str, Any]:
        """Конвертация в sing-box outbound для Wireguard"""
        parsed = self.parse()
        
        if not parsed['public_key']:
            raise ValueError("Wireguard ссылка должна содержать public_key")
        
        outbound = {
            'type': 'wireguard',
            'tag': parsed['tag'],
            'server': parsed['server'],
            'server_port': parsed['port'],
            'local_address': ['10.0.0.2/32'],
            'private_key': parsed['private_key'] or '',
            'peer_public_key': parsed['public_key'],
        }
        
        if parsed['preshared_key']:
            outbound['pre_shared_key'] = parsed['preshared_key']
        
        if parsed['allowed_ips']:
            outbound['local_address'] = parsed['allowed_ips'].split(',')
        
        if parsed['mtu']:
            outbound['mtu'] = parsed['mtu']
        
        return outbound

