import time
import requests
import concurrent.futures
import threading
from collections import Counter

BASE_URL = "http://localhost:8000"

# Use Session to pool connections
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

def main():
    # Peak RPS stats:
    media_rps = 37
    content_rps = 12
    api_rps = 0 
    total_rps = media_rps + content_rps + api_rps

    print(f"Starting peak flat load test for 30 seconds...")
    print(f"Target RPS: {total_rps} (Media: {media_rps}, Content: {content_rps}, API: {api_rps})")

    # Run for 30 cycles (30 seconds)
    with concurrent.futures.ThreadPoolExecutor(max_workers=total_rps * 2) as executor:
        for second in range(1, 31):
            start_time = time.time()
            
            # Submit media requests
            for _ in range(media_rps):
                executor.submit(send_request, "/media")
            
            # Submit content requests
            for _ in range(content_rps):
                executor.submit(send_request, "/content")
            
            # Wait for the remainder of the second
            elapsed = time.time() - start_time
            sleep_time = 1.0 - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            print(f"Cycle {second}/10 dispatched.")

    # Show results
    with stats_lock:
        print("\n=== Test Results ===")
        for key, value in stats.items():
            print(f"{key}: {value} requests")
        total_requests = sum(stats.values())
        success_requests = stats["/media_200"] + stats["/content_200"] + stats["/api_200"]
        success_rate = (success_requests / total_requests) * 100 if total_requests > 0 else 0
        print(f"Total requests dispatched: {total_requests}")
        print(f"Success Rate: {success_rate:.2f}%")

if __name__ == "__main__":
    main()
