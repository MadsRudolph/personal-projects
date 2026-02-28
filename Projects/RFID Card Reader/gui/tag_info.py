from dataclasses import dataclass
from datetime import datetime

SAK_TABLE = {
    0x08: ("MIFARE Classic 1K", "YES"),
    0x18: ("MIFARE Classic 4K", "YES"),
    0x09: ("MIFARE Mini", "YES"),
    0x20: ("MIFARE DESFire or MIFARE Plus", "NO"),
    0x00: ("MIFARE Ultralight or NTAG", "PARTIAL"),
    0x01: ("TNP3xxx (NFC Forum Type 2)", "NO"),
    0x10: ("MIFARE Plus (SL2)", "NO"),
    0x11: ("MIFARE Plus (SL3)", "NO"),
}


@dataclass
class Tag:
    atqa: str
    uid: str
    sak: int
    uid_len: int
    timestamp: datetime

    @property
    def chip_type(self) -> str:
        info = SAK_TABLE.get(self.sak)
        return info[0] if info else f"Unknown (SAK=0x{self.sak:02X})"

    @property
    def cloneable(self) -> str:
        info = SAK_TABLE.get(self.sak)
        return info[1] if info else "UNKNOWN"

    @property
    def uid_formatted(self) -> str:
        return ":".join(self.uid[i : i + 2] for i in range(0, len(self.uid), 2))
