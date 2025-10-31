"""
shrdng_snglrty.py
========================
Transport-agnostic sharding helpers for Project Singularity.
Adds per-shard header construction (64 bytes) and xxHash integrity.
"""

import os
import struct
import uuid
import xxhash
from dataclasses import dataclass
from typing import Generator, List

# ===============================================================
# Header definition (64 bytes total)
# ===============================================================

# Layout:
# > = big-endian
# 5s = magic "SLGTY"
# B  = version
# B  = flags
# Q  = session_id
# I  = shard_index
# I  = total_shards
# Q  = offset
# I  = data_length
# 16s = xxhash128 (binary)
# 14s = reserved/padding
HEADER_STRUCT = ">5sBBQIIQI16s14s"
HEADER_SIZE = struct.calcsize(HEADER_STRUCT)

MAGIC = b"SLGTY"
VERSION = 1
FLAGS_DEFAULT = 0


def pack_header(**fields) -> bytes:
    """Serialize header fields into a 64-byte binary block."""
    return struct.pack(
        HEADER_STRUCT,
        MAGIC,
        VERSION,
        fields.get("flags", FLAGS_DEFAULT),
        fields["session_id"],
        fields["shard_index"],
        fields["total_shards"],
        fields["offset"],
        fields["data_length"],
        fields["hash"],
        b"\x00" * 14,
    )


def unpack_header(data: bytes) -> dict:
    """Deserialize a 64-byte header into a Python dict."""
    (
        magic,
        version,
        flags,
        session_id,
        shard_index,
        total_shards,
        offset,
        data_length,
        hash_bytes,
        _,
    ) = struct.unpack(HEADER_STRUCT, data)
    return {
        "magic": magic.decode(errors="ignore"),
        "version": version,
        "flags": flags,
        "session_id": session_id,
        "shard_index": shard_index,
        "total_shards": total_shards,
        "offset": offset,
        "data_length": data_length,
        "hash": hash_bytes,
    }


# ===============================================================
# Shard class + helpers
# ===============================================================

@dataclass
class Shard:
    index: int
    offset: int
    data: bytes
    hash: bytes  # 16-byte binary hash
    header: bytes = b""

    def build_header(self, session_id: int, total_shards: int) -> None:
        """Construct and store binary header for this shard."""
        self.header = pack_header(
            session_id=session_id,
            shard_index=self.index,
            total_shards=total_shards,
            offset=self.offset,
            data_length=len(self.data),
            hash=self.hash,
        )

    def to_bytes(self) -> bytes:
        """Return full transmit-ready packet: [HEADER][DATA]."""
        return self.header + self.data


# ===============================================================
# Sharding logic
# ===============================================================

def shard_file(file_path: str, shard_size: int) -> Generator[Shard, None, None]:
    """Yield Shard objects from file, ready to transmit."""
    session_id = uuid.uuid4().int >> 64  # 64-bit session ID
    size = os.path.getsize(file_path)
    total = (size + shard_size - 1) // shard_size

    with open(file_path, "rb") as f:
        idx, offset = 0, 0
        while True:
            chunk = f.read(shard_size)
            if not chunk:
                break

            shard_hash = xxhash.xxh128(chunk).digest()
            s = Shard(index=idx, offset=offset, data=chunk, hash=shard_hash)
            s.build_header(session_id, total)
            yield s

            idx += 1
            offset += len(chunk)


def shard_bytes(data: bytes, shard_size: int) -> List[Shard]:
    """Shard an in-memory bytes object."""
    session_id = uuid.uuid4().int >> 64
    total = (len(data) + shard_size - 1) // shard_size
    shards: List[Shard] = []

    for i in range(0, len(data), shard_size):
        chunk = data[i:i + shard_size]
        shard_hash = xxhash.xxh128(chunk).digest()
        s = Shard(index=len(shards), offset=i, data=chunk, hash=shard_hash)
        s.build_header(session_id, total)
        shards.append(s)

    return shards
