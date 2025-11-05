"""Парсер протокола TUIC"""
from typing import Dict, Any, Optional
from urllib.parse import unquote

from .base import BaseProtocol


class TUICProtocol(BaseProtocol):
    """Парсер для протокола TUIC (tuic://)"""
    
    def parse(self) -> Dict[str, Any]:
        """Парсинг ссылки TUIC"""
        # Формат: tuic://uuid:password@server:port?params#tag
        netloc = self.parsed_url.netloc
        
        uuid = None
        password = None
        
        if '@' in netloc:
            auth, server_port = netloc.rsplit('@', 1)
            if ':' in auth:
                uuid, password = auth.split(':', 1)
                uuid = unquote(uuid)
                password = unquote(password)
        else:
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
        
        # Параметры
        congestion_control = self._get_query_param('congestion_control', 'bbr')
        udp_relay_mode = self._get_query_param('udp_relay_mode', 'native')
        zero_rtt_handshake = self._get_query_param('zero_rtt_handshake', 'false') == 'true'
        sni = self._get_query_param('sni')
        insecure = self._get_query_param('insecure', 'false') == 'true'
        alpn = self._get_query_param('alpn')
        
        tag = self._get_tag() or f"tuic-{server}"
        
        return {
            'protocol': 'tuic',
            'uuid': uuid,
            'password': password,
            'server': server,
            'port': port,
            'congestion_control': congestion_control,
            'udp_relay_mode': udp_relay_mode,
            'zero_rtt_handshake': zero_rtt_handshake,
            'sni': sni,
            'insecure': insecure,
            'alpn': alpn,
            'tag': tag,
        }
    
    def to_singbox_outbound(self) -> Dict[str, Any]:
        """Конвертация в sing-box outbound для TUIC"""
        parsed = self.parse()
        
        if not parsed['uuid'] or not parsed['password']:
            raise ValueError("TUIC ссылка должна содержать uuid и password")
        
        outbound = {
            'type': 'tuic',
            'tag': parsed['tag'],
            'server': parsed['server'],
            'server_port': parsed['port'],
            'uuid': parsed['uuid'],
            'password': parsed['password'],
            'congestion_control': parsed['congestion_control'],
            'udp_relay_mode': parsed['udp_relay_mode'],
            'zero_rtt_handshake': parsed['zero_rtt_handshake'],
        }
        
        # TLS настройки
        if parsed['sni'] or not parsed['insecure']:
            tls_config = {
                'enabled': True,
            }
            
            if parsed['sni']:
                tls_config['server_name'] = parsed['sni']
            elif parsed['server']:
                tls_config['server_name'] = parsed['server']
            
            if parsed['insecure']:
                tls_config['insecure'] = True
            
            if parsed['alpn']:
                tls_config['alpn'] = parsed['alpn'].split(',')
            
            outbound['tls'] = tls_config
        
        return outbound

