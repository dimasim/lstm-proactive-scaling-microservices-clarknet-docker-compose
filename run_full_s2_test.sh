#!/bin/bash

echo "===================================================="
echo "⏳ Memulai CLEAN RESET & Pengujian FULL 30% S2 (Durasi 4.2 Hari)..."
echo "===================================================="

# Ekstraksi data 30% dari dataset clarknet_2weeks_scaled.csv (skala 3x)
echo "[0/4] Mengekstrak 361.800 detik data dari dataset..."
python3 extract_full_s2.py

echo "[1/4] Mematikan seluruh layanan dan membersihkan memori lama..."
docker compose down

echo ""
echo "[2/4] Menyalakan ulang seluruh layanan dari awal (Fresh Start)..."
docker compose up -d

echo ""
echo "[3/4] Menunggu 20 detik agar Brain Orchestrator melakukan inisialisasi Cold Pool..."
for i in {20..1}; do
    echo -ne "Menunggu: $i detik tersisa...\033[0K\r"
    sleep 1
done
echo -e "\nInisialisasi selesai!"

echo ""
echo "[4/4] Memulai simulasi badai trafik K6 FULL 30% (Testing Data)..."
python3 k6_metrics_exporter.py k6_s2_full_data.json > k6_exporter.log 2>&1 &
EXPORTER_PID=$!

echo "Menyalakan Jembatan Metrik (PID: $EXPORTER_PID)"
docker run --rm -i --network host -v $(pwd):/app -w /app grafana/k6 run k6_s2_full_test.js > k6_test_result.txt

echo "Pengujian Selesai! Mematikan Jembatan Metrik..."
kill $EXPORTER_PID

echo "===================================================="
echo "✅ Pengujian 4.2 Hari Selesai Sempurna!"
echo "===================================================="
