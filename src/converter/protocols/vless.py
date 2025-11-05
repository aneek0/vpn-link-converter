"""Парсер протокола VLESS"""
from typing import Dict, Any, Optional
from urllib.parse import unquote

from .base import BaseProtocol


class VLESSProtocol(BaseProtocol):
    """Парсер для протокола VLESS (vless://)"""
    
    def parse(self) -> Dict[str, Any]:
        """Парсинг ссылки VLESS"""
        # Формат: vless://uuid@server:port?params#tag
        netloc = self.parsed_url.netloc
        if '@' in netloc:
            uuid, server_port = netloc.rsplit('@', 1)
            uuid = unquote(uuid)
        else:
            raise ValueError("VLESS ссылка должна содержать UUID")
        
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
        encryption = self._get_query_param('encryption', 'none')
        flow = self._get_query_param('flow')
        type_param = self._get_query_param('type', 'tcp')
        security = self._get_query_param('security', 'none')
        sni = self._get_query_param('sni')
        fp = self._get_query_param('fp')
        pbk = self._get_query_param('pbk')  # public key для reality
        sid = self._get_query_param('sid')  # short id для reality
        path = self._get_query_param('path')
        host = self._get_query_param('host')
        header_type = self._get_query_param('headerType')
        
        tag = self._get_tag() or f"vless-{server}"
        
        return {
            'protocol': 'vless',
            'uuid': uuid,
            'server': server,
            'port': port,
            'encryption': encryption,
            'flow': flow,
            'type': type_param,
            'security': security,
            'sni': sni,
            'fp': fp,
            'pbk': pbk,
            'sid': sid,
            'path': path,
            'host': host,
            'headerType': header_type,
            'tag': tag,
        }
    
    def to_singbox_outbound(self) -> Dict[str, Any]:
        """Конвертация в sing-box outbound для VLESS"""
        parsed = self.parse()
        
        outbound = {
            'type': 'vless',
            'tag': parsed['tag'],
            'server': parsed['server'],
            'server_port': parsed['port'],
            'uuid': parsed['uuid'],
        }
        
        if parsed['encryption'] != 'none':
            outbound['encryption'] = parsed['encryption']
        
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
        elif transport_type == 'http':
            transport = {
                'type': 'http',
            }
            if parsed['path']:
                transport['path'] = parsed['path']
            if parsed['host']:
                transport['host'] = [parsed['host']]
            outbound['transport'] = transport
        
        # TLS настройки
        if parsed['security'] in ['tls', 'reality']:
            tls_config = {
                'enabled': True,
            }
            
            if parsed['sni']:
                tls_config['server_name'] = parsed['sni']
            elif parsed['server']:
                tls_config['server_name'] = parsed['server']
            
            if parsed['security'] == 'reality':
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
        
        # Packet encoding
        if parsed['type'] == 'ws' or parsed['type'] == 'grpc':
            outbound['packet_encoding'] = 'xudp'
        
        return outbound

