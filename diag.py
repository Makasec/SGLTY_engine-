import psutil
import socket
import time
import os
import subprocess

print("\n=== Singularity Diagnostic ===")

# 1. Check for bound receiver ports
print("\n[1] Active TCP listeners on localhost 9000–9010:")
subprocess.run("sudo lsof -i :9000-9010 | grep LISTEN || echo 'none'", shell=True)

# 2. CPU + memory snapshot
print("\n[2] System CPU & memory load:")
print(f"CPU: {psutil.cpu_percent(interval=1):.1f}%  |  RAM used: {psutil.virtual_memory().percent:.1f}%")

# 3. Python processes related to Singularity
print("\n[3] Python processes related to Singularity:")
for p in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if 'python' in p.name() and any('snglty' in s for s in p.info['cmdline']):
            cpu = p.cpu_percent(interval=0.1)
            mem = p.memory_info().rss / 1_048_576
            print(f"PID {p.pid:>7}  CPU {cpu:>4.1f}%  MEM {mem:>6.1f} MB  CMD {' '.join(p.info['cmdline'])}")
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

# 4. Socket buffer test
print("\n[4] Socket buffer test (localhost):")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("127.0.0.1", 0))
s.listen(1)
buf = s.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
print(f"Default SO_SNDBUF: {buf/1024:.1f} KiB")
s.close()

# 5. Loopback throughput sanity check
print("\n[5] Loopback throughput test (1GiB zero-copy)")
t0 = time.perf_counter()
os.system("dd if=/dev/zero of=/dev/null bs=1M count=1024 2>/dev/null")
t1 = time.perf_counter()
print(f"Raw memcpy test (1GiB zero-copy): {(1/(t1-t0)):.2f} GiB/s")

print("\n=== End diagnostics ===\n")
