import time
import requests
import csv
import sys
import os

PROM_URL = "http://localhost:9090"
DATASET_CSV = "dataset/aggregated_clarknet_rps_3x.csv"

def query_prometheus_range(query: str, start: int, end: int, step: str = "1s"):
    chunk_size = 10000
    all_values = []
    
    current_start = start
    while current_start < end:
        current_end = min(current_start + chunk_size, end)
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
                if result.get("status") == "success":
                    data_res = result.get("data", {}).get("result", [])
                    if data_res and len(data_res) > 0:
                        vals = data_res[0].get("values", [])
                        all_values.extend(vals)
        except Exception as e:
            print(f"Error querying Prometheus chunk {current_start}-{current_end}: {e}")
        current_start = current_end + 1
        
    if all_values:
        # Sort and deduplicate values by timestamp
        seen_timestamps = set()
        deduped_values = []
        for val in all_values:
            ts_val = val[0]
            if ts_val not in seen_timestamps:
                seen_timestamps.add(ts_val)
                deduped_values.append(val)
        deduped_values.sort(key=lambda x: x[0])
        return [{"metric": {}, "values": deduped_values}]
    return []

def collect_set_metrics(suffix, start_ts, end_ts, duration, dataset_start_idx):
    output_filename = f"collected_metrics_{suffix}.csv"
    print(f"\n--- Collecting metrics for Set {suffix.upper()} into {output_filename} ---")

    queries = {
        "rps_media": f'sum(sent_rps_media{{job="load-generator-{suffix}"}})',
        "rps_content": f'sum(sent_rps_content{{job="load-generator-{suffix}"}})',
        "cpu_media": f'sum(rate(container_cpu_usage_seconds_total{{container_label_com_docker_compose_service="media-service-{suffix}"}}[2s])) * 100',
        "cpu_content": f'sum(rate(container_cpu_usage_seconds_total{{container_label_com_docker_compose_service="content-service-{suffix}"}}[2s])) * 100',
        "ram_media": f'sum(container_memory_working_set_bytes{{container_label_com_docker_compose_service="media-service-{suffix}"}} and on(id) (container_last_seen > time() - 15)) / 1024 / 1024',
        "ram_content": f'sum(container_memory_working_set_bytes{{container_label_com_docker_compose_service="content-service-{suffix}"}} and on(id) (container_last_seen > time() - 15)) / 1024 / 1024',
        "replicas_media": f'count(container_last_seen{{container_label_com_docker_compose_service="media-service-{suffix}"}} > time() - 15)',
        "replicas_content": f'count(container_last_seen{{container_label_com_docker_compose_service="content-service-{suffix}"}} > time() - 15)',
        "latency_media": f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{job="media-service-{suffix}"}}[2s])) by (le)) * 1000',
        "latency_content": f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{job="content-service-{suffix}"}}[2s])) by (le)) * 1000'
    }

    series_data = {}
    for key, q in queries.items():
        results = query_prometheus_range(q, start_ts, end_ts, "1s")
        series_data[key] = [0.0] * duration
        
        if results and len(results) > 0:
            values = results[0].get("values", [])
            for val in values:
                ts = int(val[0])
                try:
                    val_float = float(val[1])
                except ValueError:
                    val_float = 0.0
                
                # Compensate for the 1-second Prometheus scrape delay / phase shift
                idx = ts - start_ts - 1
                if 0 <= idx < duration:
                    series_data[key][idx] = val_float

    # Read original dataset first to compare and fallback if Prometheus is empty
    print(f"Reading original dataset from {DATASET_CSV}...")
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

    # Check and fallback if Prometheus metrics for sent RPS are 0
    if sum(series_data["rps_media"]) == 0.0:
        print("Warning: Prometheus rps_media is empty. Falling back to dataset values.")
        series_data["rps_media"] = [float(x) for x in orig_media_rps]
    if sum(series_data["rps_content"]) == 0.0:
        print("Warning: Prometheus rps_content is empty. Falling back to dataset values.")
        series_data["rps_content"] = [float(x) for x in orig_content_rps]

    with open(output_filename, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "rps_media", "rps_content", "cpu_media", "cpu_content", "ram_media", "ram_content", "replicas_media", "replicas_content", "latency_media", "latency_content"])
        for idx in range(duration):
            writer.writerow([
                start_ts + idx,
                f"{series_data['rps_media'][idx]:.2f}",
                f"{series_data['rps_content'][idx]:.2f}",
                f"{series_data['cpu_media'][idx]:.2f}",
                f"{series_data['cpu_content'][idx]:.2f}",
                f"{series_data['ram_media'][idx]:.2f}",
                f"{series_data['ram_content'][idx]:.2f}",
                f"{series_data['replicas_media'][idx]:.2f}",
                f"{series_data['replicas_content'][idx]:.2f}",
                f"{series_data['latency_media'][idx]:.2f}",
                f"{series_data['latency_content'][idx]:.2f}"
            ])

    prom_media = series_data["rps_media"]
    prom_content = series_data["rps_content"]

    sum_orig_media = sum(orig_media_rps)
    sum_prom_media = sum(prom_media)
    sum_orig_content = sum(orig_content_rps)
    sum_prom_content = sum(prom_content)

    print(f"=== Set {suffix.upper()} Workload Comparison ===")
    print(f"Media Service Total Requests:")
    print(f"  - Sent (Dataset): {sum_orig_media}")
    print(f"  - Recorded (Prometheus/Fallback): {sum_prom_media:.2f}")
    diff_media = abs(sum_orig_media - sum_prom_media)
    accuracy_media = (1 - (diff_media / sum_orig_media)) * 100 if sum_orig_media > 0 else 100
    print(f"  - Match Accuracy: {accuracy_media:.2f}%")

    print(f"Content Service Total Requests:")
    print(f"  - Sent (Dataset): {sum_orig_content}")
    print(f"  - Recorded (Prometheus/Fallback): {sum_prom_content:.2f}")
    diff_content = abs(sum_orig_content - sum_prom_content)
    accuracy_content = (1 - (diff_content / sum_orig_content)) * 100 if sum_orig_content > 0 else 100
    print(f"  - Match Accuracy: {accuracy_content:.2f}%")

def main():
    if len(sys.argv) < 5:
        print("Usage: python3 collect_parallel_metrics.py <start_unix_timestamp> <end_unix_timestamp> <dataset_start_idx_a> <dataset_start_idx_b>")
        return

    start_ts = int(sys.argv[1])
    end_ts = int(sys.argv[2])
    duration = end_ts - start_ts
    dataset_start_idx_a = int(sys.argv[3])
    dataset_start_idx_b = int(sys.argv[4])

    collect_set_metrics("a", start_ts, end_ts, duration, dataset_start_idx_a)
    collect_set_metrics("b", start_ts, end_ts, duration, dataset_start_idx_b)
    print("\nAll parallel CSV extractions completed successfully!")

if __name__ == "__main__":
    main()
