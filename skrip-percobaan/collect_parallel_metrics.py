import time
import requests
import csv
import sys
import os
import argparse
import string

PROM_URL = "http://localhost:9090"
DATASET_CSV = "dataset/aggregated_clarknet_rps_3x.csv"

def query_prometheus_range(query: str, start: int, end: int, step: str = "1s", retries: int = 3, timeout: int = 30):
    """Query Prometheus range API with retry logic and exponential backoff."""
    url = f"{PROM_URL}/api/v1/query_range"
    params = {
        "query": query,
        "start": start,
        "end": end,
        "step": step
    }
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                result = r.json()
                if result.get("status") == "success":
                    return result["data"]["result"]
                else:
                    print(f"    ⚠️  Prometheus returned status={result.get('status')}: {result.get('error', 'unknown')}")
            else:
                print(f"    ⚠️  HTTP {r.status_code} from Prometheus")
        except requests.exceptions.Timeout:
            print(f"    ⚠️  Timeout (attempt {attempt+1}/{retries}) for query chunk {start}-{end}")
        except Exception as e:
            print(f"    ⚠️  Error (attempt {attempt+1}/{retries}): {e}")
        
        if attempt < retries - 1:
            wait = 2 ** attempt  # exponential backoff: 1s, 2s, 4s
            print(f"    ⏳ Retrying in {wait}s...")
            time.sleep(wait)
    
    print(f"    ❌ All {retries} attempts failed for chunk {start}-{end}")
    return []

