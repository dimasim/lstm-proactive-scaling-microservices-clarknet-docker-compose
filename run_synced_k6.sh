#!/bin/bash
# Start Prometheus exporter for K6 workload
python3 k6_metrics_exporter.py > k6_exporter.log 2>&1 &
EXPORTER_PID=$!

echo "Started Prometheus Exporter with PID $EXPORTER_PID"

# Start K6 Load Test
echo "Starting K6 Load Test..."
sudo docker run --rm -i --network host -v $(pwd):/app -w /app grafana/k6 run k6_s2_peak_test.js > k6_test_result.txt

# Once K6 finishes, kill the exporter
echo "K6 Test Finished. Stopping Exporter..."
kill $EXPORTER_PID
