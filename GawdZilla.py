#!/usr/bin/env python3
"""
GawdZilla v1.0 — Parental Control & Family Device Management
Launcher / Control Console
Created by MiSFiT SeCuRiTY
"""

import os
import sys
import time
import signal
import shutil
import subprocess
import threading
import webbrowser
from pathlib import Path

# ──────────────────────────────────────────────────────────────
#  Paths & constants
# ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

HOST = "0.0.0.0"
PORT = 7777
ADMIN_URL = f"http://127.0.0.1:{PORT}/admin"

# ──────────────────────────────────────────────────────────────
#  ANSI colors
# ──────────────────────────────────────────────────────────────
CYAN   = "\033[96m"
PINK   = "\033[95m"
YEL    = "\033[93m"
GREEN  = "\033[92m"
RED    = "\033[91m"
DIM    = "\033[2m"
BOLD   = "\033[1m"
RST    = "\033[0m"

# ──────────────────────────────────────────────────────────────
#  ASCII art (your provided art)
# ──────────────────────────────────────────────────────────────
ASCII = r"""
⠀⠀⠀⠀⠀⠀⠀⣰⠀⠀⠀⠀⠀⠀⣠⠀⡄⡴⠁⠀⢀⠀⣠⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⣀⣾⠏⠀⢀⣤⣴⣧⣾⣿⣸⣿⡿⢠⣷⣿⣿⡁⠀⠀⠀⡀⠀⠀⢀⠀
⠀⠀⠀⢠⣷⣿⠃⢀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⢁⣴⣠⣾⣤⣴⠾⠁⠀
⠀⠀⣬⣿⡿⠁⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡥⠄⠀⠀
⠀⣦⣿⣿⠃⠀⠸⣿⣿⢻⡿⠛⠛⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠀⠀⠀⠀⠀
⢤⣿⣿⣿⠀⠀⠀⠿⠟⠸⠇⠀⠀⠀⠹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣾⣷⣶⣂⣀
⢸⣿⣿⡇⠀⠀⠀⠀⠀⠀⠀⣀⣀⣠⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⠏⠉
⣾⣿⣿⣿⠀⠀⠀⠀⠀⠀⢀⢼⣿⡿⠛⠉⠉⣿⣿⣿⣿⣿⣿⣿⣿⣿⣏⡉⠀⠀⠀
⣼⣿⣿⣿⡀⠀⠀⠀⠀⠀⠈⠘⠙⠁⠀⢀⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⣖⠀⠀
⠸⢿⣿⣿⣷⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠙⠋⠉⠁⠀
⠐⠻⣿⣿⣿⣿⣧⣄⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣗⠀⠀⠀⠀
⠀⠀⢉⣿⣿⣿⣿⣿⣿⣶⣦⣤⣤⣶⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣇⠈⠉⠀⠀⠀⠀
⠀⠀⠀⠈⠉⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠻⠿⡇⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠉⠻⠿⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠻⠻⡏⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⠉⠃⢘⠟⠋⠈⢙⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
"""

BANNER = r"""
   ██████╗  █████╗ ██╗    ██╗██████╗ ███████╗██╗██╗     ██╗      █████╗
  ██╔════╝ ██╔══██╗██║    ██║██╔══██╗╚══███╔╝██║██║     ██║     ██╔══██╗
  ██║  ███╗███████║██║ █╗ ██║██║  ██║  ███╔╝ ██║██║     ██║     ███████║
  ██║   ██║██╔══██║██║███╗██║██║  ██║ ███╔╝  ██║██║     ██║     ██╔══██║
  ╚██████╔╝██║  ██║╚███╔███╔╝██████╔╝███████╗██║███████╗███████╗██║  ██║
   ╚═════╝ ╚═╝  ╚═╝ ╚══╝╚══╝ ╚═════╝ ╚══════╝╚═╝╚══════╝╚══════╝╚═╝  ╚═╝
"""

# ──────────────────────────────────────────────────────────────
#  Runtime state
# ──────────────────────────────────────────────────────────────
server_proc = None
tunnel_proc = None
tunnel_url = None
started_at = None


# ──────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────
def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_banner():
    clear_screen()
    print(f"{CYAN}{ASCII}{RST}")
    print(f"{PINK}{BANNER}{RST}")
    print(f"   {YEL}Created by MiSFiT SeCuRiTY{RST}   "
          f"{DIM}│{RST}   {CYAN}v1.0.0{RST}   "
          f"{DIM}│{RST}   {YEL}Parental Control Platform{RST}")
    print(f"   {DIM}{'─' * 68}{RST}\n")


