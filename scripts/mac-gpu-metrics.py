#!/usr/bin/env python3
"""
Mac GPU metrics server for Apple Silicon.
Uses powermetrics (continuous plist output) for accurate GPU utilization.

This approach mirrors how asitop works - running powermetrics as a background
process that continuously writes to a file, then parsing the latest plist entry.

Run with sudo for accurate GPU metrics:
  sudo python3 scripts/mac-gpu-metrics.py

Access at: http://localhost:8002/gpu
Debug at:  http://localhost:8002/debug
"""

import glob
import json
import os
import plistlib
import signal
import subprocess
import re
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from subprocess import PIPE
from typing import Any, Dict, Optional

_metrics: Dict[str, Any] = {
    "percent": 0,
    "vram_used_gb": 0.0,
    "vram_allocated_gb": 0.0,
    "source": "initializing",
}
_lock = threading.Lock()
_powermetrics_process: Optional[subprocess.Popen] = None
_powermetrics_file = "/tmp/gpu_metrics_pm"


def start_powermetrics_background() -> bool:
    """Start powermetrics as a continuous background process writing plist to file."""
    global _powermetrics_process
    
    # Clean up old files
    for tmpf in glob.glob("/tmp/gpu_metrics_pm*"):
        try:
            os.remove(tmpf)
        except OSError:
            pass
    
    try:
        # Run powermetrics continuously, writing plist to file
        # Using interval of 500ms for responsive updates (same as asitop default)
        cmd = [
            "powermetrics",
            "--samplers", "gpu_power",
            "-f", "plist",
            "-i", "500",
            "-o", _powermetrics_file,
        ]
        _powermetrics_process = subprocess.Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        print(f"✅ Started powermetrics background process (PID: {_powermetrics_process.pid})")
        return True
    except PermissionError:
        print("❌ powermetrics requires sudo")
        return False
    except FileNotFoundError:
        print("❌ powermetrics not found")
        return False
    except Exception as e:
        print(f"❌ Failed to start powermetrics: {e}")
        return False


def stop_powermetrics():
    """Stop the background powermetrics process."""
    global _powermetrics_process
    if _powermetrics_process:
        try:
            _powermetrics_process.terminate()
            _powermetrics_process.wait(timeout=2)
        except Exception:
            _powermetrics_process.kill()
        _powermetrics_process = None
        print("🛑 Stopped powermetrics background process")


def parse_powermetrics_file() -> Dict[str, Any]:
    """Parse GPU metrics from powermetrics plist file (like asitop does)."""
    try:
        if not os.path.exists(_powermetrics_file):
            return {"error": "powermetrics file not found - waiting for data"}
        
        with open(_powermetrics_file, 'rb') as fp:
            data = fp.read()
        
        if not data:
            return {"error": "powermetrics file empty"}
        
        # powermetrics writes multiple plist entries separated by null bytes
        # We want the most recent (last) valid entry
        chunks = data.split(b'\x00')
        
        plist_data = None
        for chunk in reversed(chunks):
            chunk = chunk.strip()
            if chunk:
                try:
                    plist_data = plistlib.loads(chunk)
                    break
                except Exception:
                    continue
        
        if not plist_data:
            return {"error": "no valid plist data found in file"}
        
        # Parse GPU metrics (same logic as asitop's parsers.py)
        gpu = plist_data.get("gpu", {})
        if not gpu:
            return {"error": "no gpu data in plist", "keys": list(plist_data.keys())}
        
        freq_hz = gpu.get("freq_hz", 0)
        idle_ratio = gpu.get("idle_ratio", 1.0)
        
        gpu_percent = (1.0 - idle_ratio) * 100.0
        # freq_hz on M4 is already ~763 (MHz scale), not actual Hz
        gpu_freq_mhz = int(freq_hz) if freq_hz > 0 else None
        
        return {
            "percent": round(max(0, min(100, gpu_percent)), 1),
            "frequency_mhz": gpu_freq_mhz,
            "idle_ratio": round(idle_ratio, 4),
            "source": "powermetrics-continuous",
        }
    except Exception as e:
        return {"error": f"parse error: {e}"}