def collect_set_metrics(suffix, start_ts, end_ts, duration, dataset_start_idx):
    output_filename = f"collected_metrics_{suffix}.csv"
    print(f"\n--- Collecting metrics for Set {suffix.upper()} into {output_filename} ---")

    queries = {
        "rps_media": f'sum(sent_rps_media{{job="load-generator-{suffix}"}})',
        "rps_content": f'sum(sent_rps_content{{job="load-generator-{suffix}"}})',
        "cpu_media": f'sum(rate(container_cpu_usage_seconds_total{{container_label_com_docker_compose_service="media-service-{suffix}"}}[5s])) * 100',
        "cpu_content": f'sum(rate(container_cpu_usage_seconds_total{{container_label_com_docker_compose_service="content-service-{suffix}"}}[5s])) * 100',
        "ram_media": f'sum(container_memory_working_set_bytes{{container_label_com_docker_compose_service="media-service-{suffix}"}}) / 1024 / 1024',
        "ram_content": f'sum(container_memory_working_set_bytes{{container_label_com_docker_compose_service="content-service-{suffix}"}}) / 1024 / 1024',
        "replicas_media": f'count(container_last_seen{{container_label_com_docker_compose_service="media-service-{suffix}"}} > time() - 15)',
        "replicas_content": f'count(container_last_seen{{container_label_com_docker_compose_service="content-service-{suffix}"}} > time() - 15)',
        "latency_media": f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{job="media-service-{suffix}"}}[5s])) by (le)) * 1000',
        "latency_content": f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{job="content-service-{suffix}"}}[5s])) by (le)) * 1000'
    }

    series_data = {}
    query_stats = {}  # Track query success/failure per metric

    for key, q in queries.items():
        print(f"  - Querying {key}...")
        combined_values = []
        seen_timestamps = set()  # Fix Bug #4: Deduplication
        chunk_size = 7200
        curr_start = start_ts
        total_chunks = (end_ts - start_ts + chunk_size - 1) // chunk_size
        chunk_num = 0
        chunks_failed = 0
        chunks_succeeded = 0

        while curr_start < end_ts:
            # Fix Bug #3: Use exclusive end to avoid boundary overlap
            curr_end = min(curr_start + chunk_size - 1, end_ts)
            chunk_num += 1

            # Progress logging
            if chunk_num % 10 == 0 or chunk_num == 1 or chunk_num == total_chunks:
                print(f"    📊 Chunk {chunk_num}/{total_chunks} ({chunk_num/total_chunks*100:.0f}%)")

            results = query_prometheus_range(q, curr_start, curr_end, "1s")
            if results and len(results) > 0:
                for val in results[0].get("values", []):
                    ts = int(val[0])
                    # Fix Bug #4: Deduplicate timestamps
                    if ts not in seen_timestamps:
                        seen_timestamps.add(ts)
                        combined_values.append(val)
                chunks_succeeded += 1
            else:
                chunks_failed += 1

            # Fix Bug #3: Move to next non-overlapping chunk
            curr_start = curr_end + 1
            
        # Track stats
        query_stats[key] = {
            "total_chunks": chunk_num,
            "succeeded": chunks_succeeded,
            "failed": chunks_failed,
            "data_points": len(combined_values),
            "expected_points": duration,
        }

        series_data[key] = [0.0] * duration
        for val in combined_values:
            ts = int(val[0])
            try:
                val_float = float(val[1])
            except ValueError:
                val_float = 0.0
            
            # Compensate for the 1-second Prometheus scrape delay / phase shift
            idx = ts - start_ts - 1
            if 0 <= idx < duration:
                series_data[key][idx] = val_float

    # Fix Bug #5: Freeze detection BEFORE writing CSV
    print(f"\n  🔍 Freeze Detection for Set {suffix.upper()}:")
    freeze_found = False
    for key in series_data:
        values = series_data[key]
        streak = 0
        freeze_periods = []
        for i in range(1, len(values)):
            if values[i] == values[i-1]:
                streak += 1
            else:
                if streak >= 30:
                    freeze_periods.append({
                        "start_idx": i - streak,
                        "end_idx": i - 1,
                        "duration": streak,
                        "value": values[i-1]
                    })
                streak = 0
        # Check last streak
        if streak >= 30:
            freeze_periods.append({
                "start_idx": len(values) - streak,
                "end_idx": len(values) - 1,
                "duration": streak,
                "value": values[-1]
            })
        
        if freeze_periods:
            freeze_found = True
            total_frozen = sum(f["duration"] for f in freeze_periods)
            pct = total_frozen / len(values) * 100
            print(f"    ⚠️  FREEZE in {key}: {len(freeze_periods)} periods, "
                  f"{total_frozen}s total ({pct:.2f}%)")
            for fp in freeze_periods[:3]:  # show first 3
                print(f"        Row {fp['start_idx']}-{fp['end_idx']} ({fp['duration']}s) "
                      f"stuck at {fp['value']}")
            if len(freeze_periods) > 3:
                print(f"        ... and {len(freeze_periods) - 3} more")
    
    if not freeze_found:
        print(f"    ✅ No freeze patterns detected!")

    # Fix Bug #5: Query success validation
    print(f"\n  📊 Query Stats for Set {suffix.upper()}:")
    for key, stats in query_stats.items():
        coverage = stats["data_points"] / stats["expected_points"] * 100 if stats["expected_points"] > 0 else 0
        status = "✅" if coverage > 95 else ("⚠️" if coverage > 50 else "❌")
        print(f"    {status} {key}: {stats['data_points']}/{stats['expected_points']} points "
              f"({coverage:.1f}%), {stats['failed']} chunks failed")

    # Write CSV
    with open(output_filename, mode='w', encoding='utf-8', newline='') as f:
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

    print(f"\n  ✅ Wrote {duration} rows to {output_filename}")

    # Compare with dataset
    print(f"  Reading original datasets to compare...")
    orig_media_rps = []
    orig_content_rps = []
    
    rows = []
    csv_path_w1 = "dataset/aggregated_clarknet_rps_3x.csv"
    csv_path_w2 = "dataset/aggregated_clarknet_rps_week2_3x.csv"
    with open(csv_path_w1, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    with open(csv_path_w2, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    for idx in range(dataset_start_idx, dataset_start_idx + duration):
        if idx < len(rows):
            orig_media_rps.append(int(rows[idx].get("Media_Service", 0)))
            orig_content_rps.append(int(rows[idx].get("Content_Service", 0)))
        else:
            orig_media_rps.append(0)
            orig_content_rps.append(0)

    prom_media = series_data["rps_media"]
    prom_content = series_data["rps_content"]

    sum_orig_media = sum(orig_media_rps)
    sum_prom_media = sum(prom_media)
    sum_orig_content = sum(orig_content_rps)
    sum_prom_content = sum(prom_content)

    print(f"=== Set {suffix.upper()} Workload Comparison ===")
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

def main():
    parser = argparse.ArgumentParser(
        description="Collect metrics from Prometheus for parallel load test sets",
        usage="python3 collect_parallel_metrics.py <start_ts> <end_ts> [options]"
    )
    parser.add_argument("start_ts", type=int, help="Start Unix timestamp")
    parser.add_argument("end_ts", type=int, help="End Unix timestamp")
    parser.add_argument("--sets", type=str, default="a,b,c",
                        help="Comma-separated set suffixes (default: a,b,c)")
    parser.add_argument("--start-indices", type=str, default=None,
                        help="Comma-separated dataset start indices for each set")
    
    # Legacy positional args support (backward compatible)
    parser.add_argument("legacy_indices", nargs="*", type=int,
                        help=argparse.SUPPRESS)
    
    args = parser.parse_args()
    
    start_ts = args.start_ts
    end_ts = args.end_ts
    duration = end_ts - start_ts
    
    suffixes = args.sets.split(",")
    
    # Handle start indices - either from --start-indices or legacy positional args
    if args.start_indices:
        start_indices = [int(x) for x in args.start_indices.split(",")]
    elif args.legacy_indices:
        start_indices = args.legacy_indices
    else:
        # Default: evenly spaced
        total_rows = 1209425  # default total
        chunk = total_rows // len(suffixes)
        start_indices = [i * chunk for i in range(len(suffixes))]
    
    if len(suffixes) != len(start_indices):
        print(f"❌ Error: {len(suffixes)} sets but {len(start_indices)} start indices")
        return
    
    print(f"📊 Collecting metrics for {len(suffixes)} sets: {', '.join(s.upper() for s in suffixes)}")
    print(f"⏱️  Duration: {duration}s ({duration/3600:.1f}h)")
    print(f"📅 Timestamp range: {start_ts} - {end_ts}")
    
    for suffix, dataset_start_idx in zip(suffixes, start_indices):
        collect_set_metrics(suffix, start_ts, end_ts, duration, dataset_start_idx)
    
    print("\n✅ All parallel CSV extractions completed successfully!")

if __name__ == "__main__":
    main()
