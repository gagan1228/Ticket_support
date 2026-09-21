"""
Single-command launcher — starts the FastAPI backend and Streamlit UI together.
Usage: python start.py
"""

import subprocess
import sys
import os
import time
import signal


def main():
    env = os.environ.copy()

    print("Starting FastAPI backend on http://localhost:8000 ...")
    api_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
        env=env,
    )

    # give the API a second to bind before streamlit tries to call it
    time.sleep(2)

    print("Starting Streamlit UI on http://localhost:8501 ...")
    ui_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", "8501"],
        env=env,
    )

    print("\nBoth services running. Press Ctrl+C to stop.\n")

    def shutdown(sig, frame):
        print("\nShutting down...")
        api_proc.terminate()
        ui_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    api_proc.wait()


if __name__ == "__main__":
    main()
