"""
snglty_recv.py — Header-aware multi-lane receiver
for Project Singularity.
"""

import asyncio
import struct
import sys
from typing import Dict, Set, Tuple
from utils_net import tune_socket
from shrdng_snglrty import unpack_header, HEADER_SIZE
import config

LEN_FMT = "!I"  # uint32 big-endian frame prefix
LEN_SIZE = struct.calcsize(LEN_FMT)

total_bytes = 0
active_clients: Set[asyncio.Task] = set()

# Optional in-memory session tracker
sessions: Dict[int, Dict[int, bytes]] = {}


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """Handle one TCP connection and extract [HEADER][DATA] frames."""
    global total_bytes

    sock = writer.get_extra_info("socket")
    if sock:
        tune_socket(sock, getattr(config, "SO_SNDBUF", 0), getattr(config, "SO_RCVBUF", 0))

    f = None
    if getattr(config, "RECEIVER_WRITE_TO_DISK", False):
        f = await asyncio.to_thread(open, config.OUTPUT_PATH, "ab", buffering=0)

    try:
        while True:
            # Frame prefix
            hdr_bytes = await reader.readexactly(LEN_SIZE)
            (frame_len,) = struct.unpack(LEN_FMT, hdr_bytes)
            if frame_len == 0:
                break  # graceful end-of-stream

            packet = await reader.readexactly(frame_len)

            if len(packet) < HEADER_SIZE:
                print("[RX] Warning: truncated packet")
                continue

            header = unpack_header(packet[:HEADER_SIZE])
            payload = packet[HEADER_SIZE:]
            total_bytes += len(payload)

            # Optional disk write
            if f:
                await asyncio.to_thread(f.write, payload)

            # Track per-session shards (for debugging or future reassembly)
            sid = header["session_id"]
            if sid not in sessions:
                sessions[sid] = {}
            sessions[sid][header["shard_index"]] = payload

    except asyncio.IncompleteReadError:
        pass  # client closed early
    finally:
        if f:
            await asyncio.to_thread(f.close)
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def start_servers():
    servers = []
    for port in config.SEND_PORTS:
        srv = await asyncio.start_server(handle_client, host=config.HOST_IP, port=port, reuse_port=False)
        servers.append(srv)
        for sock in srv.sockets or []:
            tune_socket(sock, getattr(config, "SO_SNDBUF", 0), getattr(config, "SO_RCVBUF", 0))
        print(f"[RX] Listening on {config.HOST_IP}:{port}", flush=True)

    print("[RX_READY]", flush=True)

    async with asyncio.TaskGroup() as tg:
        for srv in servers:
            tg.create_task(srv.serve_forever())


def main():
    if getattr(config, "USE_UVLOOP", False):
        try:
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        except Exception:
            pass

    try:
        asyncio.run(start_servers())
    except KeyboardInterrupt:
        pass
    finally:
        print(f"[RX] Total received: {total_bytes/1e9:.2f} GB", flush=True)


if __name__ == "__main__":
    main()
