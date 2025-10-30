# Singularity Engine

A high-speed, sharded data transfer engine designed by **Maka Security Solutions** for rapid, reliable file replication and log movement between distributed systems.

---

##  Overview
**Singularity Engine** breaks large files into shards, transmits them concurrently across multiple TCP lanes, and reassembles them on the receiver side with full integrity verification.  
The system is designed for **speed first**, with architecture choices that allow for reordering, fault recovery, and encryption integration later.

- Handles 10+ GB transfers in ~33 seconds (~2.5 Gbps local throughput)
- Shards files for parallel transport
- Uses efficient batching and drain control for optimized I/O
- Employs `xxhash` for fast, lightweight integrity checks
- Designed for containerized and real-world (WAN) deployment

---

##  Architecture

File → Shard → Multi-port Sender → Receiver (Reassembly + Integrity Check)


### Key Components
| File | Purpose |
|------|----------|
| `sndr_snglty.py` | Splits files into shards and sends them concurrently |
| `snglty_recv.py` | Receives shards, verifies hashes, and reassembles the original file |
| `shrdng_snglrty.py` | Core sharding and reassembly logic |
| `benchmark_runner.py` | Launches sender/receiver, measures total duration |
| `benchmark_log.txt` | Historical performance log |
| `config.py` | Shard and batching configuration |
| `utils_net.py` | Utility network functions |
| `watchdog.py` | System metrics tracking |

---

## 📊 Performance
| Test File | Size | Duration | Throughput |
|------------|-------|-----------|-------------|
| `thorn_massive.log` | 10.74 GB | 33.8 s | **≈ 2.5 Gbps** |

The engine has achieved sustained multi-gigabit throughput under Python 3.13 using asyncio and concurrent TCP ports.  
It is currently being adapted for container and cloud environments for real-world testing.

---

##  Next Steps
- Add SGLTY v0 headers for session and shard metadata  
- Implement out-of-order reassembly via byte offsets  
- Introduce resumable sessions and selective retransmit logic  
- Add encryption (AES-GCM or ChaCha20)  
- Build QUIC-compatible transport layer for WAN optimization

---

## Requirements
Python 3.11+
