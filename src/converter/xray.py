"""Конвертер в формат Xray Core JSON"""
import json
from typing import Dict, Any, List
from .parser import VPNLinkParser


def convert_to_xray_outbound(url: str) -> Dict[str, Any]:
    """Конвертировать VPN ссылку в формат outbound для Xray"""
    parsed = VPNLinkParser.parse(url)
    protocol = parsed['protocol']
    
    outbound = {
        'protocol': protocol,
        'settings': {},
        'tag': parsed.get('tag', 'proxy'),
    }
    
    if protocol == 'vless':
        outbound['settings'] = {
            'vnext': [{
                'address': parsed['server'],
                'port': parsed['port'],
                'users': [{
                    'id': parsed['uuid'],
                    'encryption': parsed.get('encryption', 'none'),
                    'flow': parsed.get('flow', ''),
                }]
            }]
        }
        
        # Удаляем пустой flow
        if not outbound['settings']['vnext'][0]['users'][0]['flow']:
            del outbound['settings']['vnext'][0]['users'][0]['flow']
        
        # Stream settings
        stream_settings = {}
        network = parsed.get('type', 'tcp').lower()
        
        if network == 'ws':
            stream_settings['network'] = 'ws'
            ws_settings = {}
            if parsed.get('path'):
                ws_settings['path'] = parsed['path']
            if parsed.get('host'):
                ws_settings['headers'] = {'Host': parsed['host']}
            if ws_settings:
                stream_settings['wsSettings'] = ws_settings
        elif network == 'httpupgrade':
            stream_settings['network'] = 'httpupgrade'
            http_settings = {}
            if parsed.get('path'):
                http_settings['path'] = parsed['path']
            if parsed.get('host'):
                http_settings['host'] = [parsed['host']]
            if http_settings:
                stream_settings['httpSettings'] = http_settings
        else:
            stream_settings['network'] = 'tcp'
        
        # TLS settings
        security = parsed.get('security', 'none')
        if security in ['tls', 'reality']:
            tls_settings = {}
            if parsed.get('sni'):
                tls_settings['serverName'] = parsed['sni']
            
            if security == 'reality':
                tls_settings['reality'] = {}
                if parsed.get('pbk'):
                    tls_settings['reality']['publicKey'] = parsed['pbk']
                if parsed.get('sid'):
                    tls_settings['reality']['shortId'] = parsed['sid']
                if parsed.get('fp'):
                    tls_settings['reality']['fingerprint'] = parsed['fp']
                tls_settings['show'] = False
            
            if tls_settings:
                stream_settings['security'] = security
                stream_settings['tlsSettings'] = tls_settings
        
        if stream_settings:
            outbound['streamSettings'] = stream_settings
    
    elif protocol == 'vmess':
        outbound['settings'] = {
            'vnext': [{
                'address': parsed['server'],
                'port': parsed['port'],
                'users': [{
                    'id': parsed['uuid'],
                    'alterId': parsed.get('alterId', 0),
                    'security': parsed.get('security', 'auto'),
                }]
            }]
        }
        
        # Stream settings
        stream_settings = {}
        network = parsed.get('network', 'tcp').lower()
        
        if network == 'ws':
            stream_settings['network'] = 'ws'
            ws_settings = {}
            if parsed.get('path'):
                ws_settings['path'] = parsed['path']
            if parsed.get('host'):
                ws_settings['headers'] = {'Host': parsed['host']}
            if ws_settings:
                stream_settings['wsSettings'] = ws_settings
        else:
            stream_settings['network'] = 'tcp'
        
        if parsed.get('tls') == 'tls':
            stream_settings['security'] = 'tls'
            tls_settings = {}
            if parsed.get('sni'):
                tls_settings['serverName'] = parsed['sni']
            if tls_settings:
                stream_settings['tlsSettings'] = tls_settings
        
        if stream_settings:
            outbound['streamSettings'] = stream_settings
    
    elif protocol == 'trojan':
        outbound['settings'] = {
            'servers': [{
                'address': parsed['server'],
                'port': parsed['port'],
                'password': parsed['password'],
            }]
        }
        
        # Stream settings
        stream_settings = {}
        if parsed.get('sni'):
            stream_settings['security'] = 'tls'
            stream_settings['tlsSettings'] = {
                'serverName': parsed['sni']
            }
        
        if stream_settings:
            outbound['streamSettings'] = stream_settings
    
    elif protocol == 'shadowsocks':
        outbound['settings'] = {
            'servers': [{
                'address': parsed['server'],
                'port': parsed['port'],
                'method': parsed['method'],
                'password': parsed['password'],
            }]
        }
    
    else:
        # Неподдерживаемый протокол
        return None
    
    return outbound


def create_xray_config(outbounds: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Создать конфигурацию Xray"""
    if not outbounds:
        return {}
    
    # Фильтруем None значения
    outbounds = [o for o in outbounds if o is not None]
    
    if not outbounds:
        return {}
    
    config = {
        'log': {
            'loglevel': 'warning'
        },
        'outbounds': outbounds,
        'routing': {
            'domainStrategy': 'IPIfNonMatch',
            'rules': [
                {
                    'type': 'field',
                    'ip': ['geoip:private'],
                    'outboundTag': 'direct'
                },
                {
                    'type': 'field',
                    'domain': ['geosite:private'],
                    'outboundTag': 'direct'
                }
            ]
        }
    }
    
    return config


def convert_multiple_to_xray(urls: List[str]) -> Dict[str, Any]:
    """Конвертировать несколько VPN ссылок в конфигурацию Xray"""
    outbounds = []
    
    for url in urls:
        try:
            outbound = convert_to_xray_outbound(url)
            if outbound:
                outbounds.append(outbound)
        except Exception:
            # Пропускаем ссылки которые не поддерживаются
            continue
    
    if not outbounds:
        raise ValueError("Ни одна из ссылок не поддерживается Xray")
    
    return create_xray_config(outbounds)


def format_json(config: Dict[str, Any], indent: int = 2) -> str:
    """Форматировать конфигурацию в JSON"""
    return json.dumps(config, ensure_ascii=False, indent=indent)

