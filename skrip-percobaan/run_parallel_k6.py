import os
import sys
import time
import subprocess
import threading
import csv
import argparse
import string
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
        {",\\n        ".join(media_stages)}
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
        {",\\n        ".join(content_stages)}
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
    parser = argparse.ArgumentParser(
        description="Run parallel k6 load tests with N sets",
        usage="python3 run_parallel_k6.py <duration> [options]"
    )
    parser.add_argument("duration", type=int, help="Duration in seconds")
    parser.add_argument("--sets", type=str, default="a,b,c",
                        help="Comma-separated set suffixes (default: a,b,c)")
    parser.add_argument("--start-indices", type=str, default=None,
                        help="Comma-separated dataset start indices for each set")
    parser.add_argument("--port-start", type=int, default=8000,
                        help="Starting HAProxy port (default: 8000)")
    parser.add_argument("--exporter-port-start", type=int, default=8011,
                        help="Starting Prometheus exporter port (default: 8011)")
    
    # Legacy positional args support
    parser.add_argument("legacy_args", nargs="*", type=int, help=argparse.SUPPRESS)
    
    args = parser.parse_args()
    
    duration = args.duration
    suffixes = args.sets.split(",")
    num_sets = len(suffixes)
    
    # Handle start indices
    if args.start_indices:
        start_indices = [int(x) for x in args.start_indices.split(",")]
    elif args.legacy_args:
        start_indices = args.legacy_args
    else:
        # Default: no overlap, evenly spaced across full dataset
        total_rows = 1209425
        chunk = total_rows // num_sets
        start_indices = [i * chunk for i in range(num_sets)]
    
    if len(suffixes) != len(start_indices):
        print(f"❌ Error: {len(suffixes)} sets but {len(start_indices)} start indices")
        return
    
    # Assign ports
    ports = [args.port_start + i for i in range(num_sets)]
    exporter_ports = [args.exporter_port_start + i for i in range(num_sets)]
    
    print(f"🚀 Starting {num_sets}-parallel load test")
    print(f"📊 Sets: {', '.join(s.upper() for s in suffixes)}")
    print(f"⏱️  Duration: {duration}s ({duration/3600:.1f}h, {duration/86400:.1f}d)")
    
    # Start Prometheus exporters for each set
    registries = []
    gauge_media = []
    gauge_content = []
    
    for i, suffix in enumerate(suffixes):
        reg = CollectorRegistry()
        gm = Gauge('sent_rps_media', 'Exact sent RPS for media', registry=reg)
        gc = Gauge('sent_rps_content', 'Exact sent RPS for content', registry=reg)
        start_http_server(exporter_ports[i], registry=reg)
        print(f"  Started Prometheus exporter {suffix.upper()} on port {exporter_ports[i]}")
        
        registries.append(reg)
        gauge_media.append(gm)
        gauge_content.append(gc)

    # Load datasets
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

    # Slice windows for each set
    windows = []
    for i, (suffix, start_idx) in enumerate(zip(suffixes, start_indices)):
        window = get_slice(rows, start_idx, duration)
        windows.append(window)
        print(f"  Set {suffix.upper()}: rows {start_idx} - {start_idx + duration - 1}")

    # Generate initial scripts
    for i, suffix in enumerate(suffixes):
        generate_k6_script(windows[i], suffix, ports[i])

    # Clock synchronization
    now = time.time()
    sync_ts = int(now) + 2
    sleep_time = sync_ts - now
    print(f"Aligning clocks. Sleeping for {sleep_time:.4f}s to start at Unix Epoch {sync_ts}...")
    time.sleep(sleep_time)

    start_time = sync_ts
    end_time = sync_ts + duration

    # Chunk duration into 1-hour segments to prevent k6 memory issues
    chunk_size = 3600
    num_chunks = (duration + chunk_size - 1) // chunk_size

    for chunk_idx in range(num_chunks):
        chunk_offset = chunk_idx * chunk_size
        current_chunk_duration = min(chunk_size, duration - chunk_offset)

        # Slice windows for this chunk
        window_chunks = []
        for i in range(num_sets):
            wc = windows[i][chunk_offset:chunk_offset + current_chunk_duration]
            window_chunks.append(wc)

        # Generate scripts for this chunk
        for i, suffix in enumerate(suffixes):
            generate_k6_script(window_chunks[i], suffix, ports[i])

        # Spawn k6 processes for all sets
        print(f"Spawning chunk {chunk_idx + 1}/{num_chunks} load generators...")
        k6_procs = []
        for i, suffix in enumerate(suffixes):
            proc = subprocess.Popen(
                ["./k6", "run", f"skrip-percobaan/k6_replay_{suffix}.js"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            k6_procs.append(proc)

        next_cycle_start = float(sync_ts + chunk_offset)
        for second in range(current_chunk_duration):
            cycle_start = next_cycle_start
            next_cycle_start = cycle_start + 1.0

            # Fix Bug #2: Set gauges BEFORE sleep to better align with Prometheus scrape
            for i in range(num_sets):
                m = window_chunks[i][second]["Media_Service"]
                c = window_chunks[i][second]["Content_Service"]
                gauge_media[i].set(m)
                gauge_content[i].set(c)

            global_second = chunk_offset + second
            if (global_second + 1) % 10 == 0 or global_second == 0:
                print(f"Cycle {global_second+1}/{duration}:")
                for i, suffix in enumerate(suffixes):
                    m = window_chunks[i][second]["Media_Service"]
                    c = window_chunks[i][second]["Content_Service"]
                    print(f"  - Bot {suffix.upper()}: Media={m}, Content={c}")

            # Wait for next second boundary
            now = time.time()
            sleep_to_next = next_cycle_start - now
            if sleep_to_next > 0:
                time.sleep(sleep_to_next)

        # Wait for k6 processes to shut down
        for proc in k6_procs:
            proc.wait()

    # Reset all gauges
    for i in range(num_sets):
        gauge_media[i].set(0.0)
        gauge_content[i].set(0.0)
    
    print("Parallel Load Test Completed successfully.")

    # Automatically call metrics collector
    print("\nTriggering parallel metrics extraction...")
    collect_cmd = [
        "python3", "skrip-percobaan/collect_parallel_metrics.py",
        str(start_time), str(end_time),
        "--sets", ",".join(suffixes),
        "--start-indices", ",".join(str(idx) for idx in start_indices)
    ]
    subprocess.run(collect_cmd)

if __name__ == "__main__":
    main()
