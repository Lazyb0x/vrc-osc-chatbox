import logging
import socket
from dataclasses import dataclass
from ipaddress import ip_address

import ifaddr

logger = logging.getLogger(__name__)


@dataclass
class IpInfo:
    ip: str = None
    network_name: str = None
    network_prefix: str = None
    adapter_name: str = None


def is_port_in_use(host: str, port: int) -> bool:
    """Check if a port is in use on the given host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def find_available_port(host: str, port: int, max_attempts: int = 100) -> int:
    """Starting from the given port, find an available port by incrementing."""
    current = port
    for _ in range(max_attempts):
        if not is_port_in_use(host, current):
            if current != port:
                logger.warning("Port %s is in use, using port %s instead", port, current)
            return current
        current += 1
    raise RuntimeError(f"Could not find an available port after {max_attempts} attempts")


def get_ip_address() -> list[IpInfo]:
    addrs = []
    for adapter in ifaddr.get_adapters():
        for ip in adapter.ips:
            if ip.is_IPv4:
                addr = ip_address(ip.ip)
                if addr.is_loopback or addr.is_link_local:
                    continue
                ip_info = IpInfo(ip.ip, ip.nice_name, ip.network_prefix, adapter.name)
                addrs.append(ip_info)
    return addrs
