import os
import sys
import time
import subprocess
import threading
import queue
import random
import csv
from collections import Counter
from prometheus_client import CollectorRegistry, Gauge, start_http_server

# HTTP session settings
import requests
session_a = requests.Session()
adapter_a = requests.adapters.HTTPAdapter(pool_connections=500, pool_maxsize=500)
session_a.mount('http://', adapter_a)

session_b = requests.Session()
adapter_b = requests.adapters.HTTPAdapter(pool_connections=500, pool_maxsize=500)
session_b.mount('http://', adapter_b)

# Request Queues
queue_a = queue.Queue()
queue_b = queue.Queue()

def send_request(session, port, endpoint):
    try:
        session.get(f"http://localhost:{port}{endpoint}", timeout=1.5)
    except Exception:
        pass

def worker_thread(session, port, req_queue):
    while True:
        req = req_queue.get()
        if req is None:
            break
        send_request(session, port, req)
        req_queue.task_done()

def main():
    # Usage: python3 run_parallel_load.py [duration_seconds] [start_idx_a] [start_idx_b]
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    start_idx_a = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    start_idx_b = int(sys.argv[3]) if len(sys.argv) > 3 else 259200

    # Start independent Prometheus exporters
    reg_a = CollectorRegistry()
    gauge_media_a = Gauge('sent_rps_media', 'Exact sent RPS for media', registry=reg_a)
    gauge_content_a = Gauge('sent_rps_content', 'Exact sent RPS for content', registry=reg_a)
    try:
        start_http_server(8011, registry=reg_a)
        print("Started Prometheus exporter A on port 8011")
    except Exception as e:
        print(f"Prometheus exporter A port 8011 already bound or failed: {e}")

    reg_b = CollectorRegistry()
    gauge_media_b = Gauge('sent_rps_media', 'Exact sent RPS for media', registry=reg_b)
    gauge_content_b = Gauge('sent_rps_content', 'Exact sent RPS for content', registry=reg_b)
    try:
        start_http_server(8012, registry=reg_b)
        print("Started Prometheus exporter B on port 8012")
    except Exception as e:
        print(f"Prometheus exporter B port 8012 already bound or failed: {e}")

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

    # Pre-start worker threads
    num_workers_a = 50
    workers_a = []
    for _ in range(num_workers_a):
        t = threading.Thread(target=worker_thread, args=(session_a, 8000, queue_a), daemon=True)
        t.start()
        workers_a.append(t)

    num_workers_b = 50
    workers_b = []
    for _ in range(num_workers_b):
        t = threading.Thread(target=worker_thread, args=(session_b, 8001, queue_b), daemon=True)
        t.start()
        workers_b.append(t)

    # Clock synchronization
    now = time.time()
    sync_ts = int(now) + 2
    sleep_time = sync_ts - now
    print(f"Aligning clocks. Sleeping for {sleep_time:.4f}s to start at Unix Epoch {sync_ts}...")
    time.sleep(sleep_time)

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
            print(f"  - Bot A (Port 8000): Media={m_a}, Content={c_a}")
            print(f"  - Bot B (Port 8001): Media={m_b}, Content={c_b}")

        # Queue requests for Bot A
        reqs_a = (["/media"] * m_a) + (["/content"] * c_a)
        random.shuffle(reqs_a)
        
        # Queue requests for Bot B
        reqs_b = (["/media"] * m_b) + (["/content"] * c_b)
        random.shuffle(reqs_b)

        # Dispatch Bot A requests uniformly across the second
        if reqs_a:
            spacing_a = 1.0 / len(reqs_a)
            for idx, r in enumerate(reqs_a):
                target_time = cycle_start + (idx * spacing_a)
                sleep_for = target_time - time.time()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                queue_a.put(r)

        # Dispatch Bot B requests uniformly across the second
        if reqs_b:
            spacing_b = 1.0 / len(reqs_b)
            for idx, r in enumerate(reqs_b):
                target_time = cycle_start + (idx * spacing_b)
                sleep_for = target_time - time.time()
                if sleep_for > 0:
                    time.sleep(sleep_for)
                queue_b.put(r)

        # Sleep to align cycle boundary
        now = time.time()
        sleep_to_next = next_cycle_start - now
        if sleep_to_next > 0:
            time.sleep(sleep_to_next)

    # Reset Gauges
    gauge_media_a.set(0.0)
    gauge_content_a.set(0.0)
    gauge_media_b.set(0.0)
    gauge_content_b.set(0.0)

    # Stop workers
    for _ in range(num_workers_a):
        queue_a.put(None)
    for _ in range(num_workers_b):
        queue_b.put(None)
        
    for t in workers_a:
        t.join(timeout=1.0)
    for t in workers_b:
        t.join(timeout=1.0)

    print("Load Test Completed successfully.")

    # Automatically call metrics collector
    print("\nTriggering parallel metrics extraction...")
    collect_cmd = [
        "python3", "skrip-percobaan/collect_parallel_metrics.py",
        str(start_time), str(end_time), str(start_idx_a), str(start_idx_b)
    ]
    subprocess.run(collect_cmd)

if __name__ == "__main__":
    main()
