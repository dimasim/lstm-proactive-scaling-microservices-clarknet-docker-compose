# LSTM-Based Proactive Auto-Scaling for SLA on Microservices (Clarknet Compose)

Repository ini berisi implementasi final *testbed* arsitektur microservices berbasis Docker Compose untuk menguji sistem **Proactive Auto-Scaling** menggunakan algoritma **Long Short-Term Memory (LSTM)** dengan fungsi kerugian *Quantile Loss*. Sistem ini dilengkapi dengan agen cerdas (*Brain Orchestrator*) dan mekanisme penyediaan kontainer kilat (*Container Cold Pool*) guna mempertahankan kepatuhan *Service Level Agreement* (SLA) di bawah badai trafik dinamis dari dataset **ClarkNet**.

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
* **Agen Pengendali (Auto-Scaler):**
  * `brain-orchestrator`: Agen cerdas Python yang memprediksi beban kerja (LSTM) dan mengeksekusi siklus MAPE-K untuk menambah/mengurangi replika kontainer secara otonom menggunakan Docker Socket API (memanfaatkan *Cold Pool*).
* **Injektor Beban (Load Generator):**
  * `K6`: Alat *load testing* tingkat industri yang menembakkan trafik HTTP secara paralel (*shared-iterations*) untuk menyimulasikan beban kerja dinamis.

---

## 2. Struktur Direktori

```text
skripsi-clarknet/
├── brain-orchestrator/      # Modul AI LSTM Quantile & Eksekutor MAPE-K (Python)
├── content-service/         # Service penangan halaman HTML statik (FastAPI)
├── media-service/           # Service penangan aset gambar statik (FastAPI)
├── dashboard-service/       # Dashboard real-time telemetry (Go + HTML/JS/SSE)
├── haproxy/                 # Konfigurasi routing load balancer HAProxy
├── prometheus/              # Konfigurasi target metrik database Prometheus
├── dataset/                 # Dataset beban kerja ClarkNet (RPS per detik)
├── k6/                      # Konfigurasi load testing
├── skrip-percobaan/         # Kumpulan skrip pengumpulan data awal
├── run_full_s2_test.sh      # Skrip otomatisasi pengujian K6 4 Hari (Marathon)
├── extract_full_s2.py       # Skrip ekstraksi 30% data S2 ClarkNet untuk K6
└── k6_metrics_exporter.py   # Jembatan metrik target RPS K6 ke Prometheus
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
python3 skrip-percobaan/send_clarknet_load.py
```

