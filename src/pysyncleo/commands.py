import struct
from typing import Any, Dict, Optional, Tuple, Type

from .enums import UdpCommandType
from .models import DiagnosticStatus, OpenMqttConfig
from .utils import is_bit_enabled


class UdpCommand:
    command_type: Optional[UdpCommandType] = None
    
    COMMAND_REGISTRY: Dict[UdpCommandType, Type['UdpCommand']] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        
        cmd_type = getattr(cls, 'command_type', None)

        if cmd_type is not None:
            cls.COMMAND_REGISTRY[cmd_type] = cls

    def __init__(self, value: Any = None, byte_size: int = 1):
        self.value = value
        self.byte_size = byte_size

    def serialize(self) -> bytes:
        return b''

    def deserialize(self, payload: bytes) -> None:
        pass

    @classmethod
    def from_bytes(cls, payload: bytes) -> Optional['UdpCommand']:
        if not payload:
            return None

        command_type_id = payload[0]
        cmd_data = payload[1:]

        try:
            cmd_type = UdpCommandType(command_type_id)
        except ValueError:
            return None

        cmd_class = cls.COMMAND_REGISTRY.get(cmd_type)
        
        if not cmd_class:
            cmd = cls(value=cmd_data)
            cmd.command_type = cmd_type
            return cmd

        cmd = cmd_class()
        cmd.command_type = cmd_type
        cmd.deserialize(cmd_data) 
        
        return cmd

class SyncleoBoolCommand(UdpCommand):
    """Handles 1-byte True/False toggles (0x00 or 0x01)"""
    def __init__(self, state: bool = False):
        super().__init__(state)
    def serialize(self) -> bytes:
        return struct.pack('<B', 1 if self.value else 0)
    def deserialize(self, payload: bytes) -> None:
        if len(payload) >= 1:
            self.value = bool(payload[0])

class SyncleoByteCommand(UdpCommand):
    """Handles 1-byte Unsigned Integers"""
    def __init__(self, val: int = 0):
        super().__init__(val)
    def serialize(self) -> bytes:
        return struct.pack('<B', int(self.value) & 0xFF)
    def deserialize(self, payload: bytes) -> None:
        if len(payload) >= 1:
            self.value = payload[0]

class SyncleoShortCommand(UdpCommand):
    """Handles 2-byte Unsigned Integers"""
    def __init__(self, val: int = 0):
        super().__init__(val)
    def serialize(self) -> bytes:
        return struct.pack('<H', int(self.value) & 0xFFFF)
    def deserialize(self, payload: bytes) -> None:
        if len(payload) >= 2:
            self.value = struct.unpack('<H', payload[:2])[0]

class SyncleoIntCommand(UdpCommand):
    """Handles 4-byte Unsigned Integers"""
    def __init__(self, val: int = 0):
        super().__init__(val)
    def serialize(self) -> bytes:
        return struct.pack('<I', int(self.value) & 0xFFFFFFFF)
    def deserialize(self, payload: bytes) -> None:
        if len(payload) >= 4:
            self.value = struct.unpack('<I', payload[:4])[0]

class SyncleoFloatCommand(UdpCommand):
    """
    Handles the custom Float (Integer Byte + Fraction Byte + Sign Bit) format.
    """
    def __init__(self, value: float = 0.0): 
        super().__init__(value)

    def serialize(self) -> bytes:
        val = float(self.value)
        int_part = int(abs(val))
        
        frac_part = int(round((abs(val) - int_part) * 100))

        if val < 0:
            frac_part |= 0x80 

        return struct.pack('<BB', int_part, frac_part)

    def deserialize(self, payload: bytes) -> None:
        if len(payload) >= 2:
            int_part = payload[0]
            frac_part = payload[1]

            is_negative = (frac_part & 0x80) != 0
            actual_frac = frac_part & 0x7F 

            self.value = float(int_part) + (actual_frac / 100.0)
            
            if is_negative:
                self.value = -self.value

