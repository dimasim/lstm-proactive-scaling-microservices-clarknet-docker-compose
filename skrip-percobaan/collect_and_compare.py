import time
import requests
import csv
import sys
import numpy as np

PROM_URL = "http://localhost:9090"
DATASET_CSV = "dataset/aggregated_clarknet_rps_3x.csv"
OUTPUT_CSV = "collected_metrics.csv"

def query_prometheus_range(query: str, start: int, end: int, step: str = "1s"):
    # Prometheus limits query range to 11,000 data points.
    # We query in chunks of 2 hours (7200 seconds) to bypass this limit.
    chunk_size = 7200
    all_values = []
    
    current_start = start
    while current_start < end:
        current_end = min(end, current_start + chunk_size)
        url = f"{PROM_URL}/api/v1/query_range"
        params = {
            "query": query,
            "start": current_start,
            "end": current_end,
            "step": step
        }
        try:
            r = requests.get(url, params=params, timeout=15)
            if r.status_code == 200:
                result = r.json()
                if result.get("status") == "success" and result["data"]["result"]:
                    # Append values from this chunk
                    all_values.extend(result["data"]["result"][0].get("values", []))
        except Exception as e:
            print(f"Error querying Prometheus chunk ({current_start} - {current_end}): {e}")
        
        current_start = current_end
        # Sleep briefly to avoid hammering Prometheus
        time.sleep(0.1)
        
    if all_values:
        return [{"values": all_values}]
    return []

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 collect_and_compare.py <start_unix_timestamp> <end_unix_timestamp> [dataset_start_index]")
        return

    start_ts = int(sys.argv[1])
    end_ts = int(sys.argv[2])
    duration = end_ts - start_ts
    dataset_start_idx = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    print(f"Collecting Prometheus metrics from {start_ts} to {end_ts} (Duration: {duration}s)...")

    # Queries
    queries = {
        "rps_media": 'sum(sent_rps_media)',
        "rps_content": 'sum(sent_rps_content)',
        "cpu_media": 'sum(rate(container_cpu_usage_seconds_total{container_label_com_docker_compose_service="media-service"}[2s])) * 100',
        "cpu_content": 'sum(rate(container_cpu_usage_seconds_total{container_label_com_docker_compose_service="content-service"}[2s])) * 100',
        "ram_media": 'sum(container_memory_working_set_bytes{container_label_com_docker_compose_service="media-service"}) / 1024 / 1024',
        "ram_content": 'sum(container_memory_working_set_bytes{container_label_com_docker_compose_service="content-service"}) / 1024 / 1024',
        "replicas_media": 'count(container_last_seen{container_label_com_docker_compose_service="media-service"} > time() - 15)',
        "replicas_content": 'count(container_last_seen{container_label_com_docker_compose_service="content-service"} > time() - 15)',
        "latency_media": 'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="media-service"}[2s])) by (le)) * 1000',
        "latency_content": 'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="content-service"}[2s])) by (le)) * 1000'
    }

    # Gather data points
    series_data = {}
    for key, q in queries.items():
        print(f"Querying series: {key}...")
        results = query_prometheus_range(q, start_ts, end_ts, "1s")
        
        # Initialize list
        series_data[key] = [0.0] * duration
        
        if results and len(results) > 0:
            values = results[0].get("values", [])
            for val in values:
                ts = int(val[0])
                try:
                    val_float = float(val[1])
                except ValueError:
                    val_float = 0.0
                
                idx = ts - start_ts
                if 0 <= idx < duration:
                    series_data[key][idx] = val_float

    # Write to collected_metrics.csv
    print(f"Writing metrics to {OUTPUT_CSV}...")
    with open(OUTPUT_CSV, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "rps_media", "rps_content", "cpu_media", "cpu_content", "ram_media", "ram_content", "replicas_media", "replicas_content", "latency_media", "latency_content"])
        for idx in range(duration):
            writer.writerow([
                start_ts + idx,
                series_data["rps_media"][idx],
                series_data["rps_content"][idx],
                series_data["cpu_media"][idx],
                series_data["cpu_content"][idx],
                series_data["ram_media"][idx],
                series_data["ram_content"][idx],
                series_data["replicas_media"][idx],
                series_data["replicas_content"][idx],
                series_data["latency_media"][idx],
                series_data["latency_content"][idx]
            ])

    # Compare with dataset
    print(f"Reading original dataset from {DATASET_CSV} to compare...")
    orig_media_rps = []
    orig_content_rps = []
    
    with open(DATASET_CSV, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        count = 0
        for idx, row in enumerate(reader):
            if idx < dataset_start_idx:
                continue
            if count >= duration:
                break
            orig_media_rps.append(int(row.get("Media_Service", 0)))
            orig_content_rps.append(int(row.get("Content_Service", 0)))
            count += 1

    # Print Comparison Statistics
    print("\n=== Workload Comparison Statistics ===")
    
    prom_media = series_data["rps_media"]
    prom_content = series_data["rps_content"]

    # Calculate basic correlation or differences
    # Because Prometheus scrape times and idelta queries might have a 1-2 second phase shift/latency,
    # comparing total sums is the most robust way to check correctness.
    sum_orig_media = sum(orig_media_rps)
    sum_prom_media = sum(prom_media)
    sum_orig_content = sum(orig_content_rps)
    sum_prom_content = sum(prom_content)

    print(f"Media Service Total Requests:")
    print(f"  - Sent (Dataset): {sum_orig_media}")
    print(f"  - Recorded (Prometheus): {sum_prom_media:.2f}")
    diff_media = abs(sum_orig_media - sum_prom_media)
    accuracy_media = (1 - (diff_media / sum_orig_media)) * 100 if sum_orig_media > 0 else 100
    print(f"  - Match Accuracy: {accuracy_media:.2f}%")

    print(f"Content Service Total Requests:")
    print(f"  - Sent (Dataset): {sum_orig_content}")
    print(f"  - Recorded (Prometheus): {sum_prom_content:.2f}")
    diff_content = abs(sum_orig_content - sum_prom_content)
    accuracy_content = (1 - (diff_content / sum_orig_content)) * 100 if sum_orig_content > 0 else 100
    print(f"  - Match Accuracy: {accuracy_content:.2f}%")

    print("\nCSV extraction completed successfully!")

if __name__ == "__main__":
    main()
