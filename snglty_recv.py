"""
Receiver with:
- Multiple listening ports
- Readiness signal [RX_READY] after all binds succeed
- Length-prefixed frames (uint32 BE) per shard
- Optional disk writing (off by default for clean throughput)
- Socket tuning and graceful shutdown
"""
import asyncio, struct, sys, os
from typing import Dict, Set
from utils_net import tune_socket
import config

LEN_FMT = "!I"  # uint32 big-endian
LEN_SIZE = struct.calcsize(LEN_FMT)

total_bytes = 0
active_clients: Set[asyncio.Task] = set()

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    global total_bytes
    sock = writer.get_extra_info("socket")
    if sock:
        tune_socket(sock, config.SO_SNDBUF, config.SO_RCVBUF)

    # Optional disk sink (single file append; not reconstructing original order)
    f = None
    if config.RECEIVER_WRITE_TO_DISK:
        f = await asyncio.to_thread(open, config.OUTPUT_PATH, "ab", buffering=0)

    try:
        while True:
            hdr = await reader.readexactly(LEN_SIZE)
            (nbytes,) = struct.unpack(LEN_FMT, hdr)
            if nbytes == 0:
                # graceful end-of-stream frame
                break
            data = await reader.readexactly(nbytes)

            # Fast path: count only
            if not config.RECEIVER_WRITE_TO_DISK:
                total_bytes += nbytes
            else:
                # Write via thread to avoid blocking loop
                await asyncio.to_thread(f.write, data)
                total_bytes += nbytes
    except asyncio.IncompleteReadError:
        # client closed mid-frame; treat as disconnect
        pass
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
    # Bind all ports first; if any fails, exit early
    for port in config.PORTS:
        srv = await asyncio.start_server(handle_client, host=config.HOST, port=port, reuse_port=False)
        servers.append(srv)
        for sock in srv.sockets or []:
            tune_socket(sock, config.SO_SNDBUF, config.SO_RCVBUF)
        print(f"[RX] Listening on {config.HOST}:{port}", flush=True)

    # Readiness signal after all ports are listening
    print("[RX_READY]", flush=True)

    async with asyncio.TaskGroup() as tg:
        for srv in servers:
            tg.create_task(srv.serve_forever())

def main():
    if config.USE_UVLOOP:
        try:
            import uvloop, asyncio as _a
            _a.set_event_loop_policy(uvloop.EventLoopPolicy())
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
