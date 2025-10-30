# config.py — central knobs

HOST = "127.0.0.1"
PORTS = [9001, 9002, 9003, 9004, 9005, 9006]

# Shard / framing
SHARD_SIZE_BYTES = 4 * 1024 * 1024
FRAME_LEN_BYTES  = 4                      # uint32 BE length prefix

# Sender batching
DRAIN_BATCH_BYTES = 16 * 1024 * 1024

# Files
FILE_PATH   = "thorn_massive.log"        # input to send
OUTPUT_PATH = "thorn_recv_test.bin"      # optional receiver sink

# Receiver behavior
RECEIVER_WRITE_TO_DISK = False           # True to write, False to count only

# Event loop
USE_UVLOOP = True

# Socket buffers (kernel)
SO_SNDBUF = 4 * 1024 * 1024
SO_RCVBUF = 4 * 1024 * 1024