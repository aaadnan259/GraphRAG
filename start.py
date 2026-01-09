
import subprocess
import sys
import os
import time
import shutil
import threading
from pathlib import Path

# Configuration
FRONTEND_DIR = Path("frontend")
BACKEND_PORT = 8000
FRONTEND_PORT = 5173

def log(message: str, type: str = "INFO"):
    print(f"[{type}] {message}")

def check_frontend_setup():
    """Ensure frontend dependencies are installed."""
    if not (FRONTEND_DIR / "node_modules").exists():
        log("node_modules not found. Installing dependencies...", "WARN")
        try:
            subprocess.check_call("npm install", shell=True, cwd=FRONTEND_DIR)
            log("Frontend dependencies installed.", "SUCCESS")
        except subprocess.CalledProcessError:
            log("Failed to install frontend dependencies.", "ERROR")
            sys.exit(1)
    else:
        log("Frontend dependencies found.", "INFO")

def start_backend():
    """Start FastAPI backend using uvicorn."""
    log(f"Starting Backend on port {BACKEND_PORT}...", "INFO")
    # Using reload=True for dev experience
    cmd = [sys.executable, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", str(BACKEND_PORT), "--reload"]
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        log(f"Backend failed: {e}", "ERROR")

def start_frontend():
    """Start Vite frontend."""
    log(f"Starting Frontend on port {FRONTEND_PORT}...", "INFO")
    try:
        # Use npm run dev
        subprocess.run("npm run dev", shell=True, cwd=FRONTEND_DIR, check=True)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        log(f"Frontend failed: {e}", "ERROR")

def main():
    log("=== GraphRAG Engine Launcher ===", "INFO")
    
    # 1. Check Pre-requisites
    check_frontend_setup()

    # 2. Start Services
    try:
        # We start backend in a thread to allow parallel execution, 
        # but in a real 'production' script we might use subprocess.Popen for both.
        # However, for a simple dev runner, threads work reasonably well if we want to share stdout.
        # A robust way is two Popens.
        
        backend_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", str(BACKEND_PORT), "--reload"],
            cwd=os.getcwd()
        )
        
        frontend_process = subprocess.Popen(
            "npm run dev", 
            shell=True,
            cwd=FRONTEND_DIR
        )

        log("Services started.", "SUCCESS")
        log(f"Backend: http://localhost:{BACKEND_PORT}", "LINK")
        log(f"Frontend: http://localhost:{FRONTEND_PORT}", "LINK")
        log("Press Ctrl+C to stop.", "INFO")

        # Wait for user interruption
        backend_process.wait()
        frontend_process.wait()

    except KeyboardInterrupt:
        log("\nStopping services...", "WARN")
        backend_process.terminate()
        frontend_process.terminate()
        log("Shutdown complete.", "SUCCESS")

if __name__ == "__main__":
    main()
