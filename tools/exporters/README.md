# Mac GPU Exporter Setup

This exporter reads GPU metrics from macOS `powermetrics` and exposes them in Prometheus format.

## Prerequisites

Ensure powermetrics is running (requires sudo):

```bash
sudo powermetrics --samplers gpu_power -f plist -i 500 -o /tmp/gpu_metrics_pm
```

## Installation

### 1. Install LaunchAgent (exporter service)

```bash
# Copy plist to LaunchAgents
cp com.agentic.mac-gpu-exporter.plist ~/Library/LaunchAgents/

# Load the service
launchctl load ~/Library/LaunchAgents/com.agentic.mac-gpu-exporter.plist

# Verify it's running
curl http://localhost:9101/metrics
```

### 2. Verify metrics

```bash
curl http://localhost:9101/metrics
```

## Exposed Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `mac_gpu_utilization` | gauge | GPU utilization ratio (0-1) |
| `mac_gpu_frequency_hz` | gauge | Current GPU frequency |
| `mac_gpu_idle_ratio` | gauge | GPU idle ratio (0-1) |
| `mac_gpu_dvfm_state_ratio` | gauge | Time in each frequency state |
| `mac_gpu_exporter_up` | gauge | Exporter health (always 1) |

## Troubleshooting

```bash
# Check logs
tail -f /tmp/mac-gpu-exporter.log
tail -f /tmp/mac-gpu-exporter.err

# Restart service
launchctl unload ~/Library/LaunchAgents/com.agentic.mac-gpu-exporter.plist
launchctl load ~/Library/LaunchAgents/com.agentic.mac-gpu-exporter.plist

# Test manually
python3 mac_gpu_exporter.py --port 9101
```
