"""
sndr_snglty.py — Header-aware streaming sender
for Project Singularity.
Streams shards from disk instead of preloading.
"""

import asyncio
import struct
import time
from typing import Dict, Tuple
from shrdng_snglrty import shard_file
from utils_net import tune_socket
import config
import os

LEN_FMT = "!I"  # uint32 big-endian
LEN_SIZE = 4


async def send_on_lane(port: int, queue: asyncio.Queue):
    """Consume packets from a queue and send them over one persistent TCP lane."""
    reader, writer = await asyncio.open_connection(config.HOST_IP, port)
    sock = writer.get_extra_info("socket")
    if sock:
        tune_socket(sock, getattr(config, "SO_SNDBUF", 0), getattr(config, "SO_RCVBUF", 0))

    pending = 0
    try:
        while True:
            pkt = await queue.get()
            if pkt is None:  # shutdown sentinel
                break
            writer.write(struct.pack(LEN_FMT, len(pkt)))
            writer.write(pkt)
            pending += len(pkt)
            if pending >= config.DRAIN_BATCH_BYTES:
                await writer.drain()
                pending = 0
        # end-of-stream marker
        writer.write(struct.pack(LEN_FMT, 0))
        await writer.drain()
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def main():
    """Shard and stream file shards dynamically through multiple ports."""
    if getattr(config, "USE_UVLOOP", False):
        try:
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        except Exception:
            pass

    total_bytes = os.path.getsize(config.TEST_FILE)
    print(f"[TX] Streaming {total_bytes/1e9:.2f} GB from {config.TEST_FILE}")

    # Create a queue per port (one per lane)
    queues: Dict[int, asyncio.Queue] = {p: asyncio.Queue(maxsize=8) for p in config.SEND_PORTS}
    tasks = [asyncio.create_task(send_on_lane(p, q)) for p, q in queues.items()]

    # Stream shards in real time (memory constant)
    shard_count = 0
    start = time.perf_counter()
    for shard in shard_file(config.TEST_FILE, config.SHARD_SIZE_BYTES):
        pkt = shard.to_bytes()
        port = config.SEND_PORTS[shard.index % len(config.SEND_PORTS)]
        await queues[port].put(pkt)
        shard_count += 1

    # Signal all lanes to close
    for q in queues.values():
        await q.put(None)

    await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start
    gbps = (total_bytes * 8 / 1e9) / elapsed if elapsed > 0 else 0.0
    print(f"[TX] Sent {total_bytes/1e9:.2f} GB ({shard_count} shards) in {elapsed:.2f}s → {gbps:.2f} Gbps")


if __name__ == "__main__":
    asyncio.run(main())
