from dataclasses import dataclass, field
import logging
from typing import Any, Optional, Tuple

from .utils import format_mac_address


_LOGGER = logging.getLogger(__name__)


@dataclass
class UnackedMessage:
    frame: bytes
    attempts: int
    last_sent: float


@dataclass
class SyncleoUdpDevice:
    mac_address: str
    inet_address: Tuple[str, int]
    vendor: str = "Unknown"
    device_type: int = 0
    protocol: int = 1
    device_token: bytes = field(default_factory=lambda: b"\x00" * 16)
    device_pubkey: Optional[bytes] = None

    @classmethod
    def from_zeroconf(
        cls, ip: str, port: int, txt: dict[str, Any]
    ) -> "SyncleoUdpDevice":
        mac = format_mac_address(txt.get("mac", "00:00:00:00:00:00"))
        vendor = txt.get("vendor", "Unknown")
        device_type = int(txt.get("devtype", 0))
        protocol = int(txt.get("protocol", 1))
        token = bytes.fromhex(txt.get("token", "00" * 16))
        pubkey = bytes.fromhex(txt["public"]) if "public" in txt else None
        curve = int(txt.get("curve", 0))
        pubkey_length = len(pubkey) if pubkey else 0
        if protocol >= 2 and (curve != 29 or pubkey_length != 32):
            _LOGGER.warning(
                f"Device at {ip}:{port} advertises protocol version {protocol} with curve {curve} and public key size {pubkey_length}. Fallback to protocol 1."
            )
            protocol = 1
        return cls(mac, (ip, port), vendor, device_type, protocol, token, pubkey)


@dataclass
class OpenMqttConfig:
    secure: bool = False
    host: str = ""
    port: int = 1883
    username: str = ""
    password: str = ""
    enabled: bool = False


@dataclass
class DiagnosticStatus:
    """Detailed health report returned by the appliance."""

    hotspot_up: bool = False
    wifi_configured: bool = False
    wifi_connected: bool = False
    mqtt_connected: bool = False
    rssi: int = 0
    wifi_bssid: bytes = b""
    ssid: str = ""
    gw_ping: int = 0
    gw_loss: int = 0
    mqtt_ping: int = 0
