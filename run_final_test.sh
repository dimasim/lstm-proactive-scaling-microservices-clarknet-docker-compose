#!/bin/bash
echo "Starting Prometheus metrics exporter..."
python3 k6_metrics_exporter.py &
EX_PID=$!

echo "Waiting 3 seconds for exporter to warm up..."
sleep 3

echo "Starting K6 load test..."
./k6 run --summary-export=summary_final.json k6_s2_peak_test.js
K6_CODE=$?

echo "K6 finished. Killing metrics exporter..."
kill $EX_PID

exit $K6_CODE
