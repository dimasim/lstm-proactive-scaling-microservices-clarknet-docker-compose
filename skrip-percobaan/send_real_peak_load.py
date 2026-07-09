import time
import requests
import queue
import threading
import random
import pandas as pd
from collections import Counter
from prometheus_client import start_http_server, Gauge

# Start Prometheus metrics exporter server on port 8001
try:
    start_http_server(8001)
    print("Started Prometheus exporter on port 8001")
except Exception as e:
    print(f"Prometheus exporter port 8001 already bound or failed: {e}")

GAUGE_MEDIA = Gauge('sent_rps_media', 'Exact sent RPS for media')
GAUGE_CONTENT = Gauge('sent_rps_content', 'Exact sent RPS for content')

BASE_URL = "http://localhost:8000"

# Use Session with custom pool size to support high concurrency
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=500, pool_maxsize=500)
session.mount('http://', adapter)
session.mount('https://', adapter)

# Mutex and counters for statistics
stats_lock = threading.Lock()
stats = Counter()
cycle_results = []

# Simple Queue for dispatching requests
request_queue = queue.Queue()

def send_request(endpoint: str):
    success = False
    try:
        r = session.get(f"{BASE_URL}{endpoint}", timeout=1.5)
        success = (r.status_code == 200)
    except Exception:
        pass
    
    with stats_lock:
        stats[f"{endpoint}_{r.status_code if success else 'failed'}"] += 1
        cycle_results.append(success)

def worker_thread():
    while True:
        req = request_queue.get()
        if req is None:
            break
        send_request(req)
        request_queue.task_done()

def main():
    # Load dataset and extract 5 minutes (300s) centered around the peak (index 254291)
    csv_path = "dataset/aggregated_clarknet_rps_3x.csv"
    print(f"Loading workload from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    peak_idx = 254291
    start_idx = max(0, peak_idx - 150)
    end_idx = min(len(df) - 1, peak_idx + 150)
    window_df = df.iloc[start_idx:end_idx].copy().reset_index(drop=True)
    
    print(f"Extracted {len(window_df)} seconds of workload around the peak.")
    
    # Pre-start worker threads
    num_workers = 100
    workers = []
    for _ in range(num_workers):
        t = threading.Thread(target=worker_thread, daemon=True)
        t.start()
        workers.append(t)

    start_ts = int(time.time())
    print(f"\nStarting real peak load test for 5 minutes (300 seconds)...")
    print(f"Start Epoch Timestamp: {start_ts}")

    # Absolute time tracking to prevent drift
    next_cycle_start = time.time()

    # Replay the 300 seconds
    for second in range(len(window_df)):
        cycle_start = next_cycle_start
        next_cycle_start = cycle_start + 1.0
        
        media_rps = int(window_df.loc[second, "Media_Service"])
        content_rps = int(window_df.loc[second, "Content_Service"])
        total_rps = media_rps + content_rps
        
        # Update Prometheus Gauges for exact sent RPS
        GAUGE_MEDIA.set(media_rps)
        GAUGE_CONTENT.set(content_rps)
        
        with stats_lock:
            cycle_results.clear()
        
        # Combine and shuffle requests to simulate realistic mixed traffic flow
        requests_to_send = (["/media"] * media_rps) + (["/content"] * content_rps)
        random.shuffle(requests_to_send)
        
        # Queue requests uniformly across the 1-second cycle
        num_reqs = len(requests_to_send)
        if num_reqs > 0:
            req_spacing = 1.0 / num_reqs
            for req_idx, req in enumerate(requests_to_send):
                target_req_time = cycle_start + (req_idx * req_spacing)
                now = time.time()
                sleep_for = target_req_time - now
                if sleep_for > 0:
                    time.sleep(sleep_for)
                request_queue.put(req)
        
        # Sleep until the next absolute cycle start time to align boundaries
        now = time.time()
        sleep_time = next_cycle_start - now
        if sleep_time > 0:
            time.sleep(sleep_time)
        
        # Briefly wait for workers
        time.sleep(0.015)
        with stats_lock:
            completed = len(cycle_results)
            successes = sum(1 for x in cycle_results if x)
            cycle_results.clear()
            
        cycle_success_rate = (successes / completed * 100) if completed > 0 else 100.0
        if (second + 1) % 10 == 0 or second == 0:
            print(f"Cycle {second+1}/300: Sent {total_rps} RPS (M:{media_rps}, C:{content_rps}) -> Dispatched. Success Rate: {cycle_success_rate:.2f}%")

    # Stop workers
    for _ in range(num_workers):
        request_queue.put(None)
    for t in workers:
        t.join(timeout=1.0)

    # Reset Gauges to 0
    GAUGE_MEDIA.set(0.0)
    GAUGE_CONTENT.set(0.0)

    end_ts = int(time.time())
    with stats_lock:
        print("\n=== Test Results ===")
        print(f"End Epoch Timestamp: {end_ts}")
        for key, value in stats.items():
            print(f"{key}: {value} requests")
        total_requests = sum(stats.values())
        success_requests = stats.get("/media_200", 0) + stats.get("/content_200", 0)
        success_rate = (success_requests / total_requests) * 100 if total_requests > 0 else 0
        print(f"Total requests dispatched: {total_requests}")
        print(f"Success Rate: {success_rate:.2f}%")

if __name__ == "__main__":
    main()
