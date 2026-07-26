import pandas as pd
import numpy as np
import json
import os

# Load raw dataset
print("Loading raw dataset...")
df_raw = pd.read_csv('../data/combined_clarknet_rps_3x.csv')

# Ensure we're reading the right columns
if 'rps_media' in df_raw.columns:
    media_col = 'rps_media'
    content_col = 'rps_content'
else:
    media_col = 'Media_Service'
    content_col = 'Content_Service'

# Fix negative values if any
df_raw[media_col] = np.maximum(df_raw[media_col], 0)
df_raw[content_col] = np.maximum(df_raw[content_col], 0)

# Calculate S2 bounds (exactly as done in Notebook 04)
test_len_1s = 6030 * 60 # 361800
df_s2 = df_raw.iloc[-test_len_1s:].reset_index(drop=True)

# Peak window starts at 329016. Let's start 300 seconds earlier to see the ramp-up.
start_idx = 329016 - 300
if start_idx < 0:
    start_idx = 0

duration_seconds = 1200 # 20 minutes

print(f"Extracting 20 minutes (1200 seconds) starting from S2 index {start_idx}...")
df_peak = df_s2.iloc[start_idx : start_idx + duration_seconds]

# Format as JSON array for K6
# Each element will be: {"time_offset": sec, "rps_media": int, "rps_content": int}
output_data = []
for i, (_, row) in enumerate(df_peak.iterrows()):
    output_data.append({
        "time_offset": i,
        "rps_media": int(row[media_col]),
        "rps_content": int(row[content_col])
    })

out_file = 'k6_s2_peak_data.json'
with open(out_file, 'w') as f:
    json.dump(output_data, f, indent=2)

print(f"Successfully extracted {len(output_data)} rows to {out_file}")
print("Sample of first 3 rows:")
print(json.dumps(output_data[:3], indent=2))