### B. Mengekstrak Metrik Menjadi Berkas CSV
Setelah simulasi beban berjalan (misalnya selama 10 atau 15 menit), matikan generator beban dan jalankan skrip berikut untuk menarik data dari Prometheus dan mengonversinya ke format CSV siap pakai untuk AI training:
```bash
# Penggunaan: python3 skrip-percobaan/collect_and_compare.py <start_unix_timestamp> <end_unix_timestamp>
python3 skrip-percobaan/collect_and_compare.py 1783176375 1783177275
```
Hasil ekstraksi akan disimpan dalam file [collected_metrics.csv](file:///home/dimas/skripsi-clarknet/collected_metrics.csv).

### C. Menjalankan Pengujian Beban 4 Hari (K6 Marathon)
Untuk menguji ketahanan sistem *proactive auto-scaling* terhadap 30% data dari dataset ClarkNet (berdurasi simulasi sekitar 4,2 hari waktu nyata), jalankan *script* bash otomatis menggunakan `nohup` agar kebal dari diskoneksi SSH:
```bash
nohup ./run_full_s2_test.sh > full_test_nohup.log 2>&1 &
```
Perintah ini akan melakukan *Clean Reset* terhadap *database* Prometheus, menyalakan kontainer, dan mulai menembakkan *request* menggunakan K6 di latar belakang. Anda dapat memantau log berjalannya tes menggunakan perintah `tail -f full_test_nohup.log`.

### D. Menghentikan Pengujian K6 Secara Aman (*Graceful Stop*)
Jika Anda perlu menghentikan pengujian sebelum waktu 4 hari berakhir, sangat disarankan untuk melakukan penghentian secara halus (*Graceful Stop*) agar K6 sempat mencetak tabel *Summary* (P95 Latency, Error Rate) di akhir file log:
1. Cari tahu ID Kontainer K6 yang sedang berjalan:
   ```bash
   docker ps | grep grafana/k6
   ```
2. Hentikan kontainer menggunakan ID yang didapatkan (misal: `a1b2c3d4e5f6`):
   ```bash
   docker stop <CONTAINER_ID>
   ```
3. Setelah dimatikan, K6 akan menyelesaikan *request* terakhirnya, mencetak tabel hasil akhir ke `k6_test_result.txt`, dan *script* `nohup` akan menyelesaikan sisa pembersihan secara otomatis.

---

## 5. Dokumen Penelitian Acuan (Skripsi)

Untuk mempermudah penulisan naskah skripsi, beberapa berkas konsep dan ringkasan teori telah disediakan:
* [scalling-act.md](file:///home/dimas/skripsi-clarknet/scalling-act.md): Penjelasan rumus matematika penentuan jumlah kontainer, CDT (Cooldown Timer), dan GDS (Gradually Decreasing Strategy).
* [fundamental.md](file:///home/dimas/skripsi-clarknet/fundamental.md): Acuan logika data collection dan metrik telemetri.
* [imdoukh2019-ringkasan.md](file:///home/dimas/skripsi-clarknet/imdoukh2019-ringkasan.md): Ringkasan jurnal rujukan utama (Imdoukh et al., 2019) mengenai *Docker Auto-scaling*.
* [ringkasan-proposal-skripsi.md](file:///home/dimas/skripsi-clarknet/ringkasan-proposal-skripsi.md): Draft ringkasan proposal skripsi Anda.

---

## 6. Panduan Integrasi Layanan Baru (Microservice Integration Guide)

Untuk mengintegrasikan layanan mikro baru (*new service*) ke dalam ekosistem *Proactive Auto-Scaling*, ikuti langkah-langkah berikut:

### Langkah A: Konfigurasi Docker Compose (`docker-compose.yml`)
1. Definisikan container baru dengan label compose project dan service yang sesuai.
2. Sediakan replika kontainer siaga (*Cold Pool*) dengan nama berurutan (misalnya `new-service-1`, `new-service-2`, dst) namun diatur dalam keadaan berhenti (*stopped*) pada inisialisasi awal.
3. Batasi resource CPU dan memori menggunakan `deploy.resources.limits` (misalnya 0.1 CPU core dan 64MB RAM) agar konsisten dengan evaluasi efisiensi kontainer.

### Langkah B: Daftarkan ke Brain Orchestrator (`brain-orchestrator/main.py`)
1. **Inisialisasi Cold Pool:**  
   Tambahkan nama layanan baru ke daftar pencarian kontainer pada fungsi `_init_cold_pool()`:
   ```python
   for srv_name in ["content-service", "media-service", "new-service"]:
   ```
2. **Definisi Metrik Prometheus:**  
   Tambahkan `Gauge` baru untuk memancarkan hasil prediksi dan jumlah target replika layanan baru ke Prometheus:
   ```python
   PRED_RPS_NEW = Gauge('predicted_rps_new', 'Predicted RPS for new-service')
   TARGET_REP_NEW = Gauge('target_replicas_new', 'Target replicas for new-service')
   ```
3. **Pengambilan Metrik Aktif:**  
   Perbarui modul `metrics_collector.py` untuk menarik metrik lalu lintas masuk (*RPS*) dari Prometheus untuk layanan baru.
4. **Logika MAPE-K Loop:**  
   Pada fungsi `run()`, hitung kebutuhan replika dan picu aktuasi GDS untuk layanan baru:
   ```python
   req_new = self.calculate_replicas(pred_new)
   self.current_rep_new, self.cooldown_new = self.perform_gds_scaling(
       "new-service", req_new, self.current_rep_new, self.cooldown_new
   )
   ```

### Langkah C: Konfigurasi Ulang Target Scrape Prometheus & HAProxy
1. Tambahkan target routing kontainer baru ke konfigurasi backend di berkas `haproxy.cfg`.
2. Pastikan Prometheus melakukan *scrape* metrik cAdvisor dan HAProxy untuk mendeteksi metrics baru tersebut.

---

## 7. Fitur Utama & Panduan Evaluasi UAT (User Acceptance Testing)

Bagian ini merangkum mekanisme teknis utama yang dinilai dalam kuesioner UAT/validasi kepuasan operator:

### A. Mekanisme Container Cold Pool (Mitigasi Cold Start)
* **Masalah:** Proses pembuatan container baru dari awal saat *scale-up* mendadak memicu penundaan waktu aktif (*cold start penalty*), yang berakibat pada penurunan keandalan SLA.
* **Solusi:** Sistem menginisialisasi sejumlah kontainer cadangan dalam kondisi mati (*stopped*). Saat prediksi LSTM mendeteksi kenaikan beban, Aktuator hanya memanggil perintah *start* (`c.start()`) dari Docker Socket API, memotong durasi inisialisasi runtime & network secara instan (*warm start*).

### B. Kebijakan Gradual Down-Scaling (GDS) & Cooldown Timer (CDT)
* **Masalah:** Pola beban kerja yang sangat fluktuatif (*spiky / bursty*) dapat memicu osilasi penskalaan (kontainer terus mati-nyala berulang kali / *ping-pong effect*).
* **Solusi:** 
  * **CDT (Cooldown Timer):** Sistem menahan aksi *scale-down* selama 10 detik setelah aksi penskalaan terakhir untuk memberi jeda stabilisasi.
  * **SDR (Scale-Down Ratio = 0.40):** Pengurangan kontainer dilakukan secara bertahap (tidak langsung mematikan semua kontainer sekaligus) dengan mengalikan selisih replika terhadap rasio desimal $0{,}40$, menjamin ketersediaan kapasitas cadangan jika terjadi lonjakan trafik susulan.

### C. Observability & Dashboard Real-Time (Server-Sent Events)
* Dashboard menyerap telemetri secara *push-based* melalui Server-Sent Events (SSE) langsung dari database Prometheus.
* Memvisualisasikan perbandingan trafik aktual (RPS) terhadap prediksi LSTM Quantile ($\tau=0{,}95$) guna memberikan pemahaman langsung bagi operator/DevOps tentang performa *auto-scaler* dalam mematuhi SLA.
