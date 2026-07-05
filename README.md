# LSTM-Based Proactive Auto-Scaling for SLA on Microservices (Clarknet Compose)

Repository ini berisi implementasi *testbed* arsitektur microservices berbasis Docker Compose untuk melakukan pengumpulan dataset telemetri (CPU, RAM, dan RPS) menggunakan profil beban kerja riil **ClarkNet Dataset**. Data yang dikoleksi dari lingkungan ini dirancang untuk melatih model kecerdasan buatan (LSTM/GRU) guna melakukan *proactive auto-scaling* demi menjaga kepatuhan SLA.

---

## 1. Arsitektur Sistem

Sistem diatur secara modular menggunakan Docker Compose dengan komponen-komponen berikut:

* **Microservices (FastAPI - Python):**
  * `media-service`: Menangani rute `/media` (simulasi aset gambar/file statik).
  * `content-service`: Menangani rute `/content` (simulasi konten halaman HTML statik).
* **Load Balancer (HAProxy):**
  * Bertindak sebagai gerbang masuk utama (port `8000`) dan membagi beban ke replika service secara *round-robin* berbasis DNS resolver internal Docker.
* **Monitoring & Telemetri:**
  * `cAdvisor`: Mengoleksi penggunaan resource kontainer (CPU dan RAM) langsung dari cgroups kernel Linux.
  * `Prometheus`: Menyimpan metrik telemetri yang diekspos oleh cAdvisor dan HAProxy secara *time-series*.
  * `dashboard-service`: Dashboard visualisasi real-time berbasis Go dan Server-Sent Events (SSE) yang menyajikan metrik performa di port `3002`.

---

## 2. Struktur Direktori

```text
skripsi-clarknet/
├── content-service/         # Service penangan halaman HTML statik (FastAPI)
├── media-service/           # Service penangan aset gambar statik (FastAPI)
├── dashboard-service/       # Dashboard real-time telemetry (Go + HTML/JS)
├── haproxy/                 # Konfigurasi routing load balancer HAProxy
├── prometheus/              # Konfigurasi target metrik database Prometheus
├── dataset/                 # Dataset beban kerja ClarkNet (RPS per detik)
├── send_clarknet_load.py    # Skrip python untuk menyimulasikan beban kerja dataset ClarkNet
├── send_peak_flat_load.py   # Skrip python untuk pengujian beban puncak konstan (stress test)
└── collect_and_compare.py   # Skrip untuk mengekstrak data dari Prometheus menjadi CSV
```

---

## 3. Langkah Penggunaan (Quick Start)

### A. Konfigurasi Environment
Salin berkas konfigurasi environment bawaan:
```bash
cp .env.example .env
```

### B. Menjalankan Kontainer
Bangun dan jalankan seluruh infrastruktur di latar belakang:
```bash
docker compose up --build -d
```

### C. Verifikasi Konektivitas
Pastikan semua service merespons dengan benar:
* **Media Service:** `curl http://localhost:8000/media`
* **Content Service:** `curl http://localhost:8000/content`
* **Telemetry Dashboard:** Buka browser di `http://localhost:3002`
* **Prometheus UI:** Buka browser di `http://localhost:9090`

---

## 4. Pengumpulan Dataset & Simulasi Beban

### A. Menjalankan Simulasi Beban Kerja ClarkNet
Jalankan skrip berikut untuk mulai mengirimkan trafik ke HAProxy berdasarkan data deret waktu (*time-series*) asli dari dataset ClarkNet detik-demi-detik:
```bash
python3 send_clarknet_load.py
```

### B. Mengekstrak Metrik Menjadi Berkas CSV
Setelah simulasi beban berjalan (misalnya selama 10 atau 15 menit), matikan generator beban dan jalankan skrip berikut untuk menarik data dari Prometheus dan mengonversinya ke format CSV siap pakai untuk AI training:
```bash
# Penggunaan: python3 collect_and_compare.py <start_unix_timestamp> <end_unix_timestamp>
python3 collect_and_compare.py 1783176375 1783177275
```
Hasil ekstraksi akan disimpan dalam file [collected_metrics.csv](file:///home/dimas/skripsi-clarknet/collected_metrics.csv).

---

## 5. Dokumen Penelitian Acuan (Skripsi)

Untuk mempermudah penulisan naskah skripsi, beberapa berkas konsep dan ringkasan teori telah disediakan:
* [scalling-act.md](file:///home/dimas/skripsi-clarknet/scalling-act.md): Penjelasan rumus matematika penentuan jumlah kontainer, CDT (Cooldown Timer), dan GDS (Gradually Decreasing Strategy).
* [fundamental.md](file:///home/dimas/skripsi-clarknet/fundamental.md): Acuan logika data collection dan metrik telemetri.
* [imdoukh2019-ringkasan.md](file:///home/dimas/skripsi-clarknet/imdoukh2019-ringkasan.md): Ringkasan jurnal rujukan utama (Imdoukh et al., 2019) mengenai *Docker Auto-scaling*.
* [ringkasan-proposal-skripsi.md](file:///home/dimas/skripsi-clarknet/ringkasan-proposal-skripsi.md): Draft ringkasan proposal skripsi Anda.
