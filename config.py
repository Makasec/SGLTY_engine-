"""
config.py — Singularity Engine Core Configuration
"""

# Target file to send
TEST_FILE = "thorn_massive.log"

# Network / Ports
SEND_PORTS = [9001, 9002, 9003, 9004, 9005, 9006]
RECV_PORT  = [9001, 9002, 9003, 9004, 9005, 9006]
HOST_IP    = "127.0.0.1"

# Sharding Parameters
SHARD_SIZE_BYTES  = 4 * 1024 * 1024     # 4 MiB per shard
HEADER_SIZE_BYTES = 64                  # Fixed header size from shrdng_snglrty.py
FRAME_LEN_BYTES   = 4                   # Optional framing length (legacy streams)

# Sender batching / flow control
DRAIN_BATCH_BYTES = 16 * 1024 * 1024    # Flush every 16 MiB per lane

# Identifiers
MAGIC_TAG = "SLGTY"
VERSION    = 1

RECEIVER_WRITE_TO_DISK = False
OUTPUT_PATH = "thorn_recv_test.bin"

SO_SNDBUF = 8 * 1024 * 1024
SO_RCVBUF = 8 * 1024 * 1024

