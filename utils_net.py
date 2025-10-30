# utils_net.py — tiny socket helpers
import socket

def tune_socket(sock, sndbuf: int, rcvbuf: int):
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, sndbuf)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, rcvbuf)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    except Exception:
        # Tuning is best-effort; do not crash if a platform refuses it.
        pass
