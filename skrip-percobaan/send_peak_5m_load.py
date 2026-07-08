import time
import csv
import os
import requests
import concurrent.futures
import threading
from collections import Counter

BASE_URL = "http://localhost:8000"
CSV_PATH = "dataset/aggregated_clarknet_rps.csv"
PEAK_START_IDX = 401022
DURATION = 300  # 5 minutes

# Use Session to pool connections with custom pool size to support high concurrency
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=1000, pool_maxsize=1000)
session.mount('http://', adapter)
session.mount('https://', adapter)

# Mutex, counters, and lists for statistics
stats_lock = threading.Lock()
stats = Counter()
total_stats = Counter()
media_latencies = []
content_latencies = []

def send_request(endpoint: str):
    start_time = time.time()
    try:
        r = session.get(f"{BASE_URL}{endpoint}", timeout=1.5)
        latency = (time.time() - start_time) * 1000.0
        with stats_lock:
            stats[f"{endpoint}_{r.status_code}"] += 1
            total_stats[f"{endpoint}_{r.status_code}"] += 1
            if endpoint == "/media":
                media_latencies.append(latency)
            elif endpoint == "/content":
                content_latencies.append(latency)
    except requests.exceptions.Timeout:
        latency = (time.time() - start_time) * 1000.0
        with stats_lock:
            stats[f"{endpoint}_timeout"] += 1
            total_stats[f"{endpoint}_timeout"] += 1
            if endpoint == "/media":
                media_latencies.append(latency)
            elif endpoint == "/content":
                content_latencies.append(latency)
    except Exception as e:
        latency = (time.time() - start_time) * 1000.0
        with stats_lock:
            stats[f"{endpoint}_error_{type(e).__name__}"] += 1
            total_stats[f"{endpoint}_error_{type(e).__name__}"] += 1
            if endpoint == "/media":
                media_latencies.append(latency)
            elif endpoint == "/content":
                content_latencies.append(latency)

def report_stats():
    global stats
    while True:
        time.sleep(5)
        with stats_lock:
            current_stats = dict(stats)
            stats.clear()
        if current_stats:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Last 5s Activity: {current_stats}")

def main():
    if not os.path.exists(CSV_PATH):
        print(f"Error: Dataset CSV not found at {CSV_PATH}")
        return

    print("Starting background reporter...")
    reporter = threading.Thread(target=report_stats, daemon=True)
    reporter.start()

    # Read rows
    print(f"Loading dataset and skipping to peak index {PEAK_START_IDX}...")
    peak_rows = []
    with open(CSV_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if idx >= PEAK_START_IDX:
                peak_rows.append(row)
            if len(peak_rows) >= DURATION:
                break

    start_ts = int(time.time())
    print(f"Starting 5-minute peak load test (Duration: {DURATION}s)...")
    print(f"Start Epoch Timestamp: {start_ts}")

    MULTIPLIER = 3
    print(f"Traffic Multiplier: {MULTIPLIER}x")

    # Pre-create thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=1000) as executor:
        for idx, row in enumerate(peak_rows):
            cycle_start = time.time()
            
            try:
                content_rps = int(row.get("Content_Service", 0)) * MULTIPLIER
                media_rps = int(row.get("Media_Service", 0)) * MULTIPLIER
            except ValueError:
                continue

            total_rps_target = content_rps + media_rps

            # Dispatch concurrently
            for _ in range(media_rps):
                executor.submit(send_request, "/media")
            for _ in range(content_rps):
                executor.submit(send_request, "/content")

            if total_rps_target > 0 and idx % 10 == 0:
                print(f"[{idx+1}/{DURATION}] [{row['datetime']}] Dispatching target RPS: {total_rps_target} (Media: {media_rps}, Content: {content_rps})")

            # Sleep to maintain 1-second boundary
            elapsed = time.time() - cycle_start
            sleep_time = 1.0 - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    end_ts = int(time.time())
    print(f"\n=== Test Completed ===")
    print(f"End Epoch Timestamp: {end_ts}")
    print(f"Total Run Duration: {end_ts - start_ts} seconds")
    print(f"Final Statistics: {dict(total_stats)}")
    
    total_dispatched = sum(total_stats.values())
    success_requests = total_stats.get("/media_200", 0) + total_stats.get("/content_200", 0)
    success_rate = (success_requests / total_dispatched * 100) if total_dispatched > 0 else 100
    print(f"Total requests dispatched: {total_dispatched}")
    print(f"Success Rate: {success_rate:.2f}%")
    
    # Calculate and display P95 Latency
    def calculate_p95(latencies):
        if not latencies:
            return 0.0
        sorted_l = sorted(latencies)
        idx = int(len(sorted_l) * 0.95)
        idx = min(idx, len(sorted_l) - 1)
        return sorted_l[idx]
        
    p95_media = calculate_p95(media_latencies)
    p95_content = calculate_p95(content_latencies)
    print(f"P95 Latency Media Service: {p95_media:.2f} ms")
    print(f"P95 Latency Content Service: {p95_content:.2f} ms")

if __name__ == "__main__":
    main()
