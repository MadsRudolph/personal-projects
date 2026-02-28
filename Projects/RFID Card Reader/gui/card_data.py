class CardData:
    """Holds a complete MIFARE Classic 1K card dump (64 blocks, 16 bytes each)."""

    def __init__(self):
        self._blocks = {}

    @property
    def block_count(self):
        return len(self._blocks)

    @property
    def has_data(self):
        return len(self._blocks) > 0

    def set_block(self, block, hex_data):
        self._blocks[block] = hex_data.upper()

    def get_block(self, block):
        return self._blocks.get(block)

    def clear(self):
        self._blocks.clear()

    @staticmethod
    def sector_for_block(block):
        return block // 4

    @staticmethod
    def is_sector_trailer(block):
        return block % 4 == 3

    def blocks_for_write(self, allow_block0=False):
        result = []
        for block in sorted(self._blocks.keys()):
            if block == 0 and not allow_block0:
                continue
            result.append((block, self._blocks[block]))
        return result

    def save_bin(self, path):
        with open(path, "wb") as f:
            for block in range(64):
                data = self._blocks.get(block)
                if data:
                    f.write(bytes.fromhex(data))
                else:
                    f.write(b"\x00" * 16)

    def load_bin(self, path):
        self.clear()
        with open(path, "rb") as f:
            raw = f.read()
        for block in range(64):
            offset = block * 16
            if offset + 16 <= len(raw):
                self._blocks[block] = raw[offset : offset + 16].hex().upper()
