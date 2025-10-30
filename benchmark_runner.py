"""
Benchmark Runner for Project Singularity
----------------------------------------
- Launches receiver and waits for [RX_READY]
- Runs sender with output redirected to logs
- Prints total duration
- Logs duration, CPU, RAM, total size, and throughput (Gbps)
- Auto-creates benchmark_log.txt with header if missing
- Cleans up receiver safely
"""

import subprocess, time, sys, psutil, datetime, os
from pathlib import Path

# --- File paths ---
RECEIVER = Path(__file__).parent / "snglty_recv.py"
SENDER   = Path(__file__).parent / "sndr_snglty.py"
FILE_PATH = Path(__file__).parent / "thorn_massive.log"
LOG_PATH  = Path(__file__).parent / "benchmark_log.txt"

def ensure_log_header():
    """Create log file with header if it doesn't exist."""
    if not LOG_PATH.exists() or os.stat(LOG_PATH).st_size == 0:
        with open(LOG_PATH, "w") as log:
            log.write("Timestamp | Duration | CPU | RAM | FileSize | Throughput\n")

def run_benchmark():
    print("[RUNNER] Launching receiver...")

    rx_log = open("receiver_stdout.log", "w")
    rx = subprocess.Popen(
        [sys.executable, str(RECEIVER)],
        stdout=subprocess.PIPE,           # watch for [RX_READY]
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # --- Wait for explicit [RX_READY] signal ---
    ready = False
    while True:
        line = rx.stdout.readline()
        if not line:
            break  # receiver died early
        rx_log.write(line)
        rx_log.flush()
        if "[RX_READY]" in line:
            ready = True
            break

    if not ready:
        print("[RUNNER] Receiver failed to signal readiness. See receiver_stdout.log")
        try:
            rx.terminate()
        except Exception:
            pass
        return

    print("[RUNNER] Launching sender...")
    t0 = time.perf_counter()
    with open("sender_stdout.log", "w") as tx_log:
        subprocess.run(
            [sys.executable, str(SENDER)],
            stdout=tx_log,
            stderr=subprocess.STDOUT,
            check=True,
        )
    t1 = time.perf_counter()

    elapsed = t1 - t0
    print(f"\n[RESULT] Duration: {elapsed:.2f}s")

    # ---- Compute stats ----
    file_size = os.path.getsize(FILE_PATH)
    gb_total = file_size / 1e9
    gbps = (file_size * 8 / 1e9) / elapsed if elapsed > 0 else 0

    proc = psutil.Process()
    mem_mb = proc.memory_info().rss / 1_048_576  # MB
    cpu_pct = psutil.cpu_percent(interval=None)  # instantaneous
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ---- Ensure header exists ----
    ensure_log_header()

    # ---- Append new line ----
    with open(LOG_PATH, "a") as log:
        log.write(
            f"{timestamp} | {elapsed:.2f}s | {cpu_pct:.1f}% | {mem_mb:.1f} MB | "
            f"{gb_total:.2f} GB | {gbps:.2f} Gbps\n"
        )

    # ---- Cleanup receiver ----
    try:
        rx.terminate()
        rx.wait(timeout=3)
    except Exception:
        try:
            rx.kill()
        except Exception:
            pass
    finally:
        rx_log.close()

if __name__ == "__main__":
    run_benchmark()
