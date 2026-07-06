import asyncio
import logging
from typing import Dict

from zeroconf import ServiceStateChange
from zeroconf.asyncio import AsyncServiceBrowser, AsyncServiceInfo, AsyncZeroconf

from pysyncleo.commands import CmdInitDiagnostic
from pysyncleo.const import SYNCLEO_MDNS_TYPE
from pysyncleo.enums import ConnectionState
from pysyncleo.models import SyncleoUdpDevice
from pysyncleo.transport import SyncleoConnection, TransportManager

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
_LOGGER = logging.getLogger("syncleo_example")


class AsyncDiscoveryListener:
    """Non-blocking listener for mDNS state changes."""

    def __init__(self, queue: asyncio.Queue):
        self.queue = queue

    def async_on_service_state_change(
        self, zeroconf, service_type: str, name: str, state_change: ServiceStateChange
    ) -> None:
        """Called synchronously by zeroconf, but spawns an async task to resolve info."""
        if state_change is ServiceStateChange.Added:
            asyncio.create_task(self.resolve_service(zeroconf, service_type, name))

    async def resolve_service(self, zeroconf, service_type: str, name: str):
        info = AsyncServiceInfo(service_type, name)

        await info.async_request(zeroconf, 3000)

        if info and info.parsed_addresses():
            ip_address = info.parsed_addresses()[0]

            self.queue.put_nowait(
                {
                    "ip": ip_address,
                    "port": info.port,
                    "txt": info.decoded_properties,
                    "name": name,
                }
            )


def state_update_callback(cmd):
    _LOGGER.info(f"🟢 DEVICE STATE UPDATE: {cmd}")


async def interact_with_device(conn):
    for _ in range(10):
        if conn.state == ConnectionState.CONNECTED:
            break
        await asyncio.sleep(0.5)

    if conn.state != ConnectionState.CONNECTED:
        _LOGGER.error(f"❌ Handshake timed out for {conn.device.inet_address[0]}")
        return

    _LOGGER.info(f"✅ Secure Session Established with {conn.device.inet_address[0]}!")
    await asyncio.sleep(1.5)

    _LOGGER.info("📡 Requesting deep network diagnostics...")
    await conn.send_command(CmdInitDiagnostic(mode=0))


async def main():
    loop = asyncio.get_running_loop()

    manager = TransportManager()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: manager, local_addr=("0.0.0.0", 0)
    )

    discovery_queue = asyncio.Queue()
    listener = AsyncDiscoveryListener(discovery_queue)
    aiozc = AsyncZeroconf()

    browser = AsyncServiceBrowser(
        aiozc.zeroconf,
        [SYNCLEO_MDNS_TYPE],
        handlers=[listener.async_on_service_state_change],
    )

    _LOGGER.info("🔍 Searching for Syncleo devices on the local network...")
    active_connections: Dict[str, "SyncleoConnection"] = {}

    try:
        while True:
            discovered = await discovery_queue.get()
            ip = discovered["ip"]

            if ip in active_connections:
                continue

            _LOGGER.info(
                f"💡 Found Device: {discovered['name']} at {ip}:{discovered['port']}. Properties: {discovered}"
            )

            device = SyncleoUdpDevice.from_zeroconf(
                ip, discovered["port"], discovered["txt"]
            )

            conn = manager.register_device(device)
            if not conn:
                continue

            conn.register_callback(state_update_callback)
            active_connections[ip] = conn

            await conn.connect()
            asyncio.create_task(interact_with_device(conn))

    except asyncio.CancelledError:
        pass
    finally:
        _LOGGER.info("Closing sockets and network listeners...")

        if conn:
            conn.unregister_callback(state_update_callback)
        await browser.async_cancel()
        await aiozc.async_close()
        transport.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting script...")