class SyncleoCompositeCommand(UdpCommand):
    """Base class for commands with multiple combined data types."""
    def __init__(self, *args):
        super().__init__(list(args))

class SyncleoRawCommand(UdpCommand):
    """Handles raw byte payloads without any specific structure."""
    def __init__(self, data: bytes = b''):
        super().__init__(data)
    def serialize(self) -> bytes:
        return self.value if isinstance(self.value, bytes) else b''
    def deserialize(self, payload: bytes) -> None:
        self.value = payload


class CmdPowerMode(SyncleoBoolCommand):
    command_type = UdpCommandType.MODE
class CmdKeepWarm(SyncleoBoolCommand):
    command_type = UdpCommandType.KEEP_WARM
class CmdIonization(SyncleoBoolCommand):
    command_type = UdpCommandType.IONIZATION
class CmdWarmStream(SyncleoBoolCommand):
    command_type = UdpCommandType.WARM_STREAM
class CmdBacklight(SyncleoBoolCommand):
    command_type = UdpCommandType.BACKLIGHT
class CmdChildLock(SyncleoBoolCommand):
    command_type = UdpCommandType.CHILD_LOCK
class CmdUltraviolet(SyncleoBoolCommand):
    command_type = UdpCommandType.ULTRAVIOLET
class CmdSmartMode(SyncleoBoolCommand):
    command_type = UdpCommandType.SMART_MODE
class CmdTurbo(SyncleoBoolCommand):
    command_type = UdpCommandType.TURBO
class CmdNight(SyncleoBoolCommand):
    command_type = UdpCommandType.NIGHT
class CmdAccessControl(SyncleoBoolCommand):
    command_type = UdpCommandType.ACCESS_CONTROL

class CmdRecipeId(SyncleoByteCommand):
    command_type = UdpCommandType.RECIPE_ID
class CmdRecipeStep(SyncleoByteCommand):
    command_type = UdpCommandType.RECIPE_STEP
class CmdError(SyncleoByteCommand):
    command_type = UdpCommandType.ERROR
class CmdVolume(SyncleoByteCommand):
    command_type = UdpCommandType.VOLUME
class CmdSpeed(SyncleoByteCommand):
    command_type = UdpCommandType.SPEED
class CmdMultiStepCurrent(SyncleoByteCommand):
    command_type = UdpCommandType.MULTI_STEP_CURRENT
class CmdBattery(SyncleoByteCommand):
    command_type = UdpCommandType.BATTERY
class CmdBatteryState(SyncleoByteCommand):
    command_type = UdpCommandType.BATTERY_STATE
class CmdTank(SyncleoByteCommand):
    command_type = UdpCommandType.TANK
class CmdDamper(SyncleoByteCommand):
    command_type = UdpCommandType.DAMPER
class CmdBss(SyncleoByteCommand): 
    command_type = UdpCommandType.BSS
class CmdPlaceholder1(SyncleoByteCommand):
    command_type = UdpCommandType.PLACEHOLDER_1
class CmdPlaceholder2(SyncleoByteCommand):
    command_type = UdpCommandType.PLACEHOLDER_2
class CmdPlaceholder3(SyncleoByteCommand):
    command_type = UdpCommandType.PLACEHOLDER_3

class CmdAmount(SyncleoShortCommand):
    command_type = UdpCommandType.AMOUNT
class CmdPressure(SyncleoShortCommand):
    command_type = UdpCommandType.PRESSURE
class CmdCO2(SyncleoShortCommand):
    command_type = UdpCommandType.CO2
class CmdPM2(SyncleoShortCommand):
    command_type = UdpCommandType.PM2
class CmdAmperage(SyncleoShortCommand):
    command_type = UdpCommandType.CURRENT_AMPERAGE
class CmdVoltage(SyncleoShortCommand):
    command_type = UdpCommandType.VOLTAGE
class CmdDeviceType(SyncleoShortCommand):
    command_type = UdpCommandType.DEVICE_TYPE
class CmdPlaceholder4(SyncleoShortCommand):
    command_type = UdpCommandType.PLACEHOLDER_4
