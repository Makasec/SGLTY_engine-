"""
bench_matrix.py
---------------
Automated parameter sweep for Project Singularity.
Runs benchmark_runner.py with different shard/batch combos and logs summary CSV.
"""

import subprocess, time, csv, os
from pathlib import Path

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.py"
RUNNER = BASE_DIR / "benchmark_runner.py"
LOG_FILE = BASE_DIR / "benchmark_log.txt"
RESULTS_CSV = BASE_DIR / "bench_results.csv"

# Define test matrix (MiB values)
SHARD_SIZES_MB = [1, 2, 4, 8]
DRAIN_BATCHES_MB = [8, 16, 32]

def update_config(shard_mb: int, drain_mb: int):
    """Patch config.py with new values."""
    lines = CONFIG_FILE.read_text().splitlines()
    new_lines = []
    for line in lines:
        if line.startswith("SHARD_SIZE_BYTES"):
            new_lines.append(f"SHARD_SIZE_BYTES = {shard_mb} * 1024 * 1024")
        elif line.startswith("DRAIN_BATCH_BYTES"):
            new_lines.append(f"DRAIN_BATCH_BYTES = {drain_mb} * 1024 * 1024")
        else:
            new_lines.append(line)
    CONFIG_FILE.write_text("\n".join(new_lines))

def get_last_log_entry():
    """Return last non-header line from benchmark_log.txt."""
    if not LOG_FILE.exists():
        return None
    lines = [l.strip() for l in LOG_FILE.read_text().splitlines() if l.strip()]
    if len(lines) <= 1:
        return None
    return lines[-1]  # last entry

def run_single_test(shard_mb: int, drain_mb: int):
    update_config(shard_mb, drain_mb)
    print(f"\n=== Running: {shard_mb} MiB shards / {drain_mb} MiB drain ===")
    start = time.time()
    subprocess.run(["python", str(RUNNER)], check=True)
    elapsed = time.time() - start
    last = get_last_log_entry()
    print(f"[DONE] {last}")
    return {
        "shard_mb": shard_mb,
        "drain_mb": drain_mb,
        "elapsed_s": round(elapsed, 2),
        "log_entry": last,
    }

def main():
    results = []
    for shard_mb in SHARD_SIZES_MB:
        for drain_mb in DRAIN_BATCHES_MB:
            res = run_single_test(shard_mb, drain_mb)
            results.append(res)
            # small cooldown between runs
            time.sleep(3)

    # write summary CSV
    with open(RESULTS_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Shard (MiB)", "Drain (MiB)", "Elapsed (s)", "Log Entry"])
        for r in results:
            writer.writerow([r["shard_mb"], r["drain_mb"], r["elapsed_s"], r["log_entry"]])

    print(f"\n✅ Completed {len(results)} tests. Results saved to {RESULTS_CSV}")

if __name__ == "__main__":
    main()
