import time
import csv
import os
import requests
import concurrent.futures
import threading
from collections import Counter

BASE_URL = "http://localhost:8000"
CSV_PATH = "dataset/aggregated_clarknet_rps.csv"

# Use Session to pool connections and avoid connection churn/exhaustion
session = requests.Session()

# Mutex and counters for statistics
stats_lock = threading.Lock()
stats = Counter()

def send_request(endpoint: str):
    try:
        r = session.get(f"{BASE_URL}{endpoint}", timeout=1.5)
        with stats_lock:
            stats[f"{endpoint}_{r.status_code}"] += 1
    except requests.exceptions.Timeout:
        with stats_lock:
            stats[f"{endpoint}_timeout"] += 1
    except Exception as e:
        with stats_lock:
            stats[f"{endpoint}_error_{type(e).__name__}"] += 1

def report_stats():
    global stats
    while True:
        time.sleep(5)
        with stats_lock:
            current_stats = dict(stats)
            stats.clear()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Last 5s Activity: {current_stats}")

def main():
    if not os.path.exists(CSV_PATH):
        print(f"Error: Dataset CSV not found at {CSV_PATH}")
        return

    print("Starting background reporter...")
    reporter = threading.Thread(target=report_stats, daemon=True)
    reporter.start()

    # Pre-create a large thread pool to handle concurrent requests
    # Set max_workers high enough to handle spikes without blocking
    with concurrent.futures.ThreadPoolExecutor(max_workers=500) as executor:
        print(f"Reading Clarknet dataset from {CSV_PATH}...")
        with open(CSV_PATH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                start_time = time.time()
                
                # Parse RPS for each type of service
                try:
                    content_rps = int(row.get("Content_Service", 0))
                    media_rps = int(row.get("Media_Service", 0))
                    dynamic_rps = int(row.get("DynamicAPI_Service", 0))
                    others_rps = int(row.get("Others", 0))
                except ValueError:
                    # Skip header errors or malformed lines
                    continue

                # Group dynamic/others into /api endpoint
                api_rps = dynamic_rps + others_rps
                total_rps_target = content_rps + media_rps + api_rps

                # Submit requests concurrently
                # /media -> media-service
                for _ in range(media_rps):
                    executor.submit(send_request, "/media")

                # /content -> content-service (static)
                for _ in range(content_rps):
                    executor.submit(send_request, "/content")

                # /api -> content-service (CPU-bound)
                for _ in range(api_rps):
                    executor.submit(send_request, "/api")

                # Print target rps for this second
                if total_rps_target > 0:
                    print(f"[{row['datetime']}] Dispatching target RPS: {total_rps_target} (Media: {media_rps}, Content: {content_rps}, API: {api_rps})")

                # Sleep to maintain 1-second interval
                elapsed = time.time() - start_time
                sleep_time = 1.0 - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

if __name__ == "__main__":
    main()
