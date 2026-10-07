"""Run the API server.

Usage: uv run python scripts/serve.py [--port PORT] [--host HOST] [--reload] [--share]
Port precedence: --port, then the APP_PORT env var, then 8642.
"""

import argparse
import os
import socket
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PORT = 8642


def _lan_ipv4_addresses() -> list[str]:
    """Collect plausible LAN IPv4 addresses without extra dependencies."""
    addrs: set[str] = set()
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        addrs.add(probe.getsockname()[0])
        probe.close()
    except OSError:
        pass

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith("127."):
                addrs.add(ip)
    except OSError:
        pass

    # Per-interface getaddrinfo can hang for minutes on Windows.
    if sys.platform != "win32":
        try:
            for _index, name in socket.if_nameindex():
                try:
                    for info in socket.getaddrinfo(name, None, socket.AF_INET):
                        ip = info[4][0]
                        if not ip.startswith("127."):
                            addrs.add(ip)
                except OSError:
                    continue
        except (AttributeError, OSError):
            pass

    return sorted(addrs)


def _print_share_banner(host: str, port: int) -> None:
    localhost = f"http://127.0.0.1:{port}/app"
    print(f"\n  Lokalt (Erik):     {localhost}")
    lan_ips = _lan_ipv4_addresses()
    if lan_ips:
        for ip in lan_ips:
            print(f"  LAN:               http://{ip}:{port}/app")
        example = lan_ips[0]
        print(f"\n  Jenny på samma Wi‑Fi: öppna http://{example}:{port}/app")
    else:
        print("\n  Jenny på samma Wi‑Fi: öppna http://<din-PCs-IP>:{port}/app".format(port=port))

    token = os.environ.get("APP_SHARE_TOKEN") or os.environ.get("SHARE_TOKEN")
    if token:
        print("  (Med token: lägg till ?token=... i länken eller sätt X-Share-Token.)")

    print(
        "\n  Windows-brandvägg: tillåt Python/uvicorn på port "
        f"{port} för privata nätverk om Jenny inte når sidan.\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=int(os.environ.get("APP_PORT", DEFAULT_PORT)))
    parser.add_argument("--host", default=os.environ.get("APP_HOST", "127.0.0.1"))
    parser.add_argument("--reload", action="store_true", help="Restart on code changes")
    parser.add_argument(
        "--share",
        action="store_true",
        help="Listen on all interfaces (0.0.0.0) and print LAN URLs for Jenny",
    )
    args = parser.parse_args()

    if args.share:
        args.host = "0.0.0.0"
        os.environ["APP_SHARE_MODE"] = "1"

    sys.path.insert(0, str(ROOT))

    if args.share:
        _print_share_banner(args.host, args.port)

    print(f"Startar server på {args.host}:{args.port} …")
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload, app_dir=str(ROOT))


if __name__ == "__main__":
    main()