class CmdPlaceholder5(SyncleoShortCommand):
    command_type = UdpCommandType.PLACEHOLDER_5
class CmdPlaceholder6(SyncleoShortCommand):
    command_type = UdpCommandType.PLACEHOLDER_6

class CmdTargetTime(SyncleoIntCommand):
    command_type = UdpCommandType.TARGET_TIME
class CmdDelayStart(SyncleoIntCommand):
    command_type = UdpCommandType.DELAY_START
class CmdTotalTime(SyncleoIntCommand):
    command_type = UdpCommandType.TOTAL_TIME
class CmdStatistics(SyncleoIntCommand):
    command_type = UdpCommandType.STATISTICS
class CmdPower(SyncleoIntCommand):
    command_type = UdpCommandType.POWER
class CmdPlaceholder7(SyncleoIntCommand):
    command_type = UdpCommandType.PLACEHOLDER_7
class CmdPlaceholder8(SyncleoIntCommand):
    command_type = UdpCommandType.PLACEHOLDER_8
class CmdPlaceholder9(SyncleoIntCommand):
    command_type = UdpCommandType.PLACEHOLDER_9

class CmdTargetTemperature(SyncleoFloatCommand):
    command_type = UdpCommandType.TARGET_TEMPERATURE
class CmdTargetHumidity(SyncleoFloatCommand):
    command_type = UdpCommandType.TARGET_HUMIDITY
class CmdCurrentHumidity(SyncleoFloatCommand):
    command_type = UdpCommandType.CURRENT_HUMIDITY
class CmdCurrentTemperature(SyncleoFloatCommand):
    command_type = UdpCommandType.TEMPERATURE

class CmdJoystick(SyncleoRawCommand):
    command_type = UdpCommandType.JOYSTICK
class CmdMapData(SyncleoRawCommand):
    command_type = UdpCommandType.MAP_DATA
class CmdMultiStep(SyncleoRawCommand):
    command_type = UdpCommandType.MULTI_STEP
class CmdExpendables(SyncleoRawCommand):
    command_type = UdpCommandType.EXPENDABLES
class CmdDataSource(SyncleoRawCommand):
    command_type = UdpCommandType.DATA_SOURCE
class CmdScheduleSet(SyncleoRawCommand):
    command_type = UdpCommandType.SCHEDULE_SET
class CmdScheduleRemove(SyncleoRawCommand):
    command_type = UdpCommandType.SCHEDULE_REMOVE
class CmdProgramData(SyncleoRawCommand):
    command_type = UdpCommandType.PROGRAM_DATA
class CmdMapTarget(SyncleoRawCommand):
    command_type = UdpCommandType.MAP_TARGET
class CmdWifiList(SyncleoRawCommand):
    command_type = UdpCommandType.WIFI_LIST
class CmdWifiStatus(SyncleoRawCommand):
    command_type = UdpCommandType.WIFI_STATUS
class CmdUUID(SyncleoRawCommand):
    command_type = UdpCommandType.UUID
class CmdTargetId(SyncleoRawCommand):
    command_type = UdpCommandType.TARGET_ID
class CmdDeviceDiagnostic(SyncleoRawCommand):
    command_type = UdpCommandType.DEVICE_DIAGNOSTIC
class CmdProxyDevices(SyncleoRawCommand):
    command_type = UdpCommandType.PROXY_DEVICES
class CmdProxyLink(SyncleoRawCommand):
    command_type = UdpCommandType.PROXY_LINK
class CmdProxyData(SyncleoRawCommand):
    command_type = UdpCommandType.PROXY_DATA

class CmdHandshake(UdpCommand):
    command_type = UdpCommandType.HANDSHAKE
    
    def __init__(self, token: bytes = b''):
        super().__init__(token)
        
    def serialize(self) -> bytes:
        return self.value if isinstance(self.value, bytes) else b''

    def deserialize(self, payload: bytes) -> None:        
        if len(payload) < 21:
            return
            
        self.protocol_version = struct.unpack('<H', payload[0:2])[0]
        self.fw_major = payload[2]
        self.fw_minor = payload[3]
        self.mode = payload[4]
        self.token = payload[5:21]
        
        self.value = self.token

