#!/usr/bin/env python3
"""
Split the combined Clarknet dataset into N non-overlapping sets for parallel collection.

Usage:
    python3 split_dataset.py --total-sets 8
    python3 split_dataset.py --total-sets 8 --server-id 1 --sets-per-server 4
    python3 split_dataset.py --total-sets 8 --server-id 2 --sets-per-server 4

Output:
    Prints the start_idx and duration for each set, and optionally generates
    dataset slice CSVs for verification.
"""

import argparse
import csv
import string
import os
import math


def get_suffix(index):
    """Get alphabetic suffix: 0->a, 1->b, ..., 25->z"""
    return string.ascii_lowercase[index]


def count_total_rows(start_offset=0):
    """Count total rows across both week datasets, subtracting the start_offset."""
    csv_w1 = "dataset/aggregated_clarknet_rps_3x.csv"
    csv_w2 = "dataset/aggregated_clarknet_rps_week2_3x.csv"
    
    count = 0
    for csv_path in [csv_w1, csv_w2]:
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # skip header
                count += sum(1 for _ in reader)
        else:
            print(f"⚠️  Warning: {csv_path} not found")
    
    if start_offset > count:
        print(f"⚠️  Error: start_offset ({start_offset}) is greater than total rows ({count})")
        return 0
        
    return count - start_offset


def split_dataset(total_rows, total_sets, start_offset=0):
    """Split total_rows into total_sets non-overlapping ranges."""
    base_size = total_rows // total_sets
    remainder = total_rows % total_sets
    
    splits = []
    current_idx = start_offset
    
    for i in range(total_sets):
        # Distribute remainder evenly across first 'remainder' sets
        size = base_size + (1 if i < remainder else 0)
        splits.append({
            "set": get_suffix(i),
            "start_idx": current_idx,
            "duration": size,
            "end_idx": current_idx + size - 1,
            "day_start": current_idx / 86400,
            "day_end": (current_idx + size) / 86400,
        })
        current_idx += size
    
    return splits


def generate_slice_csv(splits, output_dir="."):
    """Generate individual dataset slice CSVs for each set."""
    csv_w1 = "dataset/aggregated_clarknet_rps_3x.csv"
    csv_w2 = "dataset/aggregated_clarknet_rps_week2_3x.csv"
    
    # Load all rows
    rows = []
    for csv_path in [csv_w1, csv_w2]:
        if os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(row)
    
    for split in splits:
        suffix = split["set"]
        start = split["start_idx"]
        duration = split["duration"]
        
        output_file = f"{output_dir}/dataset_slice_{suffix}.csv"
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Media_Service", "Content_Service"])
            for idx in range(start, start + duration):
                if idx < len(rows):
                    writer.writerow([rows[idx]["Media_Service"], rows[idx]["Content_Service"]])
                else:
                    writer.writerow([0, 0])
        
        print(f"  ✅ Generated {output_file} ({duration} rows)")


def main():
    parser = argparse.ArgumentParser(description="Split Clarknet dataset into N non-overlapping sets")
    parser.add_argument("--total-sets", type=int, required=True, help="Total number of parallel sets across all servers")
    parser.add_argument("--server-id", type=int, default=None, help="Show only sets for this server (1-based)")
    parser.add_argument("--sets-per-server", type=int, default=None, help="Number of sets per server")
    parser.add_argument("--generate-slices", action="store_true", help="Generate individual dataset slice CSVs")
    parser.add_argument("--output-dir", type=str, default=".", help="Output directory for slice CSVs")
    parser.add_argument("--start-offset", type=int, default=0, help="Row index to start processing from (e.g., 518307 for last day of week 1)")
    args = parser.parse_args()
    
    total_rows = count_total_rows(args.start_offset)
    
    if args.start_offset > 0:
        print(f"📊 Processing starting from offset: {args.start_offset}")
    
    print(f"📊 Dataset rows to process: {total_rows} rows ({total_rows/86400:.1f} days)")
    print()
    
    splits = split_dataset(total_rows, args.total_sets, args.start_offset)
    
    # Filter for specific server if requested
    if args.server_id is not None and args.sets_per_server is not None:
        server_start = (args.server_id - 1) * args.sets_per_server
        server_end = server_start + args.sets_per_server
        server_splits = splits[server_start:server_end]
    else:
        server_splits = splits
    
    # Print table
    print(f"{'Set':<5} {'Start Index':>12} {'Duration':>10} {'End Index':>12} {'Day Range':<15} {'Real Time':<15}")
    print("-" * 75)
    
    for s in server_splits:
        hours = s["duration"] / 3600
        print(f"  {s['set'].upper():<3} {s['start_idx']:>12,} {s['duration']:>10,} {s['end_idx']:>12,} "
              f"Day {s['day_start']:.1f}-{s['day_end']:.1f}  {hours:.1f}h ({hours/24:.1f}d)")
    
    print()
    total_duration = sum(s["duration"] for s in server_splits)
    max_duration = max(s["duration"] for s in server_splits)
    print(f"📈 Total rows for this server: {total_duration:,}")
    print(f"⏱️  Real-time to complete (all parallel): {max_duration/3600:.1f}h ({max_duration/86400:.1f}d)")
    
    # Print command-line args for run_parallel_k6.py
    print()
    suffixes = ",".join(s["set"] for s in server_splits)
    start_indices = " ".join(str(s["start_idx"]) for s in server_splits)
    duration = server_splits[0]["duration"]  # all should be same (±1)
    
    print(f"📋 Run command:")
    print(f"  python3 skrip-percobaan/run_parallel_k6.py {duration} --sets {suffixes} --start-indices {start_indices}")
    
    if args.generate_slices:
        print(f"\n📦 Generating slice CSVs...")
        generate_slice_csv(server_splits, args.output_dir)
    
    # Print command for collect
    print(f"\n📋 Collect command (after run completes):")
    print(f"  python3 skrip-percobaan/collect_parallel_metrics.py <start_ts> <end_ts> --sets {suffixes} --start-indices {start_indices}")


if __name__ == "__main__":
    main()
