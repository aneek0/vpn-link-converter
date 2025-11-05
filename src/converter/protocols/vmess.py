"""Парсер протокола VMess"""
import json
import base64
from typing import Dict, Any, Optional
from urllib.parse import unquote

from .base import BaseProtocol


class VMessProtocol(BaseProtocol):
    """Парсер для протокола VMess (vmess://)"""
    
    def parse(self) -> Dict[str, Any]:
        """Парсинг ссылки VMess"""
        # Формат: vmess://base64_json
        netloc = self.parsed_url.netloc
        
        # Декодируем base64
        try:
            decoded = base64.b64decode(netloc + '==').decode('utf-8')
            config = json.loads(decoded)
        except Exception:
            raise ValueError("Неверный формат VMess ссылки")
        
        server = config.get('add', '')
        port = config.get('port', 443)
        uuid = config.get('id', '')
        alter_id = config.get('aid', 0)
        security = config.get('scy', config.get('security', 'auto'))
        network = config.get('net', 'tcp')
        type_param = config.get('type', 'none')
        host = config.get('host', '')
        path = config.get('path', '')
        tls = config.get('tls', 'none')
        sni = config.get('sni', '')
        fp = config.get('fp', '')
        pbk = config.get('pbk', '')
        sid = config.get('sid', '')
        ps = config.get('ps', '')
        
        tag = ps or f"vmess-{server}"
        
        return {
            'protocol': 'vmess',
            'uuid': uuid,
            'server': server,
            'port': port,
            'alterId': alter_id,
            'security': security,
            'network': network,
            'type': type_param,
            'host': host,
            'path': path,
            'tls': tls,
            'sni': sni,
            'fp': fp,
            'pbk': pbk,
            'sid': sid,
            'tag': tag,
        }
    
    def to_singbox_outbound(self) -> Dict[str, Any]:
        """Конвертация в sing-box outbound для VMess"""
        parsed = self.parse()
        
        outbound = {
            'type': 'vmess',
            'tag': parsed['tag'],
            'server': parsed['server'],
            'server_port': parsed['port'],
            'uuid': parsed['uuid'],
        }
        
        if parsed['security'] and parsed['security'] != 'auto':
            outbound['security'] = parsed['security']
        
        # Настройка транспорта
        network = parsed['network'].lower()
        if network == 'ws':
            transport = {
                'type': 'ws',
            }
            if parsed['path']:
                transport['path'] = parsed['path']
            if parsed['host']:
                transport['headers'] = {'Host': parsed['host']}
            outbound['transport'] = transport
        elif network == 'grpc':
            transport = {
                'type': 'grpc',
            }
            if parsed['path']:
                transport['service_name'] = parsed['path']
            outbound['transport'] = transport
        elif network == 'http':
            transport = {
                'type': 'http',
            }
            if parsed['path']:
                transport['path'] = parsed['path']
            if parsed['host']:
                transport['host'] = [parsed['host']]
            outbound['transport'] = transport
        elif network == 'quic':
            transport = {
                'type': 'quic',
            }
            outbound['transport'] = transport
        
        # TLS настройки
        if parsed['tls'] in ['tls', 'reality']:
            tls_config = {
                'enabled': True,
            }
            
            if parsed['sni']:
                tls_config['server_name'] = parsed['sni']
            elif parsed['server']:
                tls_config['server_name'] = parsed['server']
            
            if parsed['tls'] == 'reality':
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

