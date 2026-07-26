import time
import json
from prometheus_client import start_http_server, Gauge

GAUGE_MEDIA = Gauge('sent_rps_media', 'Exact sent RPS for media')
GAUGE_CONTENT = Gauge('sent_rps_content', 'Exact sent RPS for content')

def main():
    start_http_server(8001)
    print("Started Prometheus exporter on port 8001")
    
    with open('k6_demo_sidang.json') as f:
        data = json.load(f)
        
    print(f"Loaded {len(data)} seconds of demo data.")
    print("Starting synchronous replay of metrics to Prometheus...")
    
    start_time = time.time()
    for index, row in enumerate(data):
        target_time = start_time + index
        now = time.time()
        
        sleep_time = target_time - now
        if sleep_time > 0:
            time.sleep(sleep_time)
            
        media_rps = row['rps_media']
        content_rps = row['rps_content']
        GAUGE_MEDIA.set(media_rps)
        GAUGE_CONTENT.set(content_rps)
        
        if index % 10 == 0:
            print(f"Time {index}s - Exposed Media RPS: {media_rps}, Content RPS: {content_rps}")

    print("Replay finished.")

if __name__ == "__main__":
    main()
