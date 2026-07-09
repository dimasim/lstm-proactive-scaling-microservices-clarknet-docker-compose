import time
import requests
import queue
import threading
import random
from collections import Counter

BASE_URL = "http://localhost:8000"

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=500, pool_maxsize=500)
session.mount('http://', adapter)
session.mount('https://', adapter)

stats_lock = threading.Lock()
stats = Counter()
cycle_results = []

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
    # Pre-start worker threads (100 is safe for up to 200 total RPS)
    num_workers = 100
    workers = []
    for _ in range(num_workers):
        t = threading.Thread(target=worker_thread, daemon=True)
        t.start()
        workers.append(t)

    # Define steps dynamically: 5 to 100 RPS in steps of 5, each for 1 second
    steps = [(i, i, 1) for i in range(5, 101, 5)]

    start_ts = int(time.time())
    print("Starting step load test...")
    print(f"Start Epoch Timestamp: {start_ts}")

    next_cycle_start = time.time()
    second_idx = 1

    for step_idx, (media_rps, content_rps, dur) in enumerate(steps):
        total_rps = media_rps + content_rps
        print(f"\n--- Step {step_idx+1}: Target RPS {total_rps} (Media: {media_rps}, Content: {content_rps}) for {dur}s ---")
        for _ in range(dur):
            cycle_start = next_cycle_start
            next_cycle_start = cycle_start + 1.0
            
            with stats_lock:
                cycle_results.clear()
            
            requests_to_send = (["/media"] * media_rps) + (["/content"] * content_rps)
            random.shuffle(requests_to_send)
            
            for req in requests_to_send:
                request_queue.put(req)
            
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
                
            success_rate = (successes / completed * 100) if completed > 0 else 100.0
            print(f"Second {second_idx} (Target: {total_rps}) -> Dispatched in {time.time() - cycle_start - 0.015:.3f}s. Success Rate: {success_rate:.2f}%")
            second_idx += 1

    # Stop workers
    for _ in range(num_workers):
        request_queue.put(None)
    for t in workers:
        t.join(timeout=1.0)

    end_ts = int(time.time())
    print(f"\n=== Test Completed ===")
    print(f"End Epoch Timestamp: {end_ts}")

if __name__ == "__main__":
    main()
