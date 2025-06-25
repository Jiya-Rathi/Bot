import subprocess
import time
from pyngrok import ngrok

DASHBOARD_FILE = "dash_modules/dash_app.py"
DASHBOARD_PORT = 8501
NGROK_AUTH_TOKEN = "2xc8zQdBntPlwfi1ycALdgL7sb3_vQaxgd5Aqi9cwKxjkLzh"  # Replace with your actual token


def kill_existing():
    subprocess.run(["pkill", "-f", "streamlit"], capture_output=True)
    subprocess.run(["pkill", "-f", "ngrok"], capture_output=True)
    print("🧹 Cleaned up old processes")

def launch_streamlit():
    print(f"🚀 Launching Streamlit dashboard on port {DASHBOARD_PORT}")
    return subprocess.Popen([
        "streamlit", "run", DASHBOARD_FILE,
        "--server.address", "0.0.0.0",
        "--server.port", str(DASHBOARD_PORT),
        "--server.headless", "true"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def open_ngrok_tunnel():
    print("🌐 Opening ngrok tunnel...")
    ngrok.kill()  # Kill old tunnels
    public_url = ngrok.connect(DASHBOARD_PORT)
    print(f"\n✅ Dashboard running at: {public_url}")
    return public_url

def main():
    kill_existing()
    streamlit_proc = launch_streamlit()
    time.sleep(4)  # Let Streamlit warm up
    tunnel_url = open_ngrok_tunnel()

    print("\n📈 Open this URL in your browser to access your accounting dashboard:")
    print(f"👉 {tunnel_url}")

    try:
        while True:
            time.sleep(10)
            if streamlit_proc.poll() is not None:
                print("⚠️ Streamlit process exited!")
                break
    except KeyboardInterrupt:
        print("🔻 Shutting down...")
    finally:
        streamlit_proc.terminate()
        ngrok.kill()
        print("🧹 Cleanup complete.")

if __name__ == "__main__":
    main()


