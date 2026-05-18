from dataclasses import dataclass
from ipaddress import ip_address

import ifaddr


@dataclass
class IpInfo:
    ip: str = None
    network_name: str = None
    network_prefix: str = None
    adapter_name: str = None


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
