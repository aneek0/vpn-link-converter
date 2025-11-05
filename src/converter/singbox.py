"""Конвертер в формат sing-box"""
import json
from typing import Dict, Any, List, Optional

from .parser import VPNLinkParser


def create_full_config(outbounds: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Создать полную конфигурацию sing-box"""
    return {
        'log': {
            'level': 'info',
            'timestamp': True,
        },
        'dns': {
            'servers': [
                {
                    'tag': 'dns_proxy',
                    'address': '8.8.8.8',
                    'address_resolver': 'dns_ip',
                },
                {
                    'tag': 'dns_ip',
                    'address': '223.5.5.5',
                    'detour': 'direct',
                },
            ],
        },
        'inbounds': [
            {
                'type': 'mixed',
                'tag': 'mixed-in',
                'listen': '127.0.0.1',
                'listen_port': 7890,
            },
        ],
        'outbounds': outbounds + [
            {
                'type': 'direct',
                'tag': 'direct',
            },
            {
                'type': 'block',
                'tag': 'block',
            },
        ],
        'route': {
            'rules': [
                {
                    'outbound': 'dns_ip',
                    'network': 'udp',
                    'port': 53,
                },
            ],
            'final': 'proxy',
        },
    }


def create_outbound_only(outbound: Dict[str, Any]) -> Dict[str, Any]:
    """Создать только outbound конфигурацию"""
    return {
        'outbounds': [outbound],
    }


def convert_to_singbox(url: str, full_config: bool = False) -> Dict[str, Any]:
    """Конвертировать VPN ссылку в sing-box конфигурацию"""
    outbound = VPNLinkParser.to_singbox_outbound(url)
    
    if full_config:
        return create_full_config([outbound])
    else:
        return create_outbound_only(outbound)


def format_json(config: Dict[str, Any], indent: int = 2) -> str:
    """Форматировать JSON конфигурацию"""
    return json.dumps(config, indent=indent, ensure_ascii=False)

