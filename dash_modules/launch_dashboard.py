import os
import sys
import subprocess
import socket
import time
import threading

# ========== CONFIG ==========
DASHBOARD_FILE = os.path.join(os.path.dirname(__file__), "dash_app.py")
URL_FILE       = os.path.join(os.getcwd(), "ngrok_url.txt")
CF_BINARY      = os.path.join(os.getcwd(), "cloudflared.exe")  # Path to your Cloudflared binary
START_PORT     = 8501
MAX_PORT_TRIES = 20
READ_TIMEOUT   = 30  # seconds to wait for URL


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


def read_output(proc, url_file):
    """Read process output in a separate thread and look for URLs."""
    public_url = None
    start_time = time.time()
    
    while time.time() - start_time < READ_TIMEOUT:
        line = proc.stdout.readline().strip()
        if not line:
            time.sleep(0.1)
            continue
            
        # Uncomment for debugging
        # print(f"DEBUG: {line}")
        
        if "trycloudflare.com" in line:
            for part in line.split():
                if part.startswith("https://") and "trycloudflare.com" in part:
                    public_url = part
                    try:
                        with open(url_file, "w") as f:
                            f.write(public_url)
                        print(f"✅ Dashboard is live: {public_url}")
                        return
                    except Exception as e:
                        print(f"⚠ Could not write URL to {url_file}: {e}")
                    break
    
    if not public_url:
        print("❌ Failed to get public URL from Cloudflared within timeout.")


def main():
    # Touch URL file
    try:
        open(URL_FILE, 'a').close()
    except Exception as e:
        print(f"⚠ Could not create URL file {URL_FILE}: {e}")

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
    print(f" Starting Streamlit on http://localhost:{port} ...", flush=True)
    try:
        streamlit_proc = subprocess.Popen(
            streamlit_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    except Exception as e:
        print(f"❌ Failed to start Streamlit: {e}")
        sys.exit(1)

    time.sleep(3)  # allow Streamlit to initialize

    # 2) Launch Cloudflared tunnel
    if not os.path.isfile(CF_BINARY):
        print(f"❌ Cloudflared binary not found at {CF_BINARY}")
        sys.exit(1)

    cf_cmd = [CF_BINARY, "tunnel", "--url", f"http://localhost:{port}"]
    print(f"Starting Cloudflared tunnel to localhost:{port} ...", flush=True)
    try:
        proc = subprocess.Popen(
            cf_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    except Exception as e:
        print(f"❌ Failed to start Cloudflared: {e}")
        streamlit_proc.kill()
        sys.exit(1)

    # 3) Read tunnel output in a separate thread
    output_thread = threading.Thread(target=read_output, args=(proc, URL_FILE))
    output_thread.daemon = True
    output_thread.start()
    
    # 4) Keep main thread alive
    try:
        while True:
            # Check if cloudflared is still running
            if proc.poll() is not None:
                print("❌ Cloudflared tunnel stopped unexpectedly")
                break
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n Shutting down tunnel.")
    finally:
        # Cleanup
        if proc and proc.poll() is None:
            proc.terminate()
        if streamlit_proc and streamlit_proc.poll() is None:
            streamlit_proc.terminate()
            
    sys.exit(0)


if __name__ == "__main__":
    main()