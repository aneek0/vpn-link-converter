"""Парсер протокола Trojan"""
from typing import Dict, Any, Optional
from urllib.parse import unquote

from .base import BaseProtocol


class TrojanProtocol(BaseProtocol):
    """Парсер для протокола Trojan (trojan://)"""
    
    def parse(self) -> Dict[str, Any]:
        """Парсинг ссылки Trojan"""
        # Формат: trojan://password@server:port?params#tag
        netloc = self.parsed_url.netloc
        if '@' in netloc:
            password, server_port = netloc.rsplit('@', 1)
            password = unquote(password)
        else:
            raise ValueError("Trojan ссылка должна содержать пароль")
        
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
        sni = self._get_query_param('sni')
        type_param = self._get_query_param('type', 'tcp')
        security = self._get_query_param('security', 'tls')
        fp = self._get_query_param('fp')
        pbk = self._get_query_param('pbk')
        sid = self._get_query_param('sid')
        path = self._get_query_param('path')
        host = self._get_query_param('host')
        flow = self._get_query_param('flow')
        
        tag = self._get_tag() or f"trojan-{server}"
        
        return {
            'protocol': 'trojan',
            'password': password,
            'server': server,
            'port': port,
            'sni': sni,
            'type': type_param,
            'security': security,
            'fp': fp,
            'pbk': pbk,
            'sid': sid,
            'path': path,
            'host': host,
            'flow': flow,
            'tag': tag,
        }
    
    def to_singbox_outbound(self) -> Dict[str, Any]:
        """Конвертация в sing-box outbound для Trojan"""
        parsed = self.parse()
        
        outbound = {
            'type': 'trojan',
            'tag': parsed['tag'],
            'server': parsed['server'],
            'server_port': parsed['port'],
            'password': parsed['password'],
        }
        
        if parsed['flow']:
            outbound['flow'] = parsed['flow']
        
        # Настройка транспорта
        transport_type = parsed['type'].lower()
        if transport_type == 'ws':
            transport = {
                'type': 'ws',
            }
            if parsed['path']:
                transport['path'] = parsed['path']
            if parsed['host']:
                transport['headers'] = {'Host': parsed['host']}
            outbound['transport'] = transport
        elif transport_type == 'grpc':
            transport = {
                'type': 'grpc',
            }
            if parsed['path']:
                transport['service_name'] = parsed['path']
            outbound['transport'] = transport
        
        # TLS настройки
        security = parsed['security'].lower()
        if security in ['tls', 'reality']:
            tls_config = {
                'enabled': True,
            }
            
            if parsed['sni']:
                tls_config['server_name'] = parsed['sni']
            elif parsed['server']:
                tls_config['server_name'] = parsed['server']
            
            if security == 'reality':
                reality_config = {
                    'enabled': True,
                }
                if parsed['pbk']:
                    reality_config['public_key'] = parsed['pbk']
                if parsed['sid']:
                    reality_config['short_id'] = parsed['sid']
                tls_config['reality'] = reality_config
            
            if parsed['fp']:
                tls_config['utls'] = {
                    'enabled': True,
                    'fingerprint': parsed['fp'],
                }
            
            outbound['tls'] = tls_config
        
        return outbound

