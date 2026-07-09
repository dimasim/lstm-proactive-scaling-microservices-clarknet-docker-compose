import os
import time
import subprocess
import threading
import pandas as pd
from prometheus_client import start_http_server, Gauge

# Start Prometheus metrics exporter server on port 8001
try:
    start_http_server(8001)
    print("Started Prometheus exporter on port 8001")
except Exception as e:
    print(f"Prometheus exporter port 8001 already bound or failed: {e}")

GAUGE_MEDIA = Gauge('sent_rps_media', 'Exact sent RPS for media')
GAUGE_CONTENT = Gauge('sent_rps_content', 'Exact sent RPS for content')

def generate_k6_script(window_df):
    media_stages = []
    content_stages = []
    
    for idx, row in window_df.iterrows():
        m_rps = int(row["Media_Service"])
        c_rps = int(row["Content_Service"])
        # In ramping-arrival-rate, we define target rates second-by-second
        media_stages.append(f"{{ target: {m_rps}, duration: '1s' }}")
        content_stages.append(f"{{ target: {c_rps}, duration: '1s' }}")
        
    js_content = f"""
import http from 'k6/http';

export const options = {{
  scenarios: {{
    media_scenario: {{
      executor: 'ramping-arrival-rate',
      startRate: 0,
      timeUnit: '1s',
      preAllocatedVUs: 150,
      maxVUs: 400,
      stages: [
        {",\n        ".join(media_stages)}
      ],
      exec: 'media_request',
    }},
    content_scenario: {{
      executor: 'ramping-arrival-rate',
      startRate: 0,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 150,
      stages: [
        {",\n        ".join(content_stages)}
      ],
      exec: 'content_request',
    }},
  }},
}};

export function media_request() {{
  http.get('http://localhost:8000/media', {{ timeout: '1.5s' }});
}}

export function content_request() {{
  http.get('http://localhost:8000/content', {{ timeout: '1.5s' }});
}}
"""
    with open("skrip-percobaan/k6_replay.js", "w") as f:
        f.write(js_content)
    print("Generated skrip-percobaan/k6_replay.js successfully.")

def main():
    # 1. Load dataset and extract 5 minutes (300s) centered around the peak
    csv_path = "dataset/aggregated_clarknet_rps_3x.csv"
    print(f"Loading workload from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    peak_idx = 254291
    start_idx = max(0, peak_idx - 150)
    end_idx = min(len(df) - 1, peak_idx + 150)
    window_df = df.iloc[start_idx:end_idx].copy().reset_index(drop=True)
    
    # 2. Generate k6 JS script
    generate_k6_script(window_df)
    
    # 3. Clock-sync: wait until next integer Unix second
    now = time.time()
    sync_ts = int(now) + 2
    sleep_time = sync_ts - now
    print(f"Aligning clocks. Sleeping for {sleep_time:.4f}s to start at Unix Epoch {sync_ts}...")
    time.sleep(sleep_time)
    
    # 4. Spawn k6 background process
    print("Spawning k6 load generator...")
    k6_process = subprocess.Popen(
        ["./k6", "run", "skrip-percobaan/k6_replay.js"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # 5. Run local gauge updater in sync with k6 stages
    next_cycle_start = float(sync_ts)
    for second in range(len(window_df)):
        cycle_start = next_cycle_start
        next_cycle_start = cycle_start + 1.0
        
        media_rps = int(window_df.loc[second, "Media_Service"])
        content_rps = int(window_df.loc[second, "Content_Service"])
        
        # Set Prometheus gauges
        GAUGE_MEDIA.set(media_rps)
        GAUGE_CONTENT.set(content_rps)
        
        if (second + 1) % 10 == 0 or second == 0:
            print(f"Cycle {second+1}/300: Dispatching {media_rps + content_rps} RPS (M:{media_rps}, C:{content_rps}) via k6")
            
        # Wait for next second boundary
        now = time.time()
        sleep_to_next = next_cycle_start - now
        if sleep_to_next > 0:
            time.sleep(sleep_to_next)
            
    # Reset gauges to 0
    GAUGE_MEDIA.set(0.0)
    GAUGE_CONTENT.set(0.0)
    
    print("Waiting for k6 process to finish shutdown...")
    k6_process.wait()
    print("Test Completed successfully.")
    
    # 6. Automatically trigger collect_and_compare.py
    import sys
    output_filename = sys.argv[1] if len(sys.argv) > 1 else "collected_metrics.csv"
    print(f"\nAutomatically collecting metrics into {output_filename}...")
    
    # We pass the start_ts, end_ts, and dataset_start_idx (254141) to the collection script
    collect_cmd = [
        "python3", "skrip-percobaan/collect_and_compare.py",
        str(start_ts), str(end_ts), "254141"
    ]
    
    # Temporary swap OUTPUT_CSV in collect_and_compare.py if custom name provided
    if output_filename != "collected_metrics.csv":
        # Run collection and then rename the output file to the user's custom name
        subprocess.run(collect_cmd)
        if os.path.exists("collected_metrics.csv"):
            os.rename("collected_metrics.csv", output_filename)
            print(f"Dataset successfully saved as {output_filename}")
    else:
        subprocess.run(collect_cmd)

if __name__ == "__main__":
    main()
