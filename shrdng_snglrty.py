"""
Transport-agnostic sharding helpers (xxHash kept).
"""
import os
from dataclasses import dataclass
from typing import Generator, List
import xxhash

@dataclass
class Shard:
    index: int
    offset: int
    data: bytes
    hash: str  # xxh64 hex

def shard_file(file_path: str, shard_size: int) -> Generator[Shard, None, None]:
    size = os.path.getsize(file_path)
    with open(file_path, "rb") as f:
        idx, offset = 0, 0
        while True:
            chunk = f.read(shard_size)
            if not chunk:
                break
            yield Shard(
                index=idx,
                offset=offset,
                data=chunk,
                hash=xxhash.xxh64(chunk).hexdigest(),
            )
            idx += 1
            offset += len(chunk)

def shard_bytes(data: bytes, shard_size: int) -> List[Shard]:
    shards: List[Shard] = []
    for i in range(0, len(data), shard_size):
        chunk = data[i:i + shard_size]
        shards.append(
            Shard(
                index=len(shards),
                offset=i,
                data=chunk,
                hash=xxhash.xxh64(chunk).hexdigest(),
            )
        )
    return shards
