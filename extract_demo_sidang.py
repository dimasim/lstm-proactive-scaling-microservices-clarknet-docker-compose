import json
import pandas as pd
import numpy as np

# Baca dataset peak 20 menit (k6_s2_peak_data.json)
with open('k6_s2_peak_data.json', 'r') as f:
    data = json.load(f)

# Titik heroik ada di index 904.
# Kita buat 2 menit demo (120 detik). 60 detik sebelum puncak (844), 60 detik setelahnya (964).
start_idx = 844
end_idx = 964

# --- 1. Buat K6 Demo Data (120 detik) ---
demo_data = []
for i in range(start_idx, min(end_idx, len(data))):
    row = data[i]
    demo_data.append({
        "time_offset": i - start_idx,
        "rps_media": row["rps_media"],
        "rps_content": row["rps_content"]
    })

with open('k6_demo_sidang.json', 'w') as f:
    json.dump(demo_data, f, indent=2)
print(f"Berhasil membuat k6_demo_sidang.json dengan {len(demo_data)} baris (durasi {len(demo_data)} detik)")

# --- 2. Buat History CSV (60 detik sebelumnya) untuk LSTM ---
# Kita ambil dari (start_idx - 60) sampai (start_idx - 1)
history_start = start_idx - 60
history_end = start_idx

history_rows = []
for i in range(history_start, history_end):
    row = data[i]
    history_rows.append({
        "Content_Service": row["rps_content"],
        "Media_Service": row["rps_media"]
    })

df_history = pd.DataFrame(history_rows)
df_history.to_csv('demo_history.csv', index=False)
print(f"Berhasil membuat demo_history.csv dengan {len(df_history)} baris historis.")
