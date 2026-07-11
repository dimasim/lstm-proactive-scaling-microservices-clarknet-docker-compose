import requests
import time
import numpy as np

PROM_URL = "http://localhost:9090"

def get_stats(query, duration_minutes=60):
    end_time = int(time.time())
    start_time = end_time - (duration_minutes * 60)
    
    url = f"{PROM_URL}/api/v1/query_range"
    params = {
        "query": query,
        "start": start_time,
        "end": end_time,
        "step": "10s"
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            result = r.json()
            if result.get("status") == "success" and len(result["data"]["result"]) > 0:
                values = [float(v[1]) for v in result["data"]["result"][0]["values"]]
                if values:
                    return min(values), max(values)
    except Exception as e:
        print(f"Error querying {query}: {e}")
    return 0.0, 0.0

def main():
    queries = {
        "cpu_media": 'sum(rate(container_cpu_usage_seconds_total{container_label_com_docker_compose_service=~"media-service.*"}[2s])) * 100',
        "cpu_content": 'sum(rate(container_cpu_usage_seconds_total{container_label_com_docker_compose_service=~"content-service.*"}[2s])) * 100',
        "ram_media": 'sum(container_memory_working_set_bytes{container_label_com_docker_compose_service=~"media-service.*"}) / 1024 / 1024',
        "ram_content": 'sum(container_memory_working_set_bytes{container_label_com_docker_compose_service=~"content-service.*"}) / 1024 / 1024',
    }
    
    print("Querying Prometheus for idle/peak statistics (last 1 hour)...")
    for key, q in queries.items():
        min_val, max_val = get_stats(q)
        print(f"{key} -> Min (Idle): {min_val:.2f}, Max (Peak): {max_val:.2f}")

if __name__ == "__main__":
    main()
