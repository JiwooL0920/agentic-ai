#!/usr/bin/env python3
"""Mac GPU Metrics Exporter for Prometheus.

Reads GPU metrics from powermetrics plist output and exposes them
in Prometheus format on port 9101.

Requires powermetrics running:
    sudo powermetrics --samplers gpu_power -f plist -i 500 -o /tmp/gpu_metrics_pm

Usage:
    python mac_gpu_exporter.py [--port 9101] [--plist-path /tmp/gpu_metrics_pm]
"""

import argparse
import plistlib
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

# Default configuration
DEFAULT_PORT = 9101
DEFAULT_PLIST_PATH = "/tmp/gpu_metrics_pm"


class GPUMetrics:
    """Container for parsed GPU metrics."""

    def __init__(self) -> None:
        self.gpu_utilization: float = 0.0  # 1 - idle_ratio
        self.gpu_frequency_hz: float = 0.0
        self.gpu_idle_ratio: float = 0.0
        self.timestamp: str = ""
        self.hw_model: str = "unknown"
        self.dvfm_states: list[dict[str, Any]] = []

    def to_prometheus(self) -> str:
        """Convert metrics to Prometheus exposition format."""
        lines = [
            "# HELP mac_gpu_utilization GPU utilization ratio (0-1)",
            "# TYPE mac_gpu_utilization gauge",
            f'mac_gpu_utilization{{model="{self.hw_model}"}} {self.gpu_utilization:.6f}',
            "",
            "# HELP mac_gpu_frequency_hz Current GPU frequency in Hz",
            "# TYPE mac_gpu_frequency_hz gauge",
            f'mac_gpu_frequency_hz{{model="{self.hw_model}"}} {self.gpu_frequency_hz:.2f}',
            "",
            "# HELP mac_gpu_idle_ratio GPU idle ratio (0-1)",
            "# TYPE mac_gpu_idle_ratio gauge",
            f'mac_gpu_idle_ratio{{model="{self.hw_model}"}} {self.gpu_idle_ratio:.6f}',
            "",
            "# HELP mac_gpu_dvfm_state_ratio Time spent in each DVFM frequency state",
            "# TYPE mac_gpu_dvfm_state_ratio gauge",
        ]

        for state in self.dvfm_states:
            freq = state.get("freq", 0)
            ratio = state.get("used_ratio", 0)
            lines.append(
                f'mac_gpu_dvfm_state_ratio{{model="{self.hw_model}",freq_mhz="{freq}"}} {ratio:.6f}'
            )

        lines.extend([
            "",
            "# HELP mac_gpu_exporter_up Whether the exporter is running (1 = up)",
            "# TYPE mac_gpu_exporter_up gauge",
            "mac_gpu_exporter_up 1",
            "",
            "# HELP mac_gpu_scrape_timestamp_seconds Unix timestamp of last successful scrape",
            "# TYPE mac_gpu_scrape_timestamp_seconds gauge",
            f"mac_gpu_scrape_timestamp_seconds {time.time():.0f}",
        ])

        return "\n".join(lines) + "\n"


def parse_plist(plist_path: Path) -> GPUMetrics:
    """Parse powermetrics plist file and extract GPU metrics."""
    metrics = GPUMetrics()

    try:
        with open(plist_path, "rb") as f:
            # Read the entire file and find the last complete plist
            content = f.read()

        # Find all plist documents (powermetrics appends new ones)
        # We want the last complete one
        plist_end = b"</plist>"
        last_end = content.rfind(plist_end)
        if last_end == -1:
            return metrics

        # Find the start of this plist
        search_start = max(0, last_end - 50000)  # Search within last ~50KB
        plist_start_marker = b'<?xml version="1.0"'
        chunk = content[search_start : last_end + len(plist_end)]
        plist_start = chunk.rfind(plist_start_marker)
        if plist_start == -1:
            return metrics

        # Extract and parse the plist
        plist_data = chunk[plist_start:]
        data = plistlib.loads(plist_data)

        # Extract GPU metrics
        metrics.hw_model = data.get("hw_model", "unknown")
        metrics.timestamp = str(data.get("timestamp", ""))

        gpu = data.get("gpu", {})
        if gpu:
            metrics.gpu_frequency_hz = float(gpu.get("freq_hz", 0))
            metrics.gpu_idle_ratio = float(gpu.get("idle_ratio", 0))
            metrics.gpu_utilization = 1.0 - metrics.gpu_idle_ratio
            metrics.dvfm_states = gpu.get("dvfm_states", [])

    except (FileNotFoundError, plistlib.InvalidFileException) as e:
        print(f"Error reading plist: {e}")
    except Exception as e:
        print(f"Unexpected error parsing plist: {e}")

    return metrics


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for Prometheus metrics endpoint."""

    plist_path: Path = Path(DEFAULT_PLIST_PATH)

    def do_GET(self) -> None:
        """Handle GET requests."""
        if self.path == "/metrics":
            metrics = parse_plist(self.plist_path)
            response = metrics.to_prometheus()

            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response.encode("utf-8"))
        elif self.path == "/health" or self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK\n")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default logging for cleaner output."""
        pass


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Mac GPU Metrics Exporter for Prometheus"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port to listen on (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--plist-path",
        type=str,
        default=DEFAULT_PLIST_PATH,
        help=f"Path to powermetrics plist file (default: {DEFAULT_PLIST_PATH})",
    )
    args = parser.parse_args()

    MetricsHandler.plist_path = Path(args.plist_path)

    server = HTTPServer(("0.0.0.0", args.port), MetricsHandler)
    print(f"Mac GPU Exporter listening on port {args.port}")
    print(f"Reading metrics from: {args.plist_path}")
    print(f"Metrics endpoint: http://localhost:{args.port}/metrics")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
