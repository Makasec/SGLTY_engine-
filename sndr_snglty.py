"""
Sender with:
- Pre-opened persistent connections (one per port)
- Length-prefixed frames (uint32 BE) per shard
- Batched drain to reduce context switches
- Socket tuning
- Robust gather (return_exceptions=True) so failures don't hang the run
"""
import asyncio, time, struct
from typing import Dict, List, Tuple
from shrdng_snglrty import shard_file
from utils_net import tune_socket
import config

LEN_FMT = "!I"  # uint32 big-endian
LEN_SIZE = 4

async def open_lanes() -> Dict[int, Tuple[asyncio.StreamReader, asyncio.StreamWriter]]:
    lanes: Dict[int, Tuple[asyncio.StreamReader, asyncio.StreamWriter]] = {}
    for port in config.PORTS:
        reader, writer = await asyncio.open_connection(config.HOST, port)
        sock = writer.get_extra_info("socket")
        if sock:
            tune_socket(sock, config.SO_SNDBUF, config.SO_RCVBUF)
        lanes[port] = (reader, writer)
    return lanes

async def send_on_lane(port: int, shards: List[bytes]):
    reader, writer = await asyncio.open_connection(config.HOST, port)
    sock = writer.get_extra_info("socket")
    if sock:
        tune_socket(sock, config.SO_SNDBUF, config.SO_RCVBUF)

    pending = 0
    try:
        for payload in shards:
            writer.write(struct.pack(LEN_FMT, len(payload)))
            writer.write(payload)
            pending += len(payload)
            if pending >= config.DRAIN_BATCH_BYTES:
                await writer.drain()
                pending = 0
        # final drain and graceful end-of-stream
        writer.write(struct.pack(LEN_FMT, 0))
        await writer.drain()
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass

async def main():
    if config.USE_UVLOOP:
        try:
            import uvloop, asyncio as _a
            _a.set_event_loop_policy(uvloop.EventLoopPolicy())
        except Exception:
            pass

    # Prepare shards once
    shards = list(shard_file(config.FILE_PATH, config.SHARD_SIZE_BYTES))
    total_bytes = sum(len(s.data) for s in shards)
    print(f"[TX] Prepared {len(shards)} shards ({total_bytes/1e9:.2f} GB total)")

    # Stripe shards across ports
    buckets: Dict[int, List[bytes]] = {p: [] for p in config.PORTS}
    for s in shards:
        port = config.PORTS[s.index % len(config.PORTS)]
        buckets[port].append(s.data)

    t0 = time.perf_counter()
    tasks = [asyncio.create_task(send_on_lane(p, buckets[p])) for p in config.PORTS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    t1 = time.perf_counter()

    for r in results:
        if isinstance(r, Exception):
            print(f"[TX] lane error: {r}")

    elapsed = t1 - t0
    gbps = (total_bytes * 8 / 1e9) / elapsed if elapsed > 0 else 0.0
    print(f"[TX] Sent {total_bytes/1e9:.2f} GB in {elapsed:.2f}s → {gbps:.2f} Gbps")

if __name__ == "__main__":
    asyncio.run(main())
