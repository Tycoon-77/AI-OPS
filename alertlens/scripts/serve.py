"""
Dual-stack server runner for macOS and Linux.
Binds :: with IPV6_V6ONLY=0 so both IPv6 (localhost / ::1) and IPv4 (127.0.0.1) work reliably.
"""
import socket
import sys
import uvicorn
from alertlens.api.main import app

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    try:
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        s.bind(("::", port))
        s.listen(128)
        sockets = [s]
        print(f"Dual-stack server listening on http://localhost:{port} and http://127.0.0.1:{port}")
    except Exception as e:
        print(f"Fallback to standard host 0.0.0.0: {e}")
        sockets = None

    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    if sockets:
        server.run(sockets=sockets)
    else:
        server.run()

if __name__ == "__main__":
    main()
