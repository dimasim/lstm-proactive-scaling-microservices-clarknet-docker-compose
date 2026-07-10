import os
import sys
import time
import subprocess
import threading
import csv
from prometheus_client import CollectorRegistry, Gauge, start_http_server

def generate_k6_script(window_df, suffix, port):
    media_stages = []
    content_stages = []
    
    for row in window_df:
        m_rps = int(row["Media_Service"])
        c_rps = int(row["Content_Service"])
        media_stages.append(f"{{ target: {m_rps}, duration: '1s' }}")
        content_stages.append(f"{{ target: {c_rps}, duration: '1s' }}")
        
    js_content = f"""
import http from 'k6/http';

export const options = {{
  scenarios: {{
    media_scenario: {{
      executor: 'ramping-arrival-rate',
      startRate: 0,
      timeUnit: '1s',
      preAllocatedVUs: 150,
      maxVUs: 400,
      stages: [
        {",\n        ".join(media_stages)}
      ],
      exec: 'media_request',
    }},
    content_scenario: {{
      executor: 'ramping-arrival-rate',
      startRate: 0,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 150,
      stages: [
        {",\n        ".join(content_stages)}
      ],
      exec: 'content_request',
    }},
  }},
}};

export function media_request() {{
  http.get('http://localhost:{port}/media', {{ timeout: '1.5s' }});
}}

export function content_request() {{
  http.get('http://localhost:{port}/content', {{ timeout: '1.5s' }});
}}
"""
    filename = f"skrip-percobaan/k6_replay_{suffix}.js"
    with open(filename, "w") as f:
        f.write(js_content)
    print(f"Generated {filename} successfully.")

def main():
    # Usage: python3 run_parallel_k6.py [duration_seconds] [start_idx_a] [start_idx_b]
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    start_idx_a = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    # Default Week 2 starts exactly 1 week (604800 seconds) after Week 1
    start_idx_b = int(sys.argv[3]) if len(sys.argv) > 3 else 604800

    # Start independent Prometheus exporters
    reg_a = CollectorRegistry()
    gauge_media_a = Gauge('sent_rps_media', 'Exact sent RPS for media', registry=reg_a)
    gauge_content_a = Gauge('sent_rps_content', 'Exact sent RPS for content', registry=reg_a)
    start_http_server(8011, registry=reg_a)
    print("Started Prometheus exporter A on port 8011")

    reg_b = CollectorRegistry()
    gauge_media_b = Gauge('sent_rps_media', 'Exact sent RPS for media', registry=reg_b)
    gauge_content_b = Gauge('sent_rps_content', 'Exact sent RPS for content', registry=reg_b)
    start_http_server(8012, registry=reg_b)
    print("Started Prometheus exporter B on port 8012")

    csv_path = "dataset/aggregated_clarknet_rps_3x.csv"
    print(f"Loading workload from {csv_path}...")
    
    rows = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "Media_Service": int(row["Media_Service"]),
                "Content_Service": int(row["Content_Service"])
            })

    # Slice windows
    window_a = rows[start_idx_a:start_idx_a + duration]
    window_b = rows[start_idx_b:start_idx_b + duration]

    # Generate scripts
    generate_k6_script(window_a, "a", 8000)
    generate_k6_script(window_b, "b", 8001)

    # Clock synchronization
    now = time.time()
    sync_ts = int(now) + 2
    sleep_time = sync_ts - now
    print(f"Aligning clocks. Sleeping for {sleep_time:.4f}s to start at Unix Epoch {sync_ts}...")
    time.sleep(sleep_time)

    # Spawn both k6 processes
    print("Spawning parallel k6 load generators...")
    k6_a = subprocess.Popen(
        ["./k6", "run", "skrip-percobaan/k6_replay_a.js"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    k6_b = subprocess.Popen(
        ["./k6", "run", "skrip-percobaan/k6_replay_b.js"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    start_time = sync_ts
    end_time = sync_ts + duration

    next_cycle_start = float(sync_ts)
    for second in range(duration):
        cycle_start = next_cycle_start
        next_cycle_start = cycle_start + 1.0

        # Load values
        m_a = window_a[second]["Media_Service"] if second < len(window_a) else 0
        c_a = window_a[second]["Content_Service"] if second < len(window_a) else 0
        m_b = window_b[second]["Media_Service"] if second < len(window_b) else 0
        c_b = window_b[second]["Content_Service"] if second < len(window_b) else 0

        # Set Gauges
        gauge_media_a.set(m_a)
        gauge_content_a.set(c_a)
        gauge_media_b.set(m_b)
        gauge_content_b.set(c_b)

        if (second + 1) % 10 == 0 or second == 0:
            print(f"Cycle {second+1}/{duration}:")
            print(f"  - Bot A: Media={m_a}, Content={c_a}")
            print(f"  - Bot B: Media={m_b}, Content={c_b}")

        # Wait for next second boundary
        now = time.time()
        sleep_to_next = next_cycle_start - now
        if sleep_to_next > 0:
            time.sleep(sleep_to_next)

    # Reset Gauges
    gauge_media_a.set(0.0)
    gauge_content_a.set(0.0)
    gauge_media_b.set(0.0)
    gauge_content_b.set(0.0)

    print("Waiting for k6 processes to shut down...")
    k6_a.wait()
    k6_b.wait()
    print("Parallel Load Test Completed successfully.")

    # Automatically call metrics collector
    print("\nTriggering parallel metrics extraction...")
    collect_cmd = [
        "python3", "skrip-percobaan/collect_parallel_metrics.py",
        str(start_time), str(end_time), str(start_idx_a), str(start_idx_b)
    ]
    subprocess.run(collect_cmd)

if __name__ == "__main__":
    main()
