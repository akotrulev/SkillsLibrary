#!/usr/bin/env python3
"""
Start one or more servers, wait for their ports to accept connections, run a command, then stop the servers.

Each server's stdout and stderr go to evidence/servers/server-<n>.log under the current directory, so a busy
server never blocks on a full pipe and its output is there to read when the command fails.

Usage:
    Single server:
    python scripts/with_server.py --server "npm run dev" --port 5173 -- python automation.py

    Multiple servers:
    python scripts/with_server.py \
      --server "cd backend && python server.py" --port 3000 \
      --server "cd frontend && npm run dev" --port 5173 \
      -- python test.py
"""

import argparse
import socket
import subprocess
import sys
import time
from pathlib import Path

LOG_DIR = Path("evidence") / "servers"
PORT_POLL_SECONDS = 0.5


def is_server_ready(port, timeout=30):
    """Return True once localhost:<port> accepts a connection, False when the timeout passes first."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("localhost", port), timeout=1):
                return True
        except OSError:
            time.sleep(PORT_POLL_SECONDS)
    return False


def stop(process):
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def main():
    parser = argparse.ArgumentParser(description="Run command with one or more servers")
    parser.add_argument("--server", action="append", dest="servers", required=True, help="Server command (can be repeated)")
    parser.add_argument("--port", action="append", dest="ports", type=int, required=True, help="Port for each server (must match --server count)")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds per server (default: 30)")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run after server(s) ready")
    args = parser.parse_args()

    command = args.command[1:] if args.command and args.command[0] == "--" else args.command
    if not command:
        print("Error: No command specified to run")
        sys.exit(1)
    if len(args.servers) != len(args.ports):
        print("Error: Number of --server and --port arguments must match")
        sys.exit(1)

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    processes = []
    try:
        for number, (server, port) in enumerate(zip(args.servers, args.ports), start=1):
            log_path = LOG_DIR / f"server-{number}.log"
            print(f"Starting server {number}/{len(args.servers)}: {server} (log: {log_path})")
            with log_path.open("w") as log:
                processes.append(subprocess.Popen(server, shell=True, stdout=log, stderr=subprocess.STDOUT))
            print(f"Waiting for server on port {port}...")
            if not is_server_ready(port, timeout=args.timeout):
                raise RuntimeError(f"Server failed to start on port {port} within {args.timeout}s; see {log_path}")
            print(f"Server ready on port {port}")

        print(f"\nAll {len(args.servers)} server(s) ready")
        print(f"Running: {' '.join(command)}\n")
        sys.exit(subprocess.run(command).returncode)
    finally:
        print(f"\nStopping {len(processes)} server(s)...")
        for number, process in enumerate(processes, start=1):
            stop(process)
            print(f"Server {number} stopped")
        print("All servers stopped")


if __name__ == "__main__":
    main()
