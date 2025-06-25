#!/usr/bin/env python3
import os
import sys
import subprocess
import socket
import time
import select

# ========== CONFIG ==========
DASHBOARD_FILE = os.path.join(os.path.dirname(__file__), "dash_app.py")
URL_FILE       = os.path.join(os.getcwd(), "ngrok_url.txt")
CF_BINARY      = os.path.join(os.getcwd(), "cloudflared-linux-amd64")  # Path to your Cloudflared binary
START_PORT     = 8501
MAX_PORT_TRIES = 20
READ_TIMEOUT   = 1.0  # seconds for select timeout


def find_free_port(start=START_PORT, tries=MAX_PORT_TRIES):
    """Find an available port on localhost."""
    for port in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue
    return None


def main():
    # Touch URL file
    try:
        open(URL_FILE, 'a').close()
    except Exception as e:
        print(f"⚠️ Could not create URL file {URL_FILE}: {e}")

    port = find_free_port()
    if port is None:
        print("❌ No free port available.")
        sys.exit(1)

    # 1) Launch Streamlit
    if not os.path.isfile(DASHBOARD_FILE):
        print(f"❌ Cannot find dashboard file at {DASHBOARD_FILE}")
        sys.exit(1)

    streamlit_cmd = [
        sys.executable, "-m", "streamlit", "run", DASHBOARD_FILE,
        "--server.address", "0.0.0.0",
        "--server.port", str(port),
        "--server.headless", "true"
    ]
    print(f"🔧 Starting Streamlit on http://localhost:{port} ...", flush=True)
    subprocess.Popen(
        streamlit_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )

    time.sleep(3)  # allow Streamlit to initialize

    # 2) Launch Cloudflared tunnel
    if not os.path.isfile(CF_BINARY):
        print(f"❌ Cloudflared binary not found at {CF_BINARY}")
        sys.exit(1)

    cf_cmd = [CF_BINARY, "tunnel", "--url", f"http://localhost:{port}"]
    print(f"🌐 Starting Cloudflared tunnel to localhost:{port} ...", flush=True)
    proc = subprocess.Popen(
        cf_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True
    )

    # 3) Read tunnel output for public URL using select
    public_url = None
    deadline = time.time() + 30
    while time.time() < deadline and not public_url:
        ready, _, _ = select.select([proc.stdout], [], [], READ_TIMEOUT)
        if ready:
            line = proc.stdout.readline().strip()
            #print(f"DEBUG: {line}")  # uncomment for debugging
            if "trycloudflare.com" in line and line.startswith("INFO") is False:
                # Attempt to extract URL
                for part in line.split():
                    if part.startswith("https://") and "trycloudflare.com" in part:
                        public_url = part
                        break

    if public_url:
        try:
            with open(URL_FILE, "w") as f:
                f.write(public_url)
        except Exception as e:
            print(f"⚠️ Could not write URL to {URL_FILE}: {e}")
        print(f"✅ Dashboard is live: {public_url}")
        # Keep running to maintain tunnel
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("🛑 Shutting down tunnel.")
            sys.exit(0)
    else:
        print("❌ Failed to get public URL from Cloudflared within timeout.")
        proc.terminate()
        sys.exit(1)

if __name__ == "__main__":
    main()
