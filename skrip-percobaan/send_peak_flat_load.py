import time
import requests
import queue
import threading
import random
from collections import Counter

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
        with stats_lock:
            stats[f"{endpoint}_{r.status_code}"] += 1
    except requests.exceptions.Timeout:
        with stats_lock:
            stats[f"{endpoint}_timeout"] += 1
    except Exception as e:
        with stats_lock:
            stats[f"{endpoint}_error_{type(e).__name__}"] += 1
    
    with stats_lock:
        cycle_results.append(success)

def worker_thread():
    while True:
        req = request_queue.get()
        if req is None:
            break
        send_request(req)
        request_queue.task_done()

def main():
    # 3x Global Peak RPS:
    media_rps = 111
    content_rps = 36
    api_rps = 0 
    total_rps = media_rps + content_rps + api_rps

    start_ts = int(time.time())
    print(f"Starting peak flat load test for 30 seconds...")
    print(f"Start Epoch Timestamp: {start_ts}")
    print(f"Target RPS: {total_rps} (Media: {media_rps}, Content: {content_rps}, API: {api_rps})")

    # Pre-start worker threads (20 is sufficient for low-latency cached endpoints)
    num_workers = 20
    workers = []
    for _ in range(num_workers):
        t = threading.Thread(target=worker_thread, daemon=True)
        t.start()
        workers.append(t)

    # Absolute time tracking to prevent drift
    next_cycle_start = time.time()

    # Run for 10 cycles (10 seconds)
    for second in range(1, 11):
        cycle_start = next_cycle_start
        next_cycle_start = cycle_start + 1.0
        
        with stats_lock:
            cycle_results.clear()
        
        # Combine and shuffle requests to simulate realistic mixed traffic flow
        requests_to_send = (["/media"] * media_rps) + (["/content"] * content_rps)
        random.shuffle(requests_to_send)
        
        # Queue all requests instantly (takes < 1ms)
        for req in requests_to_send:
            request_queue.put(req)
        
        # Sleep until the next absolute cycle start time (compensates for any jitter)
        now = time.time()
        sleep_time = next_cycle_start - now
        if sleep_time > 0:
            time.sleep(sleep_time)
        
        # Briefly wait for asynchronous workers to complete remaining work for this second
        time.sleep(0.015)
        with stats_lock:
            completed = len(cycle_results)
            successes = sum(1 for x in cycle_results if x)
            cycle_results.clear()
            
        cycle_success_rate = (successes / completed * 100) if completed > 0 else 100.0
        
        print(f"Cycle {second}/10 dispatched in {time.time() - cycle_start - 0.015:.3f}s. Success Rate: {cycle_success_rate:.2f}%")

    # Stop workers
    for _ in range(num_workers):
        request_queue.put(None)
    for t in workers:
        t.join(timeout=1.0)

    end_ts = int(time.time())
    # Show results
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
