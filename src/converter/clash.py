"""Конвертер в формат Clash YAML"""
import yaml
from typing import Dict, Any, List
from .parser import VPNLinkParser


def convert_to_clash_proxy(url: str) -> Dict[str, Any]:
    """Конвертировать VPN ссылку в формат прокси для Clash"""
    parsed = VPNLinkParser.parse(url)
    protocol = parsed['protocol']
    tag = parsed.get('tag', 'proxy')
    
    proxy = {
        'name': tag,
    }
    
    if protocol == 'vless':
        proxy['type'] = 'vless'
        proxy['server'] = parsed['server']
        proxy['port'] = parsed['port']
        proxy['uuid'] = parsed['uuid']
        
        # Network (transport)
        network = parsed.get('type', 'tcp').lower()
        if network == 'ws':
            proxy['network'] = 'ws'
            ws_opts = {}
            if parsed.get('path'):
                ws_opts['path'] = parsed['path']
            if parsed.get('host'):
                ws_opts['headers'] = {'Host': parsed['host']}
            if ws_opts:
                proxy['ws-opts'] = ws_opts
        elif network == 'httpupgrade':
            proxy['network'] = 'httpupgrade'
            http_opts = {}
            if parsed.get('path'):
                http_opts['path'] = [parsed['path']]
            if parsed.get('host'):
                http_opts['headers'] = {'Host': [parsed['host']]}
            if http_opts:
                proxy['http-opts'] = http_opts
        elif network == 'tcp':
            proxy['network'] = 'tcp'
        
        # UDP support (добавляем только если явно указано)
        if 'udp' in parsed:
            proxy['udp'] = parsed['udp']
        
        # TLS settings
        security = parsed.get('security', 'none')
        if security in ['tls', 'reality']:
            proxy['tls'] = True
            if parsed.get('sni'):
                proxy['servername'] = parsed['sni']
            
            # Client fingerprint
            if parsed.get('fp'):
                proxy['client-fingerprint'] = parsed['fp']
            
            # Flow (для xtls-rprx-vision)
            if parsed.get('flow'):
                proxy['flow'] = parsed['flow']
            
            # Reality settings
            if security == 'reality' and parsed.get('pbk'):
                reality_opts = {
                    'public-key': parsed['pbk']
                }
                if parsed.get('sid'):
                    reality_opts['short-id'] = parsed['sid']
                proxy['reality-opts'] = reality_opts
    elif protocol == 'vmess':
        proxy['type'] = 'vmess'
        proxy['server'] = parsed['server']
        proxy['port'] = parsed['port']
        proxy['uuid'] = parsed['uuid']
        proxy['alterId'] = parsed.get('alterId', 0)
        proxy['cipher'] = parsed.get('security', 'auto')
        
        if parsed.get('network') == 'ws':
            proxy['network'] = 'ws'
            if parsed.get('path'):
                proxy['ws-path'] = parsed['path']
            if parsed.get('host'):
                proxy['ws-headers'] = {'Host': parsed['host']}
        
        if parsed.get('tls') == 'tls':
            proxy['tls'] = True
            if parsed.get('sni'):
                proxy['servername'] = parsed['sni']
    elif protocol == 'trojan':
        proxy['type'] = 'trojan'
        proxy['server'] = parsed['server']
        proxy['port'] = parsed['port']
        proxy['password'] = parsed['password']
        
        if parsed.get('sni'):
            proxy['sni'] = parsed['sni']
    elif protocol == 'shadowsocks':
        proxy['type'] = 'ss'
        proxy['server'] = parsed['server']
        proxy['port'] = parsed['port']
        proxy['cipher'] = parsed['method']
        proxy['password'] = parsed['password']
    elif protocol == 'socks':
        proxy['type'] = 'socks5'
        proxy['server'] = parsed['server']
        proxy['port'] = parsed['port']
        if parsed.get('username'):
            proxy['username'] = parsed['username']
        if parsed.get('password'):
            proxy['password'] = parsed['password']
    elif protocol == 'http':
        proxy['type'] = 'http'
        proxy['server'] = parsed['server']
        proxy['port'] = parsed['port']
        if parsed.get('username'):
            proxy['username'] = parsed['username']
        if parsed.get('password'):
            proxy['password'] = parsed['password']
        if parsed.get('tls'):
            proxy['tls'] = True
    elif protocol in ['hysteria2', 'hysteria', 'tuic']:
        # Clash не поддерживает эти протоколы напрямую
        # Возвращаем базовую структуру или пропускаем
        return None
    else:
        return None
    
    return proxy


def create_clash_config(proxies: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Создать конфигурацию Clash"""
    if not proxies:
        return {}
    
    # Фильтруем None значения
    proxies = [p for p in proxies if p is not None]
    
    if not proxies:
        return {}
    
    config = {
        'port': 7890,
        'socks-port': 7891,
        'allow-lan': False,
        'mode': 'rule',
        'log-level': 'info',
        'external-controller': '127.0.0.1:9090',
        'proxies': proxies,
        'proxy-groups': [
            {
                'name': '🚀 Proxy',
                'type': 'select',
                'proxies': [p['name'] for p in proxies] + ['DIRECT']
            },
            {
                'name': '🎯 Auto',
                'type': 'url-test',
                'proxies': [p['name'] for p in proxies],
                'url': 'http://www.gstatic.com/generate_204',
                'interval': 300
            }
        ],
        'rules': [
            'DOMAIN-SUFFIX,local,DIRECT',
            'IP-CIDR,127.0.0.0/8,DIRECT',
            'IP-CIDR,10.0.0.0/8,DIRECT',
            'IP-CIDR,172.16.0.0/12,DIRECT',
            'IP-CIDR,192.168.0.0/16,DIRECT',
            'GEOIP,CN,DIRECT',
            'MATCH,🚀 Proxy'
        ]
    }
    
    return config


def convert_to_clash(url: str) -> Dict[str, Any]:
    """Конвертировать VPN ссылку в конфигурацию Clash"""
    proxy = convert_to_clash_proxy(url)
    if not proxy:
        raise ValueError(f"Протокол не поддерживается Clash")
    
    return create_clash_config([proxy])


def convert_multiple_to_clash(urls: List[str]) -> Dict[str, Any]:
    """Конвертировать несколько VPN ссылок в одну конфигурацию Clash"""
    proxies = []
    skipped = []
    
    for url in urls:
        try:
            proxy = convert_to_clash_proxy(url)
            if proxy:
                proxies.append(proxy)
            else:
                skipped.append(url)
        except Exception as e:
            # Пропускаем ссылки которые не поддерживаются Clash
            skipped.append(url)
            continue
    
    if not proxies:
        raise ValueError("Ни одна из ссылок не поддерживается Clash")
    
    return create_clash_config(proxies)


def format_yaml(config: Dict[str, Any]) -> str:
    """Форматировать конфигурацию в YAML"""
    return yaml.dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False)

