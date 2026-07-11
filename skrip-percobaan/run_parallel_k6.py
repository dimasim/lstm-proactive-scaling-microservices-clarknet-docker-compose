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
  discardResponseBodies: true,
  scenarios: {{
    media_scenario: {{
      executor: 'ramping-arrival-rate',
      startRate: 0,
      timeUnit: '1s',
      preAllocatedVUs: 10,
      maxVUs: 50,
      stages: [
        {",\n        ".join(media_stages)}
      ],
      exec: 'media_request',
    }},
    content_scenario: {{
      executor: 'ramping-arrival-rate',
      startRate: 0,
      timeUnit: '1s',
      preAllocatedVUs: 5,
      maxVUs: 20,
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
    # Usage: python3 run_parallel_k6.py [duration_seconds] [start_idx_a] [start_idx_b] [start_idx_c]
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    # Day 7 of Week 1 starts at index 518400
    start_idx_a = int(sys.argv[2]) if len(sys.argv) > 2 else 518400
    # Day 2 of Week 2 starts at index 691200
    start_idx_b = int(sys.argv[3]) if len(sys.argv) > 3 else 691200
    # Day 5 of Week 2 starts at index 950400
    start_idx_c = int(sys.argv[4]) if len(sys.argv) > 4 else 950400

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

    reg_c = CollectorRegistry()
    gauge_media_c = Gauge('sent_rps_media', 'Exact sent RPS for media', registry=reg_c)
    gauge_content_c = Gauge('sent_rps_content', 'Exact sent RPS for content', registry=reg_c)
    start_http_server(8013, registry=reg_c)
    print("Started Prometheus exporter C on port 8013")

    csv_path_w1 = "dataset/aggregated_clarknet_rps_3x.csv"
    csv_path_w2 = "dataset/aggregated_clarknet_rps_week2_3x.csv"
    print(f"Loading workloads from {csv_path_w1} and {csv_path_w2}...")
    
    rows = []
    with open(csv_path_w1, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "Media_Service": int(row["Media_Service"]),
                "Content_Service": int(row["Content_Service"])
            })

    with open(csv_path_w2, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "Media_Service": int(row["Media_Service"]),
                "Content_Service": int(row["Content_Service"])
            })

    # Helper to slice safely
    def get_slice(data, start, size):
        res = data[start:start + size]
        if len(res) < size:
            res += [{"Media_Service": 0, "Content_Service": 0}] * (size - len(res))
        return res

    # Slice windows
    window_a = get_slice(rows, start_idx_a, duration)
    window_b = get_slice(rows, start_idx_b, duration)
    window_c = get_slice(rows, start_idx_c, duration)

    # Generate scripts
    generate_k6_script(window_a, "a", 8000)
    generate_k6_script(window_b, "b", 8001)
    generate_k6_script(window_c, "c", 8002)

    # Clock synchronization
    now = time.time()
    sync_ts = int(now) + 2
    sleep_time = sync_ts - now
    print(f"Aligning clocks. Sleeping for {sleep_time:.4f}s to start at Unix Epoch {sync_ts}...")
    time.sleep(sleep_time)

    start_time = sync_ts
    end_time = sync_ts + duration

    # We chunk the duration into 1-hour segments to prevent k6 memory issues
    chunk_size = 3600
    num_chunks = (duration + chunk_size - 1) // chunk_size

    for chunk_idx in range(num_chunks):
        chunk_offset = chunk_idx * chunk_size
        current_chunk_duration = min(chunk_size, duration - chunk_offset)

        # Slice windows for this chunk
        window_a_chunk = window_a[chunk_offset:chunk_offset + current_chunk_duration]
        window_b_chunk = window_b[chunk_offset:chunk_offset + current_chunk_duration]
        window_c_chunk = window_c[chunk_offset:chunk_offset + current_chunk_duration]

        # Generate scripts for this chunk
        generate_k6_script(window_a_chunk, "a", 8000)
        generate_k6_script(window_b_chunk, "b", 8001)
        generate_k6_script(window_c_chunk, "c", 8002)

        # Spawn three k6 processes
        print(f"Spawning chunk {chunk_idx + 1}/{num_chunks} load generators...")
        k6_a = subprocess.Popen(
            ["./k6", "run", "skrip-percobaan/k6_replay_a.js"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        k6_b = subprocess.Popen(
            ["./k6", "run", "skrip-percobaan/k6_replay_b.js"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        k6_c = subprocess.Popen(
            ["./k6", "run", "skrip-percobaan/k6_replay_c.js"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        next_cycle_start = float(sync_ts + chunk_offset)
        for second in range(current_chunk_duration):
            cycle_start = next_cycle_start
            next_cycle_start = cycle_start + 1.0

            # Load values
            m_a = window_a_chunk[second]["Media_Service"]
            c_a = window_a_chunk[second]["Content_Service"]
            m_b = window_b_chunk[second]["Media_Service"]
            c_b = window_b_chunk[second]["Content_Service"]
            m_c = window_c_chunk[second]["Media_Service"]
            c_c = window_c_chunk[second]["Content_Service"]

            # Set Gauges
            gauge_media_a.set(m_a)
            gauge_content_a.set(c_a)
            gauge_media_b.set(m_b)
            gauge_content_b.set(c_b)
            gauge_media_c.set(m_c)
            gauge_content_c.set(c_c)

            global_second = chunk_offset + second
            if (global_second + 1) % 10 == 0 or global_second == 0:
                print(f"Cycle {global_second+1}/{duration}:")
                print(f"  - Bot A: Media={m_a}, Content={c_a}")
                print(f"  - Bot B: Media={m_b}, Content={c_b}")
                print(f"  - Bot C: Media={m_c}, Content={c_c}")

            # Wait for next second boundary
            now = time.time()
            sleep_to_next = next_cycle_start - now
            if sleep_to_next > 0:
                time.sleep(sleep_to_next)

        # Wait for k6 processes to shut down
        k6_a.wait()
        k6_b.wait()
        k6_c.wait()

    # Reset Gauges
    gauge_media_a.set(0.0)
    gauge_content_a.set(0.0)
    gauge_media_b.set(0.0)
    gauge_content_b.set(0.0)
    gauge_media_c.set(0.0)
    gauge_content_c.set(0.0)
    print("Parallel Load Test Completed successfully.")

    # Automatically call metrics collector
    print("\nTriggering parallel metrics extraction...")
    collect_cmd = [
        "python3", "skrip-percobaan/collect_parallel_metrics.py",
        str(start_time), str(end_time), str(start_idx_a), str(start_idx_b), str(start_idx_c)
    ]
    subprocess.run(collect_cmd)

if __name__ == "__main__":
    main()
