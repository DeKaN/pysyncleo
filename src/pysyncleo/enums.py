from enum import Enum, IntEnum


class ConnectionState(Enum):
    NOT_CONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    DISCONNECTED = 3


class FrameType(IntEnum):
    ACK = 0
    CMD = 1
    AUX = 2
    NAK = 255


class UdpCommandType(IntEnum):
    HANDSHAKE = 0  # (0x00) Handshake / Time start / Hardware
    MODE = 1  # (0x01) Mode / Power
    TARGET_TEMPERATURE = 2  # (0x02) Target Temperature
    TARGET_TIME = 3  # (0x03) Target Time
    RECIPE_ID = 4  # (0x04) Recipe ID
    RECIPE_STEP = 5  # (0x05) Recipe Step
    ERROR = 7  # (0x07) Error State
    JOYSTICK = 8  # (0x08) Joystick
    VOLUME = 9  # (0x09) Volume
    MAP_DATA = 10  # (0x0A) Map data
    AMOUNT = 11  # (0x0B) Amount
    DELAY_START = 13  # (0x0D) Delay Start
    MULTI_STEP = 14  # (0x0E) MultiStep
    SPEED = 15  # (0x0F) Fan Speed
    KEEP_WARM = 16  # (0x10) Keep Warm
    PRESSURE = 17  # (0x11) Pressure
    TARGET_HUMIDITY = 18  # (0x12) Target Humidity
    CURRENT_HUMIDITY = 19  # (0x13) Current Humidity
    TEMPERATURE = 20  # (0x14) Current Temperature
    MULTI_STEP_CURRENT = 21  # (0x15) MultiStep Current Step
    CO2 = 22  # (0x16) CO2 Sensor
    IONIZATION = 24  # (0x18) Ionization
    WARM_STREAM = 25  # (0x19) Warm Stream
    TOTAL_TIME = 26  # (0x1A) Total Time
    BATTERY = 27  # (0x1B) Battery Level
    BACKLIGHT = 28  # (0x1C) Display Backlight
    BATTERY_STATE = 29  # (0x1D) Battery State
    CHILD_LOCK = 30  # (0x1E) Child Lock
    TANK = 31  # (0x1F) Tank State
    PM2 = 32  # (0x20) PM 2.5 Sensor
    ULTRAVIOLET = 33  # (0x21) UV Light
    EXPENDABLES = 34  # (0x22) Expendables
    DAMPER = 38  # (0x26) Damper
    SMART_MODE = 40  # (0x28) Smart Mode
    BSS = 41  # (0x29) BSS
    STATISTICS = 44  # (0x2C) Statistics
    DATA_SOURCE = 45  # (0x2D) Data Source
    TURBO = 49  # (0x31) Turbo
    NIGHT = 50  # (0x32) Night Mode
    CURRENT_AMPERAGE = 51  # (0x33) Sensor Amperage
    POWER = 52  # (0x34) Sensor Power
    VOLTAGE = 53  # (0x35) Sensor Voltage
    SCHEDULE_SET = 64  # (0x40) Set Schedule
    SCHEDULE_REMOVE = 65  # (0x41) Remove Schedule
    PROGRAM_DATA = 66  # (0x42) Program Data
    MAP_TARGET = 67  # (0x43) Map Target
    TIME_SYNC = 128  # (0x80) Time Sync
    WIFI_LIST = 129  # (0x81) Wifi List
    WIFI_STATUS = 130  # (0x82) Wifi Status / Wifi Configuration
    CROSS_CONFIG = 131  # (0x83) Cross Config
    ACCESS_CONTROL = 133  # (0x85) Access Control
    OPEN_MQTT = 135  # (0x87) Open MQTT
    UUID = 136  # (0x88) UUID
    DEVICE_TYPE = 137  # (0x89) Device Type
    DIAGNOSTIC = 141  # (0x8D) Diagnostic
    DEVICE_HARDWARE = 143  # (0x8F) Device Hardware
    TARGET_ID = 144  # (0x90) Target ID
    DEVICE_DIAGNOSTIC = 145  # (0x91) Device Diagnostic
    PROXY_DEVICES = 160  # (0xA0) Proxy Devices
    PROXY_LINK = 161  # (0xA1) Proxy Link
    PROXY_DATA = 162  # (0xA2) Proxy Data
    PLACEHOLDER_1 = 193  # (0xC1) Placeholder Feature 1
    PLACEHOLDER_2 = 194  # (0xC2) Placeholder Feature 2
    PLACEHOLDER_3 = 195  # (0xC3) Placeholder Feature 3
    PLACEHOLDER_4 = 196  # (0xC4) Placeholder Feature 4
    PLACEHOLDER_5 = 197  # (0xC5) Placeholder Feature 5
    PLACEHOLDER_6 = 198  # (0xC6) Placeholder Feature 6
    PLACEHOLDER_7 = 199  # (0xC7) Placeholder Feature 7
    PLACEHOLDER_8 = 200  # (0xC8) Placeholder Feature 8
    PLACEHOLDER_9 = 201  # (0xC9) Placeholder Feature 9
    INTERNAL_LOGS = 240  # (0xF0) Internal logs
    UDP_FIRMWARE_V1 = 253  # (0xFD) CmdUdpFirmware V1
    UDP_FIRMWARE_V2 = 254  # (0xFE) CmdUdpFirmware V2
    PING = 255  # (0xFF) Ping
