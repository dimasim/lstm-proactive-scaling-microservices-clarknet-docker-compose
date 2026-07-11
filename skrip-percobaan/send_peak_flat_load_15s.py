import time
import requests
import queue
import threading
import random
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
    media_rps = 111
    content_rps = 36
    total_rps = media_rps + content_rps

    # Clear stats
    stats.clear()
    cycle_results.clear()

    # Pre-start worker threads
    num_workers = 30
    workers = []
    for _ in range(num_workers):
        t = threading.Thread(target=worker_thread, daemon=True)
        t.start()
        workers.append(t)

    print(f"\nStarting peak load test (Media: {media_rps} RPS, Content: {content_rps} RPS) for 15 seconds...")
    start_ts = int(time.time())

    next_cycle_start = time.time()
    for second in range(1, 16):
        cycle_start = next_cycle_start
        next_cycle_start = cycle_start + 1.0
        
        GAUGE_MEDIA.set(media_rps)
        GAUGE_CONTENT.set(content_rps)
        
        requests_to_send = (["/media"] * media_rps) + (["/content"] * content_rps)
        random.shuffle(requests_to_send)
        
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
        
        now = time.time()
        sleep_time = next_cycle_start - now
        if sleep_time > 0:
            time.sleep(sleep_time)
            
        time.sleep(0.015)
        print(f"Cycle {second}/15 dispatched.")

    # Stop workers
    for _ in range(num_workers):
        request_queue.put(None)
    for t in workers:
        t.join(timeout=1.0)

    GAUGE_MEDIA.set(0.0)
    GAUGE_CONTENT.set(0.0)
    end_ts = int(time.time())
    
    print("Waiting 5 seconds for Prometheus metrics to aggregate...")
    time.sleep(5)
    
    # Query Prometheus for the test range metrics
    print("\nQuerying Prometheus for peak CPU/RAM metrics during test window...")
    
    queries = {
        "cpu_media": 'sum(rate(container_cpu_usage_seconds_total{container_label_com_docker_compose_service=~"media-service.*"}[2s])) * 100',
        "cpu_content": 'sum(rate(container_cpu_usage_seconds_total{container_label_com_docker_compose_service=~"content-service.*"}[2s])) * 100',
        "ram_media": 'sum(container_memory_working_set_bytes{container_label_com_docker_compose_service=~"media-service.*"} and on(id) (container_last_seen > time() - 15)) / 1024 / 1024',
        "ram_content": 'sum(container_memory_working_set_bytes{container_label_com_docker_compose_service=~"content-service.*"} and on(id) (container_last_seen > time() - 15)) / 1024 / 1024',
    }
    
    url = "http://localhost:9090/api/v1/query_range"
    for key, q in queries.items():
        params = {
            "query": q,
            "start": start_ts,
            "end": end_ts,
            "step": "1s"
        }
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                result = r.json()
                if result.get("status") == "success" and len(result["data"]["result"]) > 0:
                    values = [float(v[1]) for v in result["data"]["result"][0]["values"]]
                    if values:
                        print(f"  - {key}: Min={min(values):.2f}, Max={max(values):.2f}, Avg={sum(values)/len(values):.2f}")
                    else:
                        print(f"  - {key}: No values found in window")
                else:
                    print(f"  - {key}: Query failed")
        except Exception as e:
            print(f"  - {key}: Error querying Prometheus: {e}")

if __name__ == "__main__":
    main()