def get_ioreg_memory() -> Dict[str, Any]:
    """Get GPU memory from ioreg (no sudo required)."""
    try:
        result = subprocess.run(
            ["ioreg", "-r", "-d", "1", "-c", "IOAccelerator"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        
        output = result.stdout
        
        in_use_mem = re.search(r'"In use system memory"=(\d+)', output)
        alloc_mem = re.search(r'"Alloc system memory"=(\d+)', output)
        
        in_use = int(in_use_mem.group(1)) if in_use_mem else 0
        allocated = int(alloc_mem.group(1)) if alloc_mem else 0
        
        return {
            "vram_used_bytes": in_use,
            "vram_allocated_bytes": allocated,
            "vram_used_gb": round(in_use / (1024**3), 1),
            "vram_allocated_gb": round(allocated / (1024**3), 1),
        }
    except Exception as e:
        return {"error": str(e)}


def update_metrics_loop(use_background: bool):
    global _metrics
    
    while True:
        try:
            if use_background:
                gpu_data = parse_powermetrics_file()
            else:
                gpu_data = {"error": "powermetrics not running (requires sudo)", "percent": 0}
            
            mem_data = get_ioreg_memory()
            
            with _lock:
                if "error" not in gpu_data:
                    _metrics["percent"] = gpu_data["percent"]
                    _metrics["source"] = gpu_data["source"]
                    if gpu_data.get("frequency_mhz"):
                        _metrics["frequency_mhz"] = gpu_data["frequency_mhz"]
                    if gpu_data.get("idle_ratio") is not None:
                        _metrics["idle_ratio"] = gpu_data["idle_ratio"]
                    _metrics.pop("error", None)
                else:
                    _metrics["percent"] = 0
                    _metrics["source"] = "error"
                    _metrics["error"] = gpu_data["error"]
                
                if "error" not in mem_data:
                    _metrics["vram_used_gb"] = mem_data["vram_used_gb"]
                    _metrics["vram_allocated_gb"] = mem_data["vram_allocated_gb"]
                    _metrics["vram_used_bytes"] = mem_data["vram_used_bytes"]
                    _metrics["vram_allocated_bytes"] = mem_data["vram_allocated_bytes"]
        
        except Exception as e:
            with _lock:
                _metrics["error"] = str(e)
        
        time.sleep(0.3)


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/gpu" or self.path == "/":
            with _lock:
                metrics = _metrics.copy()
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.end_headers()
            self.wfile.write(json.dumps(metrics).encode())
        
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        
        elif self.path == "/debug":
            debug_info: Dict[str, Any] = {
                "is_root": os.geteuid() == 0,
                "powermetrics_file_exists": os.path.exists(_powermetrics_file),
                "powermetrics_running": _powermetrics_process is not None and _powermetrics_process.poll() is None,
            }
            
            if os.path.exists(_powermetrics_file):
                try:
                    with open(_powermetrics_file, 'rb') as f:
                        data = f.read()
                    debug_info["file_size_bytes"] = len(data)
                    chunks = data.split(b'\x00')
                    debug_info["num_chunks"] = len(chunks)
                    
                    for chunk in reversed(chunks):
                        chunk = chunk.strip()
                        if chunk:
                            try:
                                plist_data = plistlib.loads(chunk)
                                debug_info["plist_keys"] = list(plist_data.keys())
                                if "gpu" in plist_data:
                                    debug_info["gpu_raw"] = {
                                        k: (float(v) if isinstance(v, (int, float)) else str(v))
                                        for k, v in plist_data["gpu"].items()
                                    }
                                break
                            except Exception as e:
                                debug_info["plist_error"] = str(e)
                except Exception as e:
                    debug_info["file_error"] = str(e)
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(debug_info, indent=2).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()
    
    def log_message(self, format, *args):
        pass


def signal_handler(signum, frame):
    print("\n👋 Shutting down...")
    stop_powermetrics()
    os._exit(0)


if __name__ == "__main__":
    port = 8002
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    is_root = os.geteuid() == 0
    if not is_root:
        print("⚠️  Warning: Run with sudo for accurate GPU utilization")
        print("   sudo python3 scripts/mac-gpu-metrics.py")
        print()
    
    use_background = False
    if is_root:
        use_background = start_powermetrics_background()
        if use_background:
            time.sleep(1)
    
    updater = threading.Thread(target=update_metrics_loop, args=(use_background,), daemon=True)
    updater.start()
    
    time.sleep(0.5)
    
    print(f"🖥️  Mac GPU metrics server: http://localhost:{port}/gpu")
    print(f"📊 Debug endpoint: http://localhost:{port}/debug")
    print("Press Ctrl+C to stop")
    
    server = HTTPServer(("0.0.0.0", port), MetricsHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_powermetrics()
        print("\n👋 Stopped")
