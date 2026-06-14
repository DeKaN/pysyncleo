def is_bit_enabled(byte_val: int, bit_index: int) -> bool:
    return (byte_val & (1 << bit_index)) != 0

def format_mac_address(raw_mac: str) -> str:
    if not raw_mac:
        return ""
        
    clean_mac = raw_mac.replace(":", "").replace("-", "").replace(" ", "").upper()
    
    if len(clean_mac) != 12:
        return clean_mac
        
    return ":".join(clean_mac[i:i+2] for i in range(0, 12, 2))
