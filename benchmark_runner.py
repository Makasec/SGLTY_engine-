"""
Benchmark Runner for Project Singularity
----------------------------------------
- Launches receiver, waits for [RX_READY]
- Launches sender, captures duration
- Measures CPU and RAM deltas across run
- Logs size, throughput, and system metrics to benchmark_log.txt
- Graceful receiver shutdown
"""

import subprocess, time, sys, psutil, datetime, os, signal
from pathlib import Path

# --- Paths ---
BASE_DIR  = Path(__file__).parent
RECEIVER  = BASE_DIR / "snglty_recv.py"
SENDER    = BASE_DIR / "sndr_snglty.py"
FILE_PATH = BASE_DIR / "thorn_massive.log"
LOG_PATH  = BASE_DIR / "benchmark_log.txt"

# --- Helpers ---
def ensure_log_header():
    """Create log file with header if missing."""
    if not LOG_PATH.exists() or LOG_PATH.stat().st_size == 0:
        with open(LOG_PATH, "w") as f:
            f.write("Timestamp | Duration | CPU Δ | RAM Δ | FileSize | Throughput\n")


def run_benchmark():
    print("[RUNNER] Launching receiver...")

    rx_log = open("receiver_stdout.log", "w")
    rx = subprocess.Popen(
        [sys.executable, str(RECEIVER)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # --- Wait for readiness ---
    ready = False
    while True:
        line = rx.stdout.readline()
        if not line:
            break
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

    # --- System metrics before ---
    proc = psutil.Process()
    cpu_before = psutil.cpu_percent(interval=None)
    mem_before = proc.memory_info().rss / 1_048_576  # MB

    # --- Run sender ---
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

    # --- System metrics after ---
    cpu_after = psutil.cpu_percent(interval=None)
    mem_after = proc.memory_info().rss / 1_048_576  # MB
    cpu_delta = cpu_after - cpu_before
    mem_delta = mem_after - mem_before

    print(f"[RESULT] Duration: {elapsed:.2f}s")

    # --- File stats ---
    file_size = os.path.getsize(FILE_PATH)
    gb_total = file_size / 1e9
    gbps = (file_size * 8 / 1e9) / elapsed if elapsed > 0 else 0.0

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ensure_log_header()
    with open(LOG_PATH, "a") as log:
        log.write(
            f"{timestamp} | {elapsed:.2f}s | {cpu_delta:.1f}% | {mem_delta:.1f} MB | "
            f"{gb_total:.2f} GB | {gbps:.2f} Gbps\n"
        )

    # --- Cleanup receiver ---
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
