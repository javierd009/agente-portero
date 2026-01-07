#!/usr/bin/env python3
"""
Development server with auto-port detection (8000-8006)
"""
import socket
import uvicorn

def is_port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False

def find_available_port(start: int = 8000, end: int = 8006) -> int:
    for port in range(start, end + 1):
        if is_port_available(port):
            return port
    raise RuntimeError(f"No available ports in range {start}-{end}")

if __name__ == "__main__":
    port = find_available_port()
    print(f"🚀 Starting server on port {port}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