class CmdTimeSync(SyncleoCompositeCommand):
    command_type = UdpCommandType.TIME_SYNC

    def __init__(self, timestamp: int = 0, offset: int = 0):
        super().__init__(timestamp, offset)
    
    def serialize(self) -> bytes:
        return struct.pack('<Ih', int(self.value[0]), int(self.value[1]))

class CmdOpenMqtt(UdpCommand):
    command_type = UdpCommandType.OPEN_MQTT

    def __init__(self, config: Optional[OpenMqttConfig] = None):
        super().__init__(config or OpenMqttConfig())

    def serialize(self) -> bytes:
        cfg: OpenMqttConfig = self.value
        
        host_b = (cfg.host.encode('utf-8') if cfg.host else b'')[:255]
        user_b = (cfg.username.encode('utf-8') if cfg.username else b'')[:255]
        pass_b = (cfg.password.encode('utf-8') if cfg.password else b'')[:255]
        
        secure_val = 1 if cfg.secure else 0
        port_val = cfg.port if cfg.port > 0 else (8883 if cfg.secure else 1883)
        
        return (
            struct.pack('<BH', secure_val, port_val)
            + bytes([len(host_b)]) + host_b
            + bytes([len(user_b)]) + user_b
            + bytes([len(pass_b)]) + pass_b
        )

    def deserialize(self, payload: bytes) -> None:
        if len(payload) < 6:
            return

        secure_byte, port = struct.unpack_from('<BH', payload, 0)
        ptr = 3
        
        def read_string(p: int) -> Tuple[str, int]:
            if p >= len(payload):
                return "", p
            length = payload[p]
            p += 1
            data = payload[p : p + length].decode('utf-8', errors='ignore')
            return data, p + length

        host, ptr = read_string(ptr)
        username, ptr = read_string(ptr)
        password, ptr = read_string(ptr)

        enabled = bool(secure_byte or port != 0 or host or username or password)
        
        self.value = OpenMqttConfig(
            secure=(secure_byte != 0),
            host=host,
            port=port,
            username=username,
            password=password,
            enabled=enabled
        )

class CmdInitDiagnostic(UdpCommand):
    command_type = UdpCommandType.DIAGNOSTIC

    def __init__(self, mode: int = 0, ssid: str = ""):
        self.mode = mode
        self.ssid = ssid
        self.status: Optional[DiagnosticStatus] = None
        super().__init__(mode)

    def serialize(self) -> bytes:
        if self.mode == -2:
            ssid_bytes = self.ssid.encode('utf-8')
            return bytes([self.mode & 0xFF, len(ssid_bytes) & 0xFF]) + ssid_bytes
        return bytes([self.mode & 0xFF])

    def deserialize(self, payload: bytes) -> None:
        if len(payload) == 0:
            return
            
        self.mode = payload[0]
        
        if self.mode == 0 and len(payload) >= 15:
            bits = payload[1]
            self.status = DiagnosticStatus(
                hotspot_up=is_bit_enabled(bits, 0),
                wifi_configured=is_bit_enabled(bits, 1),
                wifi_connected=is_bit_enabled(bits, 2),
                mqtt_connected=is_bit_enabled(bits, 3),
                rssi=payload[2],
                wifi_bssid=payload[3:9],
            )
            
            ssid_len = payload[9]
            if ssid_len > 0:
                self.status.ssid = payload[10 : 10 + ssid_len].decode('utf-8', 'ignore').strip()
            
            ptr = 10 + ssid_len
            if len(payload) >= ptr + 5:
                self.status.gw_ping, self.status.gw_loss, self.status.mqtt_ping = struct.unpack('<hbh', payload[ptr : ptr + 5])
            
            self.value = self.status

class CmdPing(UdpCommand):
    command_type = UdpCommandType.PING
    def __init__(self):
        super().__init__(None)
