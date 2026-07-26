#!/bin/bash
# Start Prometheus exporter for K6 workload (Demo Version)
python3 k6_demo_exporter.py > k6_demo_exporter.log 2>&1 &
EXPORTER_PID=$!

echo "Started Prometheus Demo Exporter with PID $EXPORTER_PID"

# Start K6 Load Test (Demo Version)
echo "Starting K6 Demo Load Test (2 Minutes)..."
sudo docker run --rm -i --network host -v $(pwd):/app -w /app grafana/k6 run k6_demo_sidang.js > k6_demo_result.txt

# Once K6 finishes, kill the exporter
echo "K6 Demo Test Finished. Stopping Exporter..."
kill $EXPORTER_PID
