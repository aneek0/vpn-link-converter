"""Парсер VPN ссылок"""
import re
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from .protocols.base import BaseProtocol
from .protocols.hy2 import Hysteria2Protocol
from .protocols.vless import VLESSProtocol
from .protocols.vmess import VMessProtocol
from .protocols.trojan import TrojanProtocol
from .protocols.shadowsocks import ShadowsocksProtocol
from .protocols.socks5 import SOCKS5Protocol
from .protocols.http import HTTPProtocol
from .protocols.wireguard import WireguardProtocol
from .protocols.tuic import TUICProtocol
from .protocols.hysteria import HysteriaProtocol


class VPNLinkParser:
    """Парсер VPN ссылок различных протоколов"""
    
    PROTOCOL_MAP = {
        'hy2': Hysteria2Protocol,
        'hysteria2': Hysteria2Protocol,
        'vless': VLESSProtocol,
        'vmess': VMessProtocol,
        'trojan': TrojanProtocol,
        'ss': ShadowsocksProtocol,
        'shadowsocks': ShadowsocksProtocol,
        'socks5': SOCKS5Protocol,
        'socks': SOCKS5Protocol,
        'http': HTTPProtocol,
        'https': HTTPProtocol,
        'wg': WireguardProtocol,
        'wireguard': WireguardProtocol,
        'tuic': TUICProtocol,
        'hysteria': HysteriaProtocol,
    }
    
    @classmethod
    def detect_protocol(cls, url: str) -> Optional[str]:
        """Определить протокол по URL"""
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        
        # Удаляем возможные суффиксы
        scheme = scheme.replace('://', '')
        
        # Проверяем специальные случаи
        if scheme == 'ss':
            return 'ss'
        if scheme.startswith('hy2') or scheme == 'hysteria2':
            return 'hy2'
        if scheme == 'hysteria':
            return 'hysteria'
        
        return scheme if scheme in cls.PROTOCOL_MAP else None
    
    @classmethod
    def parse(cls, url: str) -> Dict[str, Any]:
        """Парсить VPN ссылку"""
        protocol_name = cls.detect_protocol(url)
        
        if not protocol_name:
            raise ValueError(f"Неподдерживаемый протокол: {urlparse(url).scheme}")
        
        protocol_class = cls.PROTOCOL_MAP[protocol_name]
        protocol = protocol_class(url)
        
        return protocol.parse()
    
    @classmethod
    def to_singbox_outbound(cls, url: str) -> Dict[str, Any]:
        """Конвертировать ссылку в sing-box outbound"""
        protocol_name = cls.detect_protocol(url)
        
        if not protocol_name:
            raise ValueError(f"Неподдерживаемый протокол: {urlparse(url).scheme}")
        
        protocol_class = cls.PROTOCOL_MAP[protocol_name]
        protocol = protocol_class(url)
        
        return protocol.to_singbox_outbound()

