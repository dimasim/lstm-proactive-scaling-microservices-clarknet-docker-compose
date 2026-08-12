import pandas as pd
import numpy as np
import json

# Load raw dataset (yang sudah di-scale 3x)
print("Loading 3x scaled dataset...")
df_raw = pd.read_csv('./dataset/clarknet_2weeks_scaled.csv')

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

# S2 test length is 30% of the data
test_len_1s = int(len(df_raw) * 0.3)
df_s2 = df_raw.iloc[-test_len_1s:].reset_index(drop=True)

print(f"Extracting FULL 30% TEST DATA ({test_len_1s} seconds / ~4.18 hari)...")

# Format as JSON array for K6
output_data = []
for i, (_, row) in enumerate(df_s2.iterrows()):
    output_data.append({
        "time_offset": i,
        "rps_media": int(row[media_col]),
        "rps_content": int(row[content_col])
    })

out_file = 'k6_s2_full_data.json'
with open(out_file, 'w') as f:
    json.dump(output_data, f, indent=2)

print(f"Successfully extracted {len(output_data)} rows to {out_file}")
