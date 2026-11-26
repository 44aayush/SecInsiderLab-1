"""Raw frame builder for the kernel tests and the dataset replay (stdlib only).

Frames are plain bytes for `bpftool prog run ... data_in`; checksums stay 0 (XDP ignores them).
Moved from ``tests/pktgen.py`` so that the IDS image can build replay frames.
"""
from __future__ import annotations

import socket
import struct

# Frame builders mirror header fields, so some take more than five arguments.

ETH_IP, ETH_ARP, ETH_IPV6, ETH_VLAN = 0x0800, 0x0806, 0x86DD, 0x8100
PROTO_ICMP, PROTO_TCP, PROTO_UDP = 1, 6, 17
SYN, FIN, PSH, ACK, RST = 0x02, 0x01, 0x08, 0x10, 0x04
MF = 0x2000  # IPv4 "more fragments" flag
MAC_DST, MAC_SRC = b"\x02\x00\x00\x00\x00\x01", b"\x02\x00\x00\x00\x00\x02"
IP_HDR, TCP_HDR, UDP_HDR, WORD = 20, 20, 8, 4
DEFAULT_TTL = 64


def eth(payload: bytes, ethertype: int = ETH_IP) -> bytes:
    """Wrap a payload in an Ethernet header.

    Args:
        payload: Bytes after the Ethernet header.
        ethertype: EtherType value.

    Returns:
        The frame.
    """
    return MAC_DST + MAC_SRC + struct.pack("!H", ethertype) + payload


def ipv4(src: str, dst: str, proto: int, l4: bytes, ihl: int = 5,  # pylint: disable=too-many-arguments,too-many-positional-arguments
         frag: int = 0) -> bytes:
    """Build an IPv4 packet; tot_len always matches the bytes given.

    Args:
        src: Source address.
        dst: Destination address.
        proto: IP protocol number.
        l4: Transport header plus payload.
        ihl: Header length in 32-bit words (extra words are zero options).
        frag: Flags and fragment offset field (e.g. MF).

    Returns:
        The IP packet.
    """
    hdr_len = ihl * WORD
    head = struct.pack("!BBHHHBBH4s4s", 0x40 | ihl, 0, hdr_len + len(l4), 0, frag, DEFAULT_TTL,
                       proto, 0, socket.inet_aton(src), socket.inet_aton(dst))
    return head + bytes(max(0, hdr_len - IP_HDR)) + l4


def tcp_segment(sport: int, dport: int, flags: int, payload: int = 0, doff: int = 5) -> bytes:
    """Build a TCP segment with `payload` zero bytes.

    Args:
        sport: Source port.
        dport: Destination port.
        flags: TCP flag octet.
        payload: Payload length in bytes.
        doff: Data offset in 32-bit words (extra words are zero options).

    Returns:
        The segment.
    """
    head = struct.pack("!HHIIBBHHH", sport, dport, 0, 0, doff << 4, flags, 1024, 0, 0)
    return head + bytes(max(0, doff * WORD - TCP_HDR)) + bytes(payload)


def udp_datagram(sport: int, dport: int, payload: int = 0) -> bytes:
    """Build a UDP datagram with `payload` zero bytes.

    Args:
        sport: Source port.
        dport: Destination port.
        payload: Payload length in bytes.

    Returns:
        The datagram.
    """
    return struct.pack("!HHHH", sport, dport, UDP_HDR + payload, 0) + bytes(payload)


def tcp(src: str, dst: str, sport: int, dport: int, flags: int, payload: int = 0,  # pylint: disable=too-many-arguments,too-many-positional-arguments
        ihl: int = 5, doff: int = 5, frag: int = 0) -> bytes:
    """Build an Ethernet/IPv4/TCP frame.

    Args:
        src: Source address.
        dst: Destination address.
        sport: Source port.
        dport: Destination port.
        flags: TCP flag octet.
        payload: Payload length in bytes.
        ihl: IPv4 header words.
        doff: TCP data offset words.
        frag: IPv4 flags and fragment offset.

    Returns:
        The frame.
    """
    seg = tcp_segment(sport, dport, flags, payload, doff)
    return eth(ipv4(src, dst, PROTO_TCP, seg, ihl, frag))


def udp(src: str, dst: str, sport: int, dport: int, payload: int = 0) -> bytes:
    """Build an Ethernet/IPv4/UDP frame.

    Args:
        src: Source address.
        dst: Destination address.
        sport: Source port.
        dport: Destination port.
        payload: Payload length in bytes.

    Returns:
        The frame.
    """
    return eth(ipv4(src, dst, PROTO_UDP, udp_datagram(sport, dport, payload)))


def icmp(src: str, dst: str) -> bytes:
    """Build an Ethernet/IPv4/ICMP echo request frame.

    Args:
        src: Source address.
        dst: Destination address.

    Returns:
        The frame.
    """
    return eth(ipv4(src, dst, PROTO_ICMP, struct.pack("!BBHHH", 8, 0, 0, 1, 1)))


def arp() -> bytes:
    """Build an Ethernet/ARP request frame.

    Returns:
        The frame.
    """
    body = struct.pack("!HHBBH6s4s6s4s", 1, ETH_IP, 6, 4, 1, MAC_SRC, bytes(4), bytes(6), bytes(4))
    return eth(body, ETH_ARP)


def ipv6() -> bytes:
    """Build a minimal Ethernet/IPv6 frame (no extension headers, empty UDP payload).

    Returns:
        The frame.
    """
    addr = bytes(16)
    head = struct.pack("!IHBB16s16s", 6 << 28, UDP_HDR, PROTO_UDP, DEFAULT_TTL, addr, addr)
    return eth(head + udp_datagram(1, 2), ETH_IPV6)


def vlan(inner_ip: bytes) -> bytes:
    """Build an 802.1Q frame around an IPv4 packet.

    Args:
        inner_ip: IPv4 packet (no Ethernet header).

    Returns:
        The tagged frame.
    """
    return eth(struct.pack("!HH", 1, ETH_IP) + inner_ip, ETH_VLAN)


def truncated(frame: bytes, size: int) -> bytes:
    """Cut a frame to `size` bytes.

    Args:
        frame: A complete frame.
        size: Bytes to keep.

    Returns:
        The shortened frame.
    """
    return frame[:size]
