#!/usr/bin/env python3
"""
watchdog_adaptive_json.py
=========================
Adaptive watchdog for Project Singularity with minimal overhead.
Outputs newline-delimited JSON ("metrics.jsonl") instead of CSV.
Runs as its own process to isolate timing and CPU contention.
"""

import subprocess, time, psutil, shlex, signal, json, os

# --- CONFIG -----------------------------------------------------
RECEIVER_CMD = "python snglty_recv.py"
SENDER_CMD   = "python sndr_snglty.py"
INTERVAL     = 1.0
OUTFILE      = "metrics.jsonl"
CPU_THRESHOLD = 80.0
MEM_THRESHOLD = 90.0
DEEP_DURATION = 5
FLUSH_EVERY  = 10   # write to disk every N samples
# ---------------------------------------------------------------

def _popen(cmd):
    return subprocess.Popen(
        shlex.split(cmd),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,  # prevents ctrl+c from killing children
    )

def _proc_stats(proc: psutil.Process):
    try:
        cpu = proc.cpu_percent(None)
        mem = proc.memory_info().rss
        io = proc.io_counters() if hasattr(proc, "io_counters") else None
        return cpu, mem, getattr(io, "read_bytes", 0), getattr(io, "write_bytes", 0)
    except Exception:
        return 0.0, 0, 0, 0

def _sys_deep_metrics():
    try:
        disk = psutil.disk_io_counters()
        net = psutil.net_io_counters()
        return {
            "sys_disk_r": getattr(disk, "read_bytes", 0),
            "sys_disk_w": getattr(disk, "write_bytes", 0),
            "sys_net_tx": getattr(net, "bytes_sent", 0),
            "sys_net_rx": getattr(net, "bytes_recv", 0),
        }
    except Exception:
        return {}

def main():
    print("[WD] Launching receiver subprocess...")
    rx_p = _popen(RECEIVER_CMD)
    rx = psutil.Process(rx_p.pid)
    time.sleep(2)

    print("[WD] Launching sender subprocess...")
    tx_p = _popen(SENDER_CMD)
    tx = psutil.Process(tx_p.pid)
    time.sleep(0.5)

    rx.cpu_percent(None)
    tx.cpu_percent(None)

    deep_mode_until = 0
    t0 = time.perf_counter()
    buffer = []

    print("[WD] Adaptive JSON watchdog active — output →", OUTFILE)

    try:
        with open(OUTFILE, "w") as f:
            while tx_p.poll() is None:
                elapsed = round(time.perf_counter() - t0, 2)
                sys_cpu = psutil.cpu_percent(None)
                sys_mem = psutil.virtual_memory().percent
                rx_cpu, rx_mem, rx_r, rx_w = _proc_stats(rx)
                tx_cpu, tx_mem, tx_r, tx_w = _proc_stats(tx)

                row = {
                    "t": elapsed,
                    "sys": {"cpu": sys_cpu, "mem": sys_mem},
                    "rx": {"cpu": rx_cpu, "mem": rx_mem, "r": rx_r, "w": rx_w},
                    "tx": {"cpu": tx_cpu, "mem": tx_mem, "r": tx_r, "w": tx_w},
                    "mode": "LIGHT"
                }

                if sys_cpu > CPU_THRESHOLD or sys_mem > MEM_THRESHOLD:
                    deep_mode_until = time.perf_counter() + DEEP_DURATION

                if time.perf_counter() < deep_mode_until:
                    row.update(_sys_deep_metrics())
                    row["mode"] = "DEEP"

                buffer.append(row)
                if len(buffer) >= FLUSH_EVERY:
                    f.write("\n".join(json.dumps(b) for b in buffer) + "\n")
                    f.flush()
                    buffer.clear()

                time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print("[WD] Interrupted by user.")
    finally:
        if buffer:
            with open(OUTFILE, "a") as f:
                f.write("\n".join(json.dumps(b) for b in buffer) + "\n")

        if rx_p.poll() is None:
            rx_p.send_signal(signal.SIGTERM)
        print("[WD] Done. Metrics saved →", os.path.abspath(OUTFILE))

if __name__ == "__main__":
    main()
