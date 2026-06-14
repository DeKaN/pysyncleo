import asyncio
import time
import logging
from typing import Callable, Dict, Optional, Tuple

from .const import MAX_RETRIES, PING_INTERVAL, RETRY_TIMEOUT

from .commands import CmdHandshake, CmdInitDiagnostic, CmdPing, CmdTimeSync, UdpCommand
from .encoding import CryptoV2Encoder, PlainEncoder
from .enums import ConnectionState, FrameType, UdpCommandType
from .models import SyncleoUdpDevice, UnackedMessage


_LOGGER = logging.getLogger(__name__)

class SyncleoConnection:    
    def __init__(self, device: SyncleoUdpDevice, transport: asyncio.DatagramTransport):
        self.device = device
        self.transport = transport
        self.state = ConnectionState.NOT_CONNECTED
        
        self.inseq = 0
        self.outseq = 0
        self._unacked_seq: Dict[int, UnackedMessage] = {}
        self.on_state_updated: Optional[Callable[[UdpCommand], None]] = None
        self.last_activity = time.monotonic()

        if self.device.protocol < 2:
            self.encoder = PlainEncoder(self.device)
        else:
            self.encoder = CryptoV2Encoder(self.device)

        self._loop_task = asyncio.create_task(self._session_loop())

    def _send_bytes(self, data: bytes):
        _LOGGER.debug(f"TX [{self.device.inet_address[0]}]: {data.hex()}")
        self.last_activity = time.monotonic()
        self.transport.sendto(data, self.device.inet_address)

    async def connect(self):
        self.state = ConnectionState.CONNECTING
        self.outseq = 0
        
        _LOGGER.info(f"Initiating Handshake with {self.device.inet_address[0]}...")
        
        handshake_frame = self.encoder.generate_handshake()
        
        self._unacked_seq[0] = UnackedMessage(
            frame=handshake_frame, 
            attempts=1, 
            last_sent=time.monotonic()
        )
        self._send_bytes(handshake_frame)

    async def _run_initialization(self, mode: int):
        await asyncio.sleep(0.5) 
        
        _LOGGER.debug("Sending Time Sync...")
        current_unix_time = int(time.time())
        await self.send_command(CmdTimeSync(current_unix_time))
        
        if mode == 1:
            _LOGGER.debug("Mode 1 detected: Triggering Diagnostic Init...")
            await asyncio.sleep(0.2)
            await self.send_command(CmdInitDiagnostic())

    async def send_command(self, cmd: UdpCommand):
        if self.state != ConnectionState.CONNECTED:
            _LOGGER.warning("Cannot send command, device not connected.")
            return
        
        if cmd.command_type is None:
            _LOGGER.error("Cannot send command: command_type is not defined.")
            return

        self.outseq = (self.outseq + 1) % 256
        seq = self.outseq

        payload = bytes([cmd.command_type.value]) + cmd.serialize()
        frame = self.encoder.encode(seq, FrameType.CMD, payload)

        self._unacked_seq[seq] = UnackedMessage(
            frame=frame, 
            attempts=1, 
            last_sent=time.monotonic()
        )
        self._send_bytes(frame)

    def feed_datagram(self, data: bytes):
        _LOGGER.debug(f"RX [{self.device.inet_address[0]}]: {data.hex()}")
        self.last_activity = time.monotonic()
        
        try:
            seq, frame_type, payload = self.encoder.decode(data)
        except Exception as e:
            _LOGGER.error(f"Failed to process frame: {e}")
            return

        self.inseq = seq

        if frame_type == FrameType.ACK:
            if seq in self._unacked_seq:
                del self._unacked_seq[seq]
            return

        if frame_type == FrameType.CMD:
            ack_frame = self.encoder.encode(seq, FrameType.ACK, b'')
            self._send_bytes(ack_frame)

            parsed_cmd = UdpCommand.from_bytes(payload)
            if not parsed_cmd:
                return
            
            if isinstance(parsed_cmd, CmdHandshake) and self.state == ConnectionState.CONNECTING:
                self.state = ConnectionState.CONNECTED
                
                _LOGGER.info(
                    f"Device Connected! "
                    f"Protocol: v{parsed_cmd.protocol_version} | "
                    f"Firmware: {parsed_cmd.fw_major}.{parsed_cmd.fw_minor} | "
                    f"Mode: {parsed_cmd.mode}"
                )
                
                if 0 in self._unacked_seq: 
                    del self._unacked_seq[0]
                
                asyncio.create_task(self._run_initialization(parsed_cmd.mode))
                return

            if parsed_cmd.command_type in (UdpCommandType.PING, UdpCommandType.TIME_SYNC):
                return 
            
            if parsed_cmd.command_type is None:
                _LOGGER.warning("Received command with no command_type defined.")
                return

            _LOGGER.debug(f"Parsed State: {parsed_cmd.command_type.name} = {parsed_cmd.value}")
            if self.on_state_updated:
                self.on_state_updated(parsed_cmd)

    async def _session_loop(self):
        while True:
            try:
                await asyncio.sleep(0.5)
                now = time.monotonic()
                
                if self.state == ConnectionState.CONNECTED:
                    if now - self.last_activity >= PING_INTERVAL:
                        _LOGGER.debug(f"Idle for {PING_INTERVAL}s. Sending Keep-Alive PING to {self.device.inet_address[0]}")
                        await self.send_command(CmdPing())

                unacked_keys = list(self._unacked_seq.keys())
                
                for seq in unacked_keys:
                    msg = self._unacked_seq.get(seq)
                    if not msg:
                        continue
                        
                    if now - msg.last_sent >= RETRY_TIMEOUT:
                        if msg.attempts >= MAX_RETRIES:
                            _LOGGER.warning(f"Dropping packet seq={seq} after {MAX_RETRIES} failed attempts.")
                            
                            if seq == 0 and self.state == ConnectionState.CONNECTING:
                                self.state = ConnectionState.NOT_CONNECTED
                                
                            del self._unacked_seq[seq]
                        else:
                            msg.attempts += 1
                            msg.last_sent = now
                            _LOGGER.debug(f"Retrying packet seq={seq} (Attempt {msg.attempts}/{MAX_RETRIES})")
                            self._send_bytes(msg.frame)
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                _LOGGER.error(f"Error in session loop: {e}")

class TransportManager(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None
        self.devices: Dict[Tuple[str, int], SyncleoUdpDevice] = {}
        self.connections: Dict[Tuple[str, int], SyncleoConnection] = {}

    def connection_made(self, transport):
        self.transport = transport
        _LOGGER.info("Syncleo Transport Bound.")

    def datagram_received(self, data: bytes, addr: Tuple[str, int]):
        if addr in self.connections:
            self.connections[addr].feed_datagram(data)

    def register_device(self, device: SyncleoUdpDevice) -> Optional[SyncleoConnection]:
        if self.transport is None:
            _LOGGER.error(f"Cannot register {device.mac_address}: UDP socket is not bound yet!")
            return None
        self.devices[device.inet_address] = device
        conn = SyncleoConnection(device, self.transport)
        self.connections[device.inet_address] = conn
        return conn

