#!/usr/bin/env python3
"""
Merge collected_metrics CSV files from multiple parallel sets into a single dataset.

Usage:
    # Merge all collected_metrics_*.csv in current directory
    python3 merge_collected_metrics.py --sets a,b,c,d,e,f,g,h --start-indices 0,151178,302356,453534,604712,755890,907068,1058246

    # Merge from two server directories
    python3 merge_collected_metrics.py --sets a,b,c,d,e,f,g,h \\
        --start-indices 0,151178,302356,453534,604712,755890,907068,1058246 \\
        --input-dirs ./server1-results ./server2-results \\
        --output collected_metrics_final.csv
"""

import argparse
import csv
import os
import sys
import string


def load_metrics_csv(filepath):
    """Load a collected_metrics CSV file and return rows as list of dicts."""
    rows = []
    if not os.path.exists(filepath):
        print(f"⚠️  Warning: {filepath} not found, skipping")
        return rows
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    
    return rows


def validate_and_merge(set_data, total_expected_rows=None):
    """
    Validate and merge set data in order.
    set_data: list of (suffix, start_idx, rows) tuples, sorted by start_idx.
    """
    # Sort by start_idx
    set_data.sort(key=lambda x: x[1])
    
    merged = []
    issues = []
    
    for i, (suffix, start_idx, rows) in enumerate(set_data):
        if len(rows) == 0:
            issues.append(f"❌ Set {suffix.upper()}: no data (0 rows)")
            continue
        
        # Check for gap between previous set and this one
        if i > 0:
            prev_suffix, prev_start, prev_rows = set_data[i - 1]
            prev_end = prev_start + len(prev_rows)
            if start_idx > prev_end:
                gap = start_idx - prev_end
                issues.append(f"⚠️  Gap of {gap} rows between Set {prev_suffix.upper()} and Set {suffix.upper()}")
            elif start_idx < prev_end:
                overlap = prev_end - start_idx
                issues.append(f"⚠️  Overlap of {overlap} rows between Set {prev_suffix.upper()} and Set {suffix.upper()}")
        
        merged.extend(rows)
        print(f"  ✅ Set {suffix.upper()}: {len(rows):,} rows (idx {start_idx:,} - {start_idx + len(rows) - 1:,})")
    
    # Validate total
    if total_expected_rows:
        if len(merged) != total_expected_rows:
            issues.append(f"⚠️  Expected {total_expected_rows:,} rows, got {len(merged):,}")
    
    return merged, issues


def detect_freezes(merged_rows, threshold=30):
    """Detect freeze patterns in the merged data."""
    columns_to_check = ["cpu_media", "cpu_content", "ram_media", "ram_content", 
                        "latency_media", "latency_content", "rps_media", "rps_content"]
    
    freeze_report = []
    
    for col in columns_to_check:
        streak = 0
        last_val = None
        freezes = []
        
        for i, row in enumerate(merged_rows):
            val = row.get(col, "")
            if val == last_val:
                streak += 1
            else:
                if streak >= threshold:
                    freezes.append({
                        "start": i - streak,
                        "end": i - 1,
                        "duration": streak,
                        "value": last_val
                    })
                streak = 1
            last_val = val
        
        # Check last streak
        if streak >= threshold:
            freezes.append({
                "start": len(merged_rows) - streak,
                "end": len(merged_rows) - 1,
                "duration": streak,
                "value": last_val
            })
        
        if freezes:
            total_frozen = sum(f["duration"] for f in freezes)
            freeze_report.append({
                "column": col,
                "freeze_count": len(freezes),
                "total_frozen_seconds": total_frozen,
                "percentage": total_frozen / len(merged_rows) * 100,
                "details": freezes[:5]  # show first 5
            })
    
    return freeze_report


def main():
    parser = argparse.ArgumentParser(description="Merge collected_metrics CSVs from parallel sets")
    parser.add_argument("--sets", type=str, required=True, help="Comma-separated set suffixes (e.g., a,b,c,d,e,f,g,h)")
    parser.add_argument("--start-indices", type=str, required=True, help="Comma-separated start indices for each set")
    parser.add_argument("--input-dirs", nargs="+", default=["."], help="Directories containing collected_metrics_*.csv files")
    parser.add_argument("--output", type=str, default="collected_metrics_final.csv", help="Output filename")
    parser.add_argument("--total-expected", type=int, default=None, help="Total expected rows for validation")
    parser.add_argument("--freeze-threshold", type=int, default=30, help="Consecutive identical values to flag as freeze")
    args = parser.parse_args()
    
    suffixes = args.sets.split(",")
    start_indices = [int(x) for x in args.start_indices.split(",")]
    
    if len(suffixes) != len(start_indices):
        print("❌ Error: number of sets must match number of start indices")
        sys.exit(1)
    
    print(f"🔄 Loading {len(suffixes)} set files...")
    
    # Load all set data
    set_data = []
    for suffix, start_idx in zip(suffixes, start_indices):
        filename = f"collected_metrics_{suffix}.csv"
        rows = []
        
        # Search across input directories
        for input_dir in args.input_dirs:
            filepath = os.path.join(input_dir, filename)
            found_rows = load_metrics_csv(filepath)
            if found_rows:
                rows = found_rows
                print(f"  📂 Found {filename} in {input_dir} ({len(rows):,} rows)")
                break
        
        if not rows:
            print(f"  ⚠️  {filename} not found in any input directory")
        
        set_data.append((suffix, start_idx, rows))
    
    # Validate and merge
    print(f"\n📊 Validating and merging...")
    merged, issues = validate_and_merge(set_data, args.total_expected)
    
    if issues:
        print(f"\n⚠️  Issues found:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print(f"\n✅ No issues found!")
    
    # Detect freezes
    print(f"\n🔍 Checking for freeze patterns (threshold: {args.freeze_threshold}s)...")
    freeze_report = detect_freezes(merged, args.freeze_threshold)
    
    if freeze_report:
        print(f"\n⚠️  Freeze patterns detected:")
        for fr in freeze_report:
            print(f"  📌 {fr['column']}: {fr['freeze_count']} freezes, "
                  f"{fr['total_frozen_seconds']:,}s total ({fr['percentage']:.2f}%)")
            for d in fr['details']:
                print(f"      Row {d['start']:,}-{d['end']:,} ({d['duration']}s) stuck at {d['value']}")
    else:
        print(f"  ✅ No freeze patterns detected!")
    
    # Write merged output
    if merged:
        print(f"\n💾 Writing {len(merged):,} rows to {args.output}...")
        
        # Use same column order as original
        fieldnames = ["timestamp", "rps_media", "rps_content", "cpu_media", "cpu_content",
                      "ram_media", "ram_content", "replicas_media", "replicas_content",
                      "latency_media", "latency_content"]
        
        with open(args.output, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            # Re-index timestamps sequentially
            for i, row in enumerate(merged):
                # Keep original metrics, but assign sequential index as timestamp
                out_row = {}
                for col in fieldnames:
                    if col == "timestamp":
                        out_row[col] = i  # sequential index
                    else:
                        out_row[col] = row.get(col, 0)
                writer.writerow(out_row)
        
        print(f"✅ Successfully wrote {args.output}")
    else:
        print(f"❌ No data to merge!")
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 MERGE SUMMARY")
    print(f"{'='*60}")
    print(f"  Sets merged: {len(set_data)}")
    print(f"  Total rows: {len(merged):,} ({len(merged)/86400:.1f} days)")
    print(f"  Issues: {len(issues)}")
    print(f"  Freezes: {len(freeze_report)} columns affected")
    print(f"  Output: {args.output}")


if __name__ == "__main__":
    main()