def uptime_str():
    if not started_at:
        return "00:00:00"
    s = int(time.time() - started_at)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def status_line():
    if server_proc and server_proc.poll() is None:
        tag = f"{GREEN}● RUNNING{RST}"
        if tunnel_proc and tunnel_proc.poll() is None and tunnel_url:
            tag += f"  {PINK}● TUNNEL {tunnel_url}{RST}"
        elif tunnel_proc and tunnel_proc.poll() is None:
            tag += f"  {YEL}● TUNNEL starting...{RST}"
        tag += f"  {DIM}up {uptime_str()}{RST}"
    else:
        tag = f"{RED}● STOPPED{RST}"
    print(f"   STATUS  {tag}\n")


def print_menu():
    print(f" {YEL}[1]{RST}  Start server  {DIM}(localhost + LAN){RST}")
    print(f" {YEL}[2]{RST}  Start server  {DIM}+ Cloudflare Tunnel (public URL){RST}")
    print(f" {YEL}[3]{RST}  Stop server / disconnect tunnel")
    print(f" {YEL}[4]{RST}  Show status & URLs")
    print(f" {YEL}[5]{RST}  Open admin dashboard in browser")
    print(f" {YEL}[6]{RST}  Exit\n")


# ──────────────────────────────────────────────────────────────
#  Server control
# ──────────────────────────────────────────────────────────────
def _free_port(port: int) -> bool:
    """Check if we can bind the port (i.e. nothing already listening)."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def start_server(with_tunnel=False):
    global server_proc, tunnel_proc, tunnel_url, started_at

    if server_proc and server_proc.poll() is None:
        print(f"\n  {YEL}[!] Server already running (PID {server_proc.pid}).{RST}")
        return

    if not _free_port(PORT):
        print(f"\n  {RED}[!] Port {PORT} is already in use. "
              f"Stop the other process or change PORT in gawdzilla.py.{RST}")
        return

    # Sanity: server package must exist
    if not (ROOT / "server" / "app.py").exists():
        print(f"\n  {RED}[!] server/app.py not found. "
              f"Complete Block 1 files first.{RST}")
        return

    env = os.environ.copy()
    env["GZ_PUBLIC"] = "1" if with_tunnel else "0"
    env["GZ_PORT"] = str(PORT)
    env["PYTHONUNBUFFERED"] = "1"

    log_file = LOG_DIR / "server.log"
    log_handle = open(log_file, "ab", buffering=0)

    print(f"\n  {CYAN}[+] Starting GawdZilla server on port {PORT}...{RST}")
    server_proc = subprocess.Popen(
        [sys.executable, "-m", "server.app"],
        cwd=str(ROOT),
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )
    started_at = time.time()

    # Wait for server to actually come up
    import socket
    up = False
    for _ in range(30):
        time.sleep(0.3)
        if server_proc.poll() is not None:
            print(f"  {RED}[!] Server crashed on startup. Check {log_file}{RST}")
            return
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            if s.connect_ex(("127.0.0.1", PORT)) == 0:
                up = True
                break

    if not up:
        print(f"  {YEL}[!] Server did not respond in time — check {log_file}{RST}")
    else:
        print(f"  {GREEN}[✓] Server up (PID {server_proc.pid}){RST}")
        print(f"      Admin dashboard : {YEL}{ADMIN_URL}{RST}")
        print(f"      Device endpoint : {YEL}http://127.0.0.1:{PORT}/device{RST}")
        print(f"      LAN access      : {YEL}http://<your-lan-ip>:{PORT}/admin{RST}")
        print(f"      Logs            : {DIM}{log_file}{RST}")

    if with_tunnel:
        _start_tunnel()


def _start_tunnel():
    global tunnel_proc, tunnel_url

    if tunnel_proc and tunnel_proc.poll() is None:
        print(f"  {YEL}[!] Tunnel already running.{RST}")
        return

    if shutil.which("cloudflared") is None:
        print(f"\n  {YEL}[!] cloudflared not found in PATH.{RST}")
        print(f"      Install from: {CYAN}https://developers.cloudflare.com/"
              f"cloudflare-one/connections/connect-networks/downloads/{RST}")
        return

    print(f"  {CYAN}[+] Launching Cloudflare quick tunnel...{RST}")
    tunnel_proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://127.0.0.1:{PORT}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    import re
    url_re = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

    def pump():
        global tunnel_url
        for line in tunnel_proc.stdout:
            m = url_re.search(line)
            if m and not tunnel_url:
                tunnel_url = m.group(0)
                print(f"\n  {PINK}{BOLD}[TUNNEL] {tunnel_url}{RST}")
                print(f"  {PINK}         Admin : {tunnel_url}/admin{RST}")
                print(f"  {PINK}         Enroll: {tunnel_url}/enroll{RST}\n")

    threading.Thread(target=pump, daemon=True).start()


def stop_all():
    global server_proc, tunnel_proc, tunnel_url, started_at

    stopped = False

    if tunnel_proc:
        print(f"  {CYAN}[-] Stopping tunnel...{RST}")
        try:
            tunnel_proc.terminate()
            tunnel_proc.wait(timeout=5)
        except Exception:
            try: tunnel_proc.kill()
            except Exception: pass
        tunnel_proc = None
        tunnel_url = None
        stopped = True

    if server_proc:
        print(f"  {CYAN}[-] Stopping server...{RST}")
        try:
            server_proc.terminate()
            server_proc.wait(timeout=5)
        except Exception:
            try: server_proc.kill()
            except Exception: pass
        server_proc = None
        started_at = None
        stopped = True

    if not stopped:
        print(f"  {DIM}Nothing was running.{RST}")
    else:
        print(f"  {GREEN}[✓] All services stopped.{RST}")


def show_status():
    print()
    if server_proc and server_proc.poll() is None:
        print(f"  {GREEN}● Server running{RST}  PID {server_proc.pid}  up {uptime_str()}")
        print(f"      Admin    : {YEL}{ADMIN_URL}{RST}")
        print(f"      Device   : {YEL}http://127.0.0.1:{PORT}/device{RST}")
    else:
        print(f"  {RED}● Server stopped{RST}")

    if tunnel_proc and tunnel_proc.poll() is None:
        if tunnel_url:
            print(f"  {PINK}● Tunnel running{RST}  {tunnel_url}")
            print(f"      Admin    : {PINK}{tunnel_url}/admin{RST}")
            print(f"      Enroll   : {PINK}{tunnel_url}/enroll{RST}")
        else:
            print(f"  {YEL}● Tunnel starting...{RST}")
    else:
        print(f"  {DIM}● Tunnel stopped{RST}")


# ──────────────────────────────────────────────────────────────
#  Main loop
# ──────────────────────────────────────────────────────────────
def main():
    signal.signal(signal.SIGINT, _sig_handler)
    try:
        signal.signal(signal.SIGTERM, _sig_handler)
    except Exception:
        pass

    while True:
        print_banner()
        status_line()
        print_menu()

        try:
            choice = input(f"  {PINK}gawdzilla>{RST} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            stop_all()
            print(f"\n  {YEL}Stay safe. — MiSFiT SeCuRiTY{RST}\n")
            sys.exit(0)

        if choice == "1":
            start_server(with_tunnel=False)
            input(f"\n  {DIM}Press Enter to return to menu...{RST}")

        elif choice == "2":
            start_server(with_tunnel=True)
            input(f"\n  {DIM}Press Enter to return to menu...{RST}")

        elif choice == "3":
            print()
            stop_all()
            input(f"\n  {DIM}Press Enter to return to menu...{RST}")

        elif choice == "4":
            show_status()
            input(f"\n  {DIM}Press Enter to return to menu...{RST}")

        elif choice == "5":
            if server_proc and server_proc.poll() is None:
                webbrowser.open(ADMIN_URL)
                print(f"  {CYAN}[+] Opening {ADMIN_URL}{RST}")
                time.sleep(0.8)
            else:
                print(f"\n  {YEL}[!] Server is not running. Start it first (option 1 or 2).{RST}")
                input(f"\n  {DIM}Press Enter to return to menu...{RST}")

        elif choice == "6":
            print()
            stop_all()
            print(f"\n  {YEL}Stay safe. — MiSFiT SeCuRiTY{RST}\n")
            sys.exit(0)

        else:
            print(f"  {RED}Invalid choice.{RST}")
            time.sleep(0.6)


def _sig_handler(signum, frame):
    print()
    stop_all()
    print(f"\n  {YEL}Stay safe. — MiSFiT SeCuRiTY{RST}\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
