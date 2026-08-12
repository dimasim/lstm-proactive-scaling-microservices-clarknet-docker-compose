# LSTM-Based Proactive Auto-Scaling for SLA on Microservices (Clarknet Compose)

Repository ini berisi implementasi *testbed* arsitektur microservices berbasis Docker Compose untuk menguji sistem **Proactive Auto-Scaling** menggunakan model **LSTM Multivariate** dengan fungsi kerugian *Quantile Loss (τ=0.95)*. Agen cerdas (*Brain Orchestrator*) memanfaatkan model LSTM untuk memprediksi beban kerja masa depan dan mengeksekusi siklus MAPE-K guna mempertahankan kepatuhan *Service Level Agreement* (SLA).

> **Model yang digunakan adalah MULTIVARIATE** — model LSTM secara simultan memprediksi RPS untuk **dua layanan sekaligus** (`content-service` dan `media-service`) dari 12 fitur temporal yang diekstrak dari deret waktu agregat 30 detik.

---

## Daftar Isi

1. [Arsitektur Sistem](#1-arsitektur-sistem)
2. [Struktur Direktori](#2-struktur-direktori)
3. [Pelatihan Model LSTM (Wajib Dibaca)](#3-pelatihan-model-lstm-wajib-dibaca)
4. [Quick Start — Menjalankan Testbed](#4-quick-start--menjalankan-testbed)
5. [Simulasi Beban Kerja (Load Testing)](#5-simulasi-beban-kerja-load-testing)
6. [UAT — User Acceptance Testing](#6-uat--user-acceptance-testing)
7. [Menambahkan Service Baru](#7-menambahkan-service-baru)
8. [Adopsi ke Aplikasi Lain (Custom Deployment)](#8-adopsi-ke-aplikasi-lain-custom-deployment)

---

## 1. Arsitektur Sistem

```
┌──────────────────────────────────────────────────────────────────┐
│                      LOAD GENERATOR (K6)                          │
│           Replay dataset ClarkNet detik-per-detik                 │
└───────────────────────────┬──────────────────────────────────────┘
                            │  HTTP Request (port 8000)
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                       HAProxy (port 8000)                         │
│   ACL routing: /media → media_back | /content → content_back      │
│   Metrics Exporter: port 8404/metrics                            │
└─────────────┬──────────────────────────┬─────────────────────────┘
              │                          │
              ▼                          ▼
   ┌──────────────────┐       ┌────────────────────┐
   │  media-service   │       │  content-service   │
   │  (N replika Go)  │       │  (N replika Go)    │
   │  CPU: 0.1 core   │       │  CPU: 0.1 core     │
   │  RAM: 64MB       │       │  RAM: 64MB         │
   └────────┬─────────┘       └────────┬───────────┘
            │                          │
            └────────────┬─────────────┘
                         │ cAdvisor scrape
                         ▼
           ┌─────────────────────────┐
           │  Prometheus (port 9090) │◄── HAProxy metrics (8404)
           │  + cAdvisor (8080)      │◄── brain-orchestrator (8000)
           └────────────┬────────────┘
                        │
           ┌────────────┴────────────┐
           │                         │
           ▼                         ▼
 ┌──────────────────┐    ┌─────────────────────────┐
 │ dashboard-service│    │    brain-orchestrator   │
 │  (Go+SSE, :3002) │    │    (Python LSTM Agent)  │
 │  Visualisasi RPS,│    │                         │
 │  Replika, Prediksi    │  1. Query RPS Prometheus │
 └──────────────────┘    │  2. Hitung 12 Fitur     │
                         │  3. Prediksi LSTM       │
                         │  4. Hitung target rep.  │
                         │  5. Eksekusi GDS Scale  │
                         └─────────────────────────┘
```

### Tabel Komponen

| Komponen | Teknologi | Port | Fungsi |
|---|---|---|---|
| `haproxy` | HAProxy 2.8 | 8000 | Load balancer, routing `/media` & `/content` |
| `media-service` | Go | — | Simulasi layanan aset gambar (CPU-intensive) |
| `content-service` | Go | — | Simulasi layanan halaman HTML (CPU-intensive) |
| `cadvisor` | cAdvisor | 8080 | Monitoring resource kontainer (CPU/RAM) |
| `prometheus` | Prometheus | 9090 | Time-series database metrik |
| `dashboard-service` | Go + SSE | 3002 | Dashboard real-time visualisasi |
| `brain-orchestrator` | Python LSTM | 8000* | Agen prediksi & auto-scaling |
| `locust` | Locust | 8089 | Load generator alternatif (development) |

> \*Port 8000 pada `brain-orchestrator` digunakan untuk meng-*expose* metrik prediksi ke Prometheus.

---

## 2. Struktur Direktori

```text
lstm-proactive-scaling-microservices-clarknet-docker-compose/
│
├── brain-orchestrator/          # Agen AI utama (Python)
│   ├── main.py                  # ★ Loop MAPE-K, GDS scaling, cold pool
│   ├── lstm_model.py            # ★ Wrapper load & inferensi model LSTM
│   ├── metrics_collector.py     # Query RPS real-time dari Prometheus
│   ├── Dockerfile
│   └── requirements.txt
│
├── content-service/             # Microservice halaman konten (Go)
│   ├── main.go
│   └── Dockerfile
│
├── media-service/               # Microservice aset gambar (Go)
│   ├── main.go
│   └── Dockerfile
│
├── dashboard-service/           # Dashboard telemetri real-time (Go)
├── haproxy/
│   └── haproxy.cfg              # ★ Routing ACL dan backend server-template
├── prometheus/
│   └── prometheus.yml           # ★ Target scrape semua komponen
│
├── dataset/                     # Dataset ClarkNet (CSV siap pakai)
├── locust/                      # Konfigurasi load testing Locust
├── k6_s2_full_test.js           # ★ Script K6 marathon 4.2 hari
├── k6_s2_full_data.json         # Data replay ClarkNet 30% untuk K6
├── extract_full_s2.py           # Skrip ekstraksi dataset ClarkNet → JSON
├── k6_metrics_exporter.py       # Jembatan: export target RPS K6 → Prometheus
├── run_full_s2_test.sh          # Otomasi pengujian K6 marathon
├── docker-compose.yml           # ★ Definisi semua service & cold pool
├── .env.example                 # Template konfigurasi port
└── kodetrainingmodel.py         # ★ Kode pelatihan model LSTM (lihat Bagian 3)
```

---

## 3. Pelatihan Model LSTM (Wajib Dibaca)

> ⚠️ **Model TIDAK dilatih ulang saat runtime.** File model (`.keras`) harus sudah tersedia sebelum testbed dijalankan. Bagian ini menjelaskan cara melatih model dari awal jika dibutuhkan.

### 3.1 Memahami Model: LSTM Multivariate Quantile

Model yang digunakan adalah **LSTM Multivariate** yang menerima **12 fitur temporal** dan memprediksi **2 nilai output secara bersamaan**:

```
INPUT (60 langkah × 12 fitur)                   OUTPUT (2 nilai)
┌──────────────────────────────────┐       ┌───────────────────────────┐
│  [t-59] roll_1m_mean             │       │  pred_rps_content  ──────►│ → Hitung replika
│  [t-59] roll_15m_mean            │       │  pred_rps_media    ──────►│ → Hitung replika
│  [t-59] roll_1h_mean             │ ─LSTM─►                           │
│  [t-59] roll_1m_max              │       │  (Prediksi RPS 30 detik   │
│  [t-59] roll_1h_std              │       │   ke depan untuk SETIAP   │
│  [t-59] lag_30s                  │       │   layanan secara simultan)│
│  [t-59] diff_1, diff_2, diff_10  │       └───────────────────────────┘
│  [t-59] hour_sin, hour_cos       │
│  [t-59] is_weekend               │
│  ... (60 langkah total) ...      │
└──────────────────────────────────┘
```

- **Lookback**: 60 langkah × 30 detik = **30 menit sejarah**
- **Fungsi Loss**: *Quantile Loss* dengan τ=0.95 (konservatif — lebih baik over-provision daripada SLA dilanggar)
- **Split data**: 70% training / 30% testing

### 3.2 Format Dataset untuk Training

File CSV harus memiliki kolom berikut (minimal):

```csv
datetime,rps_total,Content_Service,Media_Service
2024-01-01 00:00:00,45.2,15.1,30.1
2024-01-01 00:00:30,47.8,16.2,31.6
...
```

| Kolom | Tipe | Keterangan |
|---|---|---|
| `datetime` | datetime | Timestamp setiap 30 detik |
| `rps_total` | float | Total RPS gabungan semua service |
| `Content_Service` | float | RPS khusus content-service |
| `Media_Service` | float | RPS khusus media-service |

> Dataset ClarkNet yang sudah diproses tersedia di direktori `dataset/`. File `clarknet_features_30s.csv` sudah berformat siap pakai.

### 3.3 Pipeline Pelatihan (`kodetrainingmodel.py`)

**Tahap 1 — Rekayasa Fitur (Feature Engineering)**
```python
# 12 fitur dihitung dari kolom rps_total
features = [
    'roll_1m_mean',   # Rata-rata rolling 1 menit (2 langkah × 30 detik)
    'roll_15m_mean',  # Rata-rata rolling 15 menit (30 langkah)
    'roll_1h_mean',   # Rata-rata rolling 1 jam (120 langkah)
    'roll_1m_max',    # Nilai maksimum rolling 1 menit
    'roll_1h_std',    # Standar deviasi rolling 1 jam
    'lag_30s',        # Nilai RPS 30 detik yang lalu
    'diff_1',         # Selisih dengan 1 langkah sebelumnya
    'diff_2',         # Selisih dengan 2 langkah sebelumnya
    'diff_10',        # Selisih dengan 10 langkah sebelumnya
    'hour_sin',       # Fitur waktu siklus jam (sin)
    'hour_cos',       # Fitur waktu siklus jam (cos)
    'is_weekend',     # Apakah akhir pekan? (0 = tidak, 1 = ya)
]

# Target (2 output yang diprediksi secara bersamaan)
targets = ['Content_Service', 'Media_Service']
```

**Tahap 2 — Normalisasi & Split Data**
```python
# Normalisasi fitur → disimpan sebagai feat_scaler.pkl
feat_scaler = MinMaxScaler()
X_scaled = feat_scaler.fit_transform(X)

# Normalisasi target → disimpan sebagai tgt_scaler.pkl
tgt_scaler = MinMaxScaler()
y_scaled = tgt_scaler.fit_transform(y)

# Split 70% training / 30% testing
n_train = int(len(X_scaled) * 0.7)
```

**Tahap 3 — Arsitektur Model LSTM**
```python
model = Sequential([
    LSTM(64, return_sequences=True, input_shape=(LOOK_BACK, N_FEATURES)),  # LOOK_BACK=60, N_FEATURES=12
    Dropout(0.2),
    LSTM(32),
    Dropout(0.2),
    Dense(2)  # Output: [pred_rps_content, pred_rps_media]
])
model.compile(optimizer='adam', loss=quantile_loss(tau=0.95))
```

**Tahap 4 — Output Pelatihan**

Setelah training selesai, akan dihasilkan **3 file** yang wajib disimpan di direktori `./models/` (relatif dari root proyek ini):

```
./models/
├── lstm_quantile_tau095_30s_7030.keras  # Model LSTM tersimpan
├── feat_scaler.pkl                       # Scaler untuk 12 fitur input
└── tgt_scaler.pkl                        # Scaler untuk 2 output target
```

> ⚠️ **Ketiga file ini HARUS tersedia** sebelum menjalankan `docker compose up`. Tanpa file ini, `brain-orchestrator` akan gagal start.

### 3.4 Menjalankan Pelatihan

```bash
# Pastikan dependensi tersedia
pip install tensorflow scikit-learn pandas numpy joblib

# Jalankan pelatihan (butuh dataset/clarknet_features_30s.csv)
python kodetrainingmodel.py

# Setelah selesai, salin output ke direktori models
mkdir -p ../models
cp lstm_quantile_tau095_30s_7030.keras feat_scaler.pkl tgt_scaler.pkl ./models/
```

---

## 4. Quick Start — Menjalankan Testbed

### Langkah A: Pastikan Model Sudah Tersedia

```bash
# Verifikasi ketiga file model ada di tempat yang benar
ls ./models/
# Harus ada: lstm_quantile_tau095_30s_7030.keras  feat_scaler.pkl  tgt_scaler.pkl
```

### Langkah B: Konfigurasi Environment

```bash
cp .env.example .env
```

Isi file `.env` (port default sudah mencukupi untuk pengujian lokal):
```env
HAPROXY_PORT_HTTP=8000
PROMETHEUS_PORT=9090
LOCUST_PORT=8089
```

### Langkah C: Bangun dan Jalankan Semua Kontainer

```bash
docker compose up --build -d
```

### Langkah D: Verifikasi Konektivitas

Tunggu ±30 detik setelah kontainer naik, lalu verifikasi:

```bash
# Cek service utama
curl http://localhost:8000/media     # → response biner (gambar)
curl http://localhost:8000/content   # → response HTML

# Cek health Prometheus
curl http://localhost:9090/-/healthy  # → "Prometheus Server is Healthy."
```

Buka di browser:
- **Dashboard Real-Time**: `http://localhost:3002`
- **Prometheus UI**: `http://localhost:9090`
- **HAProxy Stats**: `http://localhost:8404/stats`

### Langkah E: Verifikasi Brain Orchestrator

```bash
docker logs brain-orchestrator --tail 20
```

Output yang diharapkan:
```
Loading Feature Scaler from /app/models/feat_scaler.pkl...
Loading Target Scaler from /app/models/tgt_scaler.pkl...
Loading Model from /app/models/lstm_quantile_tau095_30s_7030.keras...
LSTM 12-feature model and scalers successfully loaded.
Initializing Cold Pool via Docker Socket API...
Cold Pool Initialization Complete.
Starting Brain Orchestrator (12-feature 30s aggregate) on Prometheus port 8000...
```

---

## 5. Simulasi Beban Kerja (Load Testing)

### A. Pengujian Singkat dengan Locust (Development)

Akses antarmuka web Locust di `http://localhost:8089` dan konfigurasikan jumlah pengguna sesuai kebutuhan.

### B. Pengujian Marathon K6 (4.2 Hari — untuk UAT)

Jalankan skrip otomatis menggunakan `nohup` agar kebal terhadap diskoneksi SSH:

```bash
nohup ./run_full_s2_test.sh > full_test_nohup.log 2>&1 &
```

Pantau progres:
```bash
tail -f full_test_nohup.log
```

### C. Menghentikan K6 Secara Aman (*Graceful Stop*)

```bash
# 1. Temukan ID kontainer K6
docker ps | grep grafana/k6

# 2. Hentikan dengan graceful stop (K6 akan cetak summary sebelum berhenti)
docker stop <CONTAINER_ID>

# 3. Lihat summary hasil akhir
cat k6_test_result.txt | tail -50
```

---

## 6. UAT — User Acceptance Testing

Bagian ini adalah panduan bagi **operator/validator** yang melakukan *User Acceptance Testing*. Tidak perlu memahami kode — cukup ikuti langkah di bawah.

### 6.1 Prasyarat UAT

Sebelum memulai UAT, pastikan kondisi berikut terpenuhi:

| Prasyarat | Cara Verifikasi |
|---|---|
| Docker Desktop berjalan | `docker info` → tidak ada error |
| Model LSTM tersedia | `ls ./models/` menampilkan 3 file |
| Semua kontainer running | `docker compose ps` → semua status `running` |
| Brain orchestrator OK | `docker logs brain-orchestrator` → "model loaded" |

### 6.2 Skenario UAT

---

#### ✅ Skenario 1: Verifikasi Prediksi Proaktif (Fungsi Utama)

**Tujuan**: Memastikan sistem memprediksi lonjakan RPS dan menambah replika *sebelum* beban aktual tiba.

**Langkah**:
1. Pastikan semua kontainer running: `docker compose ps`
2. Jalankan K6:
   ```bash
   nohup ./run_full_s2_test.sh > full_test_nohup.log 2>&1 &
   ```
3. Buka dashboard di `http://localhost:3002`
4. Amati selama minimal **30 menit** pertama pengujian

**Kriteria Lulus**:
- Grafik "Predicted RPS" pada dashboard bergerak *mendahului* grafik "Actual RPS"
- Saat actual RPS naik, jumlah replika kontainer sudah bertambah terlebih dahulu
- Tidak ada proses `docker build` — kontainer diaktifkan langsung dari cold pool

**Cara Verifikasi Replika**:
```bash
# Berapa kontainer media-service yang sedang running
docker ps --filter "label=com.docker.compose.service=media-service" | grep " Up "

# Berapa kontainer content-service yang sedang running
docker ps --filter "label=com.docker.compose.service=content-service" | grep " Up "
```

---

#### ✅ Skenario 2: Verifikasi Cold Pool (Mitigasi Cold Start)

**Tujuan**: Memastikan kontainer siaga (*cold pool*) diaktifkan cepat saat scale-up tanpa proses build ulang.

**Langkah**:
1. Lihat status kontainer cold pool sebelum ada beban:
   ```bash
   docker ps -a --filter "label=com.docker.compose.service=media-service"
   ```
   Kontainer dengan status `Exited` adalah cold pool yang siap diaktifkan.

2. Amati log orchestrator saat terjadi scale-up:
   ```bash
   docker logs brain-orchestrator -f | grep -E "SCALE-UP|Starting"
   ```

**Kriteria Lulus**:
- Log menampilkan `[SCALE-UP] media-service: 1 -> N` diikuti `Starting <nama-kontainer>...`
- **Tidak** ada log `docker build` — hanya perintah `start`
- Kontainer menjadi `running` dalam waktu **< 2 detik** setelah perintah start

---

#### ✅ Skenario 3: Verifikasi GDS & CDT (Anti-Osilasi)

**Tujuan**: Memastikan sistem tidak melakukan scale-down berlebihan (tidak ada efek *ping-pong*).

**Langkah**:
1. Pantau log scale-down saat beban fluktuatif:
   ```bash
   docker logs brain-orchestrator -f | grep -E "SCALE-DOWN|SCALE-UP"
   ```
2. Amati pola log selama minimal **5 menit** pada periode beban turun-naik

**Kriteria Lulus**:
- Setelah `[SCALE-DOWN]`, tidak ada aksi skala lagi dalam **10 detik** berikutnya (ini adalah CDT = Cooldown Timer)
- Scale-down dilakukan secara bertahap (tidak langsung dari N kontainer ke 1)
- Tidak ada pola `scale-up → scale-down → scale-up` dalam interval < 30 detik

---

### 6.3 Metrik Kunci di Prometheus

Query-query berikut dapat dijalankan langsung di UI Prometheus (`http://localhost:9090`):

| Metrik | Query Prometheus | Keterangan |
|---|---|---|
| Prediksi RPS Content | `predicted_rps_content` | Output model LSTM untuk content-service |
| Prediksi RPS Media | `predicted_rps_media` | Output model LSTM untuk media-service |
| Target Replika Content | `target_replicas_content` | Jumlah replika yang ditentukan sistem |
| Target Replika Media | `target_replicas_media` | Jumlah replika yang ditentukan sistem |
| RPS Aktual Content | `sum(sent_rps_content)` | Traffic aktual ke content-service |
| RPS Aktual Media | `sum(sent_rps_media)` | Traffic aktual ke media-service |

### 6.4 Melihat Log Selama UAT

```bash
# Log orchestrator real-time
docker logs brain-orchestrator -f

# Log HAProxy (untuk cek routing dan error)
docker logs haproxy -f

# Summary K6 setelah tes selesai
cat k6_test_result.txt | tail -50
```

---

## 7. Menambahkan Service Baru

Bagian ini menjelaskan cara menambahkan microservice baru ke dalam ekosistem *Proactive Auto-Scaling*. Terdapat **7 file/direktori yang harus dimodifikasi**.

> 📌 Contoh di bawah menggunakan nama service baru: **`api-service`** dengan endpoint `/api`.

---

### File 1: Buat Direktori Service Baru

Buat direktori `api-service/` dengan struktur minimal:

```
api-service/
├── main.go        # Logika HTTP server
└── Dockerfile
```

Contoh `main.go` minimal:
```go
package main

import (
    "fmt"
    "net/http"
    "os"
)

func apiHandler(w http.ResponseWriter, r *http.Request) {
    w.Header().Set("Content-Type", "application/json")
    w.Write([]byte(`{"status": "ok"}`))
}

func main() {
    http.HandleFunc("/api", apiHandler)
    http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
        w.Write([]byte(`{"status": "healthy"}`))
    })
    port := os.Getenv("PORT")
    if port == "" { port = "8000" }
    fmt.Printf("API Service started on port %s\n", port)
    http.ListenAndServe(":"+port, nil)
}
```

---

### File 2: `docker-compose.yml`

Tambahkan definisi service baru **beserta jumlah replika cold pool-nya**:

```yaml
services:
  # ... service existing ...

  api-service:                    # ← TAMBAHKAN BLOK INI
    build:
      context: ./api-service
    image: api-service:latest
    deploy:
      replicas: 5                 # Total kontainer (1 aktif + 4 cold pool)
      resources:
        limits:
          cpus: '0.1'
          memory: '64M'
    environment:
      - CPU_LOAD_ITERATIONS=20000 # Sesuaikan dengan profil CPU service
```

> 💡 `replicas` menentukan jumlah *total* kontainer yang dibuat (termasuk yang "tidur" di cold pool). Brain Orchestrator yang akan mengatur mana yang `running` / `stopped` secara otomatis.

---

### File 3: `haproxy/haproxy.cfg`

Tambahkan ACL routing dan backend baru:

```haproxy
frontend http_front
    bind *:80

    # ACL existing
    acl url_media    path_beg /media
    acl url_content  path_beg /content
    acl url_api      path_beg /api        # ← TAMBAHKAN INI

    use_backend media_back   if url_media
    use_backend content_back if url_content
    use_backend api_back     if url_api   # ← TAMBAHKAN INI

# ... backend existing ...

# ← TAMBAHKAN BACKEND BARU
backend api_back
    balance leastconn
    server-template api 1-5 api-service:8000 check maxconn 18 resolvers docker resolve-prefer ipv4
    #                   ^^^ harus sama dengan nilai 'replicas' di docker-compose.yml
```

---

### File 4: `prometheus/prometheus.yml`

Tambahkan job scrape untuk service baru:

```yaml
scrape_configs:
  # ... job existing ...

  - job_name: 'api-service'       # ← TAMBAHKAN INI
    static_configs:
      - targets: ['api-service:8000']
```

---

### File 5: `brain-orchestrator/main.py`

Ada **4 bagian** di file ini yang perlu dimodifikasi:

#### 5a — Tambahkan Gauge Prometheus (di sekitar baris 32)

```python
# Tambahkan Gauge baru untuk service baru
PRED_RPS_API   = Gauge('predicted_rps_api',   'Predicted RPS for api-service')    # ← TAMBAH
TARGET_REP_API = Gauge('target_replicas_api', 'Target replicas for api-service')  # ← TAMBAH
```

#### 5b — Tambahkan State Variable di `__init__` (di sekitar baris 50)

```python
def __init__(self):
    # ... kode existing ...
    self.cooldown_content = 0
    self.cooldown_media   = 0
    self.cooldown_api     = 0    # ← TAMBAH

    self.current_rep_content = R_MIN
    self.current_rep_media   = R_MIN
    self.current_rep_api     = R_MIN  # ← TAMBAH
```

#### 5c — Daftarkan ke Cold Pool di `_init_cold_pool` (di sekitar baris 63)

```python
def _init_cold_pool(self):
    for srv_name in ["content-service", "media-service", "api-service"]:  # ← TAMBAH "api-service"
        containers = self.docker_client.containers.list(...)
```

#### 5d — Tambahkan Logika Scaling di fungsi `run()` (di sekitar baris 235)

```python
# Di dalam blok `if len(self.history_30s_rps) >= LOOK_BACK:`

# Hitung Replika untuk service baru
req_api = self.calculate_replicas(pred_api)   # ← TAMBAH

# Apply GDS Scaling untuk service baru
self.current_rep_api, self.cooldown_api = self.perform_gds_scaling(
    "api-service", req_api, self.current_rep_api, self.cooldown_api
)  # ← TAMBAH

# Export ke Prometheus
PRED_RPS_API.set(pred_api)               # ← TAMBAH
TARGET_REP_API.set(self.current_rep_api) # ← TAMBAH
```

---

### File 6: `brain-orchestrator/metrics_collector.py`

Tambahkan query Prometheus untuk RPS service baru:

```python
def get_current_metrics():
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:  # max_workers +1
        f_content = executor.submit(query_prometheus, 'sum(sent_rps_content)')
        f_media   = executor.submit(query_prometheus, 'sum(sent_rps_media)')
        f_api     = executor.submit(query_prometheus, 'sum(sent_rps_api)')   # ← TAMBAH

        return {
            'rps_content': f_content.result(),
            'rps_media':   f_media.result(),
            'rps_api':     f_api.result(),    # ← TAMBAH
        }
```

Kemudian update baris konsumsi metrik di `main.py` (di sekitar baris 212):
```python
metrics = get_current_metrics()
tot_rps = metrics['rps_content'] + metrics['rps_media'] + metrics['rps_api']  # ← update
```

---

### File 7: `kodetrainingmodel.py` — Latih Ulang Model LSTM

> ⚠️ **WAJIB dilakukan.** Model LSTM saat ini hanya menghasilkan 2 output (content + media). Menambah service baru berarti model harus dilatih ulang dengan **3 output**.

Perubahan yang diperlukan di `kodetrainingmodel.py`:

```python
# 1. Tambahkan kolom target baru di dataset
targets = ['Content_Service', 'Media_Service', 'API_Service']  # ← dari 2 menjadi 3

# 2. Update arsitektur model: output Dense dari 2 → 3
model = Sequential([
    LSTM(64, return_sequences=True, input_shape=(LOOK_BACK, N_FEATURES)),
    Dropout(0.2),
    LSTM(32),
    Dropout(0.2),
    Dense(3)  # ← GANTI dari Dense(2) menjadi Dense(3)
])

# 3. Di lstm_model.py, update parsing output prediksi
pred_content = max(0.0, float(pred[0][0]))
pred_media   = max(0.0, float(pred[0][1]))
pred_api     = max(0.0, float(pred[0][2]))  # ← TAMBAH
return pred_content, pred_media, pred_api   # ← TAMBAH return value ke-3
```

Jalankan ulang pelatihan:
```bash
python kodetrainingmodel.py
cp lstm_quantile_tau095_30s_7030.keras feat_scaler.pkl tgt_scaler.pkl ./models/
```

---

### Ringkasan Checklist Menambah Service Baru

| # | File / Direktori | Aksi |
|---|---|---|
| 1 | `api-service/` | Buat direktori + `main.go` + `Dockerfile` |
| 2 | `docker-compose.yml` | Tambahkan blok service dengan `replicas` |
| 3 | `haproxy/haproxy.cfg` | Tambahkan ACL + backend baru (cocokkan angka server-template dengan replicas) |
| 4 | `prometheus/prometheus.yml` | Tambahkan job scrape |
| 5 | `brain-orchestrator/main.py` | Tambahkan Gauge, state variable, cold pool entry, dan scaling loop |
| 6 | `brain-orchestrator/metrics_collector.py` | Tambahkan query RPS dan update `tot_rps` |
| 7 | `kodetrainingmodel.py` | Latih ulang model dengan 3 output, ganti file `.keras` dan `.pkl` |

---

## Referensi Teknis

| Parameter | Nilai | Lokasi di Kode |
|---|---|---|
| Lookback LSTM | 60 langkah (30 menit) | `lstm_model.py` — `LOOK_BACK=60` |
| Jumlah Fitur | 12 fitur | `lstm_model.py` — `N_FEATURES=12` |
| Kapasitas per Kontainer | 10 RPS | `main.py` — `MAX_CAPACITY=10.0` |
| Minimum Replika | 1 | `main.py` — `R_MIN=1` |
| Cooldown Timer | 10 detik | `main.py` — `CDT_LIMIT=10` |
| Scale-Down Ratio | 40% per siklus | `main.py` — `SDR=0.4` |
| Kuantil LSTM | τ=0.95 | Nama file model `.keras` |
| Interval Agregasi | 30 detik | `main.py` — `AGGREGATION_WINDOW=30` |

> Jurnal Rujukan Utama: Imdoukh et al. (2019) — *Machine learning-based auto-scaling for containerized applications*.

---

## 8. Adopsi ke Aplikasi Lain (Custom Deployment)

Bagian ini ditujukan bagi **DevOps Engineer, praktisi IT, maupun akademisi** yang ingin menerapkan sistem *LSTM Proactive Auto-Scaling* ini pada **aplikasi mereka sendiri** — bukan hanya mereplikasi testbed ClarkNet.

> **Inti perubahan**: Dataset ClarkNet diganti dengan data trafik aplikasi Anda sendiri. Model dilatih ulang. Infrastruktur (service, HAProxy, Prometheus) disesuaikan. Brain Orchestrator tetap sama — hanya konfigurasinya yang diubah.

### 8.1 Apa yang Tetap vs. Apa yang Berubah

| Komponen | Status | Keterangan |
|---|---|---|
| `brain-orchestrator/main.py` | ✅ **Tetap** (konfigurasi diubah) | Logika MAPE-K, GDS, CDT — tidak perlu diubah |
| `brain-orchestrator/lstm_model.py` | ✅ **Tetap** | Wrapper inferensi LSTM — tidak perlu diubah |
| `brain-orchestrator/metrics_collector.py` | 🔧 **Sesuaikan** | Nama metrik Prometheus disesuaikan dengan service baru |
| `kodetrainingmodel.py` | 🔧 **Jalankan ulang** | Dataset berbeda, output kolom berbeda |
| `docker-compose.yml` | 🔧 **Ganti total** | Definisikan service aplikasi Anda |
| `haproxy/haproxy.cfg` | 🔧 **Ganti total** | Routing ke service Anda |
| `prometheus/prometheus.yml` | 🔧 **Sesuaikan** | Target scrape disesuaikan |
| Dataset (`*.csv`) | 🔄 **Ganti total** | Data historis trafik aplikasi Anda |
| File model (`*.keras`, `*.pkl`) | 🔄 **Latih ulang** | Model baru dari data Anda |
| `dashboard-service` | ✅ **Tetap** | Dashboard generik, membaca dari Prometheus |
| `cadvisor`, `prometheus` | ✅ **Tetap** | Monitoring generik Docker |

---

### 8.2 Prasyarat Adopsi

Sebelum memulai, pastikan aplikasi target memenuhi kondisi berikut:

| Prasyarat | Penjelasan |
|---|---|
| Containerized (Docker) | Setiap service berjalan sebagai Docker container |
| HTTP-based | Service menerima request HTTP (REST API, web server, dll.) |
| Stateless atau dapat di-scale horizontal | Tidak ada state session yang terikat pada 1 instance |
| Data historis trafik tersedia | Minimal **2–4 minggu** data RPS per service (resolusi ≤ 1 menit) |

---

### 8.3 Fase Adopsi (6 Fase)

---

#### 📊 Fase 1: Kumpulkan Data Historis Trafik Aplikasi

Tujuan: mendapatkan data deret waktu RPS (Request Per Second) per service dari aplikasi Anda.

**Opsi A — Dari Prometheus yang sudah ada:**

Jika aplikasi Anda sudah memiliki Prometheus, ekstrak data historis menggunakan API-nya:

```python
# collect_history.py — jalankan SEKALI untuk ekspor data historis
import requests
import pandas as pd
from datetime import datetime, timedelta

PROMETHEUS_URL = "http://<your-prometheus>:9090"

def query_range(query, start, end, step="30s"):
    resp = requests.get(f"{PROMETHEUS_URL}/api/v1/query_range", params={
        'query': query,
        'start': start.isoformat() + 'Z',
        'end':   end.isoformat() + 'Z',
        'step':  step
    })
    data = resp.json()['data']['result']
    if not data:
        return pd.Series(dtype=float)
    values = data[0]['values']
    return pd.Series(
        {datetime.utcfromtimestamp(float(t)): float(v) for t, v in values}
    )

# Sesuaikan: ganti query PromQL dengan metrik aplikasi Anda
# Contoh untuk nginx ingress:
end   = datetime.utcnow()
start = end - timedelta(days=14)  # 2 minggu terakhir

# Ganti query PromQL sesuai service Anda:
rps_serviceA = query_range('sum(rate(http_requests_total{service="service-a"}[30s]))', start, end)
rps_serviceB = query_range('sum(rate(http_requests_total{service="service-b"}[30s]))', start, end)

df = pd.DataFrame({
    'datetime':  rps_serviceA.index,
    'Service_A': rps_serviceA.values,
    'Service_B': rps_serviceB.values,
})
df['rps_total'] = df['Service_A'] + df['Service_B']
df.to_csv('dataset/myapp_features_30s.csv', index=False)
print(f"Saved {len(df)} rows")
```

**Opsi B — Dari log HAProxy/Nginx:**

Jika belum ada Prometheus, parse log akses HAProxy atau Nginx:

```bash
# Contoh: hitung RPS per 30 detik dari log Nginx
# Format log default: [timestamp] "GET /service-a/..." 200
awk '{print $4, $7}' /var/log/nginx/access.log \
  | awk -F: '{print $1":"$2":"int($3/30)*30, $2}' \
  | sort | uniq -c \
  | awk '{print $2, $1}' > rps_raw.txt
```

> **Minimum data yang dibutuhkan**: ≥ 2 minggu dengan resolusi 30 detik = ±40.320 baris. Semakin banyak data, semakin akurat prediksi LSTM.

---

#### 🗂️ Fase 2: Siapkan Dataset dalam Format yang Diperlukan

Format CSV yang wajib dipenuhi:

```csv
datetime,rps_total,Service_A,Service_B
2024-03-01 00:00:00,120.5,80.3,40.2
2024-03-01 00:00:30,135.2,90.1,45.1
2024-03-01 00:01:00,98.7,65.4,33.3
...
```

**Aturan penting**:
- Kolom `datetime`: timestamp ISO 8601, interval konsisten **30 detik**
- Kolom `rps_total`: jumlah RPS semua service (digunakan untuk hitung 12 fitur input LSTM)
- Kolom per service (mis. `Service_A`, `Service_B`): RPS masing-masing service (ini **target output** model)
- **Tidak boleh ada gap** — jika ada menit yang kosong, isi dengan interpolasi atau nilai 0

**Validasi dataset**:
```python
import pandas as pd

df = pd.read_csv('dataset/myapp_features_30s.csv', parse_dates=['datetime'])

print(f"Total baris: {len(df)}")
print(f"Rentang waktu: {df['datetime'].min()} — {df['datetime'].max()}")
print(f"Interval: {df['datetime'].diff().mode()[0]}")
print(f"Missing values:\n{df.isnull().sum()}")
print(f"\nStatistik RPS:")
print(df[['rps_total', 'Service_A', 'Service_B']].describe())
```

Output yang diharapkan:
```
Total baris: 40320
Rentang waktu: 2024-03-01 — 2024-03-15
Interval: 0 days 00:00:30
Missing values: 0 (semua kolom)
```

---

#### 🧠 Fase 3: Latih Ulang Model LSTM untuk Aplikasi Anda

Edit `kodetrainingmodel.py` — ubah hanya **3 bagian** berikut:

```python
# ============================================================
# BAGIAN 1: Ganti path dataset
# ============================================================
CSV_PATH = 'dataset/myapp_features_30s.csv'  # ← GANTI

# ============================================================
# BAGIAN 2: Ganti nama kolom target sesuai service Anda
# (harus cocok persis dengan nama kolom di CSV)
# ============================================================
TARGET_COLS = ['Service_A', 'Service_B']  # ← GANTI (tambah jika lebih dari 2 service)

# ============================================================
# BAGIAN 3: Ganti nama file output model
# (opsional, tapi memudahkan identifikasi)
# ============================================================
MODEL_OUTPUT = 'lstm_quantile_tau095_30s_myapp.keras'  # ← GANTI (opsional)
```

Jalankan pelatihan:
```bash
pip install tensorflow scikit-learn pandas numpy joblib matplotlib
python kodetrainingmodel.py

# Salin output ke direktori models
mkdir -p ../models
cp lstm_quantile_tau095_30s_myapp.keras feat_scaler.pkl tgt_scaler.pkl ./models/
```

> ⏱️ Estimasi waktu training: 5–30 menit tergantung ukuran dataset dan hardware (GPU mempercepat 5–10x).

**Validasi model sebelum deploy:**
```python
# quick_test.py — uji model sebelum digunakan di production
import numpy as np
import joblib
from tensorflow.keras.models import load_model

model      = load_model('./models/lstm_quantile_tau095_30s_myapp.keras', compile=False)
feat_sc    = joblib.load('./models/feat_scaler.pkl')
tgt_sc     = joblib.load('./models/tgt_scaler.pkl')

# Buat input dummy (60 langkah × 12 fitur)
dummy = np.random.rand(60, 12).astype(np.float32)
X     = feat_sc.transform(dummy).reshape(1, 60, 12)
pred  = tgt_sc.inverse_transform(model.predict(X, verbose=0))

print(f"Output model: {pred}")
print(f"Jumlah output: {pred.shape[1]} nilai (harus = jumlah service)")
# Contoh output: [[80.3, 40.2]] → berarti model OK
```

---

#### 🏗️ Fase 4: Adaptasi Infrastruktur Docker

Ganti seluruh `docker-compose.yml` dengan definisi service aplikasi Anda. Berikut template yang dapat langsung disesuaikan:

```yaml
# docker-compose.yml — Template untuk aplikasi kustom
version: '3.8'

services:

  # ── 1. LOAD BALANCER ──────────────────────────────────────
  haproxy:
    image: haproxy:2.8-alpine
    container_name: haproxy
    ports:
      - "8000:80"        # Port publik
      - "8404:8404"      # HAProxy stats + metrics
    volumes:
      - ./haproxy/haproxy.cfg:/usr/local/etc/haproxy/haproxy.cfg:ro
    depends_on:
      - service-a
      - service-b

  # ── 2. SERVICE ANDA (ganti image dan konfigurasi) ─────────
  service-a:
    image: your-registry/service-a:latest   # ← GANTI dengan image aplikasi Anda
    deploy:
      replicas: 5            # total kontainer (termasuk cold pool)
      resources:
        limits:
          cpus: '0.5'        # ← Sesuaikan dengan profil CPU service Anda
          memory: '256M'     # ← Sesuaikan dengan kebutuhan RAM
    environment:
      - DATABASE_URL=...     # ← variabel env service Anda
      - PORT=8080
    # Jika service memerlukan volume/secrets, tambahkan di sini

  service-b:
    image: your-registry/service-b:latest   # ← GANTI
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '0.3'
          memory: '128M'
    environment:
      - PORT=8080

  # ── 3. MONITORING (tidak perlu diubah) ────────────────────
  cadvisor:
    image: ghcr.io/google/cadvisor:latest
    container_name: cadvisor
    privileged: true
    devices:
      - "/dev/kmsg:/dev/kmsg"
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /sys/fs/cgroup:/sys/fs/cgroup:ro
      - /var/lib/docker/:/rootfs/var/lib/docker:ro
    command:
      - '--housekeeping_interval=1s'
      - '--max_housekeeping_interval=1s'
      - '--docker_only=true'

  prometheus:
    image: prom/prometheus:v2.45.0
    container_name: prometheus
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'   # simpan 30 hari
    ports:
      - "9090:9090"
    depends_on:
      - cadvisor
      - haproxy

  dashboard-service:
    build:
      context: ./dashboard-service
    container_name: dashboard-service
    ports:
      - "3002:3002"
    environment:
      - PROMETHEUS_URL=http://prometheus:9090
    depends_on:
      - prometheus

  # ── 4. BRAIN ORCHESTRATOR (sesuaikan env saja) ────────────
  brain-orchestrator:
    build:
      context: ./brain-orchestrator
    container_name: brain-orchestrator
    volumes:
      - ./models:/app/models:ro              # ← path ke folder models Anda
      - ./:/app/compose
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - PROMETHEUS_URL=http://prometheus:9090
      - DASHBOARD_PREDICT_URL=http://dashboard-service:3002/api/predict
      - PRELOAD_CSV=/app/models/myapp_features_30s.csv  # ← CSV historis Anda
      - COMPOSE_PROJECT_NAME=my-app-autoscaling          # ← nama project compose
      - COMPOSE_DIR=/app/compose
      - MODEL_PATH=/app/models/lstm_quantile_tau095_30s_myapp.keras  # ← model Anda
      - FEAT_SCALER_PATH=/app/models/feat_scaler.pkl
      - TGT_SCALER_PATH=/app/models/tgt_scaler.pkl
    depends_on:
      - prometheus
      - dashboard-service
```

**Sesuaikan `haproxy/haproxy.cfg`** untuk routing ke service Anda:

```haproxy
frontend http_front
    bind *:80

    acl url_service_a  path_beg /api/v1    # ← sesuaikan path endpoint service Anda
    acl url_service_b  path_beg /api/v2

    use_backend service_a_back if url_service_a
    use_backend service_b_back if url_service_b
    default_backend service_a_back

backend service_a_back
    balance leastconn
    server-template svc-a 1-5 service-a:8080 check resolvers docker resolve-prefer ipv4
    #                      ^^^ harus sama dengan nilai replicas di docker-compose.yml

backend service_b_back
    balance leastconn
    server-template svc-b 1-3 service-b:8080 check resolvers docker resolve-prefer ipv4

resolvers docker
    nameserver dns1 127.0.0.11:53
    resolve_retries 3
    timeout resolve 100ms
    timeout retry   100ms
    hold valid      100ms
    hold obsolete   100ms
```

**Sesuaikan `prometheus/prometheus.yml`**:

```yaml
global:
  scrape_interval: 1s

scrape_configs:
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']

  - job_name: 'haproxy'
    static_configs:
      - targets: ['haproxy:8404']

  - job_name: 'brain-orchestrator'
    static_configs:
      - targets: ['brain-orchestrator:8000']

  # Tambahkan job per service jika service Anda expose /metrics
  # (tidak wajib jika hanya mengandalkan HAProxy metrics)
  - job_name: 'service-a'
    static_configs:
      - targets: ['service-a:8080']

  - job_name: 'service-b'
    static_configs:
      - targets: ['service-b:8080']
```

---

#### ⚙️ Fase 5: Kalibrasi Parameter `MAX_CAPACITY`

Ini adalah langkah **paling kritis** yang sering terlewat. `MAX_CAPACITY` adalah batas RPS maksimal yang mampu ditangani oleh **1 kontainer** sebelum latensi melampaui SLA.

Nilai ini **berbeda untuk setiap aplikasi** dan **harus diukur secara empiris**.

**Cara mengukur `MAX_CAPACITY` aplikasi Anda:**

```bash
# Langkah 1: Jalankan 1 kontainer saja (nonaktifkan auto-scaling sementara)
docker compose up service-a --scale service-a=1 -d

# Langkah 2: Kirim load bertahap menggunakan wrk atau k6
# Mulai dari 1 RPS, naikkan perlahan sampai latensi P95 > batas SLA Anda
wrk -t4 -c10 -d30s --latency http://localhost:8000/api/v1/endpoint

# Atau gunakan k6:
k6 run --vus 10 --duration 30s - <<'EOF'
import http from 'k6/http';
import { check } from 'k6';
export default function() {
    const res = http.get('http://localhost:8000/api/v1/endpoint');
    check(res, { 'p95 < 500ms': (r) => r.timings.duration < 500 });
}
EOF

# Langkah 3: Catat RPS tertinggi saat P95 MASIH di bawah target SLA Anda
# Nilai itu = MAX_CAPACITY untuk service tersebut
```

Setelah mendapat nilai, edit `brain-orchestrator/main.py`:

```python
# Ubah nilai ini sesuai hasil pengukuran Anda
MAX_CAPACITY = 25.0   # ← GANTI: RPS maks per kontainer sebelum SLA dilanggar
R_MIN = 1             # Minimum replika saat idle
CDT_LIMIT = 10        # Cooldown timer (detik) — bisa disesuaikan
SDR = 0.4             # Scale-down ratio — tidak perlu diubah
```

> 💡 **Tips**: Jika service Anda beda-beda profil CPU (mis. service A berat, service B ringan), gunakan `MAX_CAPACITY` yang berbeda per service dengan membuat fungsi `calculate_replicas` menerima parameter kapasitas:
> ```python
> def calculate_replicas(self, predicted_rps, max_cap=MAX_CAPACITY):
>     return max(R_MIN, math.ceil(predicted_rps / max_cap))
> ```

---

#### 🔧 Fase 6: Sesuaikan Brain Orchestrator untuk Nama Service Anda

Edit `brain-orchestrator/metrics_collector.py` — ganti nama metrik Prometheus:

```python
# metrics_collector.py
# Ganti query sesuai nama metrik HAProxy untuk service Anda
# Format HAProxy: haproxy_backend_http_responses_total{backend="<nama_backend>"}

def get_current_metrics():
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        # Ganti 'sent_rps_content' dan 'sent_rps_media' dengan metrik service Anda
        # Jika menggunakan HAProxy, query-nya seperti ini:
        f_a = executor.submit(query_prometheus,
            'sum(rate(haproxy_backend_http_responses_total{backend="service_a_back"}[30s]))')
        f_b = executor.submit(query_prometheus,
            'sum(rate(haproxy_backend_http_responses_total{backend="service_b_back"}[30s]))')

        return {
            'rps_service_a': f_a.result(),
            'rps_service_b': f_b.result(),
        }
```

Edit `brain-orchestrator/main.py` — ganti nama metrik, nama service, dan nama key dict:

```python
# Gauge Prometheus (nama bisa bebas, tapi harus konsisten)
PRED_RPS_A   = Gauge('predicted_rps_service_a', 'Predicted RPS for service-a')
PRED_RPS_B   = Gauge('predicted_rps_service_b', 'Predicted RPS for service-b')
TARGET_REP_A = Gauge('target_replicas_service_a', 'Target replicas for service-a')
TARGET_REP_B = Gauge('target_replicas_service_b', 'Target replicas for service-b')

# Di __init__:
self.cooldown_a = 0
self.cooldown_b = 0
self.current_rep_a = R_MIN
self.current_rep_b = R_MIN

# Di _init_cold_pool — ganti nama service:
for srv_name in ["service-a", "service-b"]:   # ← nama harus cocok dengan docker-compose
    ...

# Di run() — ganti nama key dan nama service:
metrics = get_current_metrics()
tot_rps = metrics['rps_service_a'] + metrics['rps_service_b']   # ← update key
...
# Pada blok prediksi:
pred_a, pred_b = self.model.predict(feat_matrix)
req_a = self.calculate_replicas(pred_a)
req_b = self.calculate_replicas(pred_b)
self.current_rep_a, self.cooldown_a = self.perform_gds_scaling(
    "service-a", req_a, self.current_rep_a, self.cooldown_a)
self.current_rep_b, self.cooldown_b = self.perform_gds_scaling(
    "service-b", req_b, self.current_rep_b, self.cooldown_b)
PRED_RPS_A.set(pred_a)
PRED_RPS_B.set(pred_b)
TARGET_REP_A.set(self.current_rep_a)
TARGET_REP_B.set(self.current_rep_b)
```

---

### 8.4 Ringkasan Checklist Adopsi ke Aplikasi Baru

```
 Fase 1  □  Kumpulkan data historis RPS ≥ 2 minggu (resolusi 30 detik)
         □  Format: CSV dengan kolom datetime, rps_total, Service_A, Service_B, ...

 Fase 2  □  Validasi dataset: tidak ada gap, tidak ada missing value
         □  Simpan di dataset/myapp_features_30s.csv

 Fase 3  □  Edit kodetrainingmodel.py: ganti CSV_PATH dan TARGET_COLS
         □  Jalankan python kodetrainingmodel.py
         □  Salin .keras + .pkl ke ./models/
         □  Validasi output model dengan quick_test.py

 Fase 4  □  Ganti docker-compose.yml dengan service aplikasi Anda
         □  Sesuaikan haproxy/haproxy.cfg (ACL + backend)
         □  Sesuaikan prometheus/prometheus.yml (tambah scrape target)

 Fase 5  □  Ukur MAX_CAPACITY secara empiris dengan load test
         □  Update MAX_CAPACITY di brain-orchestrator/main.py

 Fase 6  □  Update metrics_collector.py (query Prometheus untuk service Anda)
         □  Update main.py (nama Gauge, nama service di cold pool, key dict)
         □  Update env COMPOSE_PROJECT_NAME di docker-compose.yml

 Deploy  □  docker compose up --build -d
         □  Verifikasi: docker logs brain-orchestrator | grep "model loaded"
         □  Pantau dashboard: http://localhost:3002
```

### 8.5 Troubleshooting Umum

| Masalah | Kemungkinan Penyebab | Solusi |
|---|---|---|
| `brain-orchestrator` crash saat start | File `.keras` / `.pkl` tidak ditemukan | Periksa `MODEL_PATH`, `FEAT_SCALER_PATH`, `TGT_SCALER_PATH` di env |
| Prediksi selalu 0 atau negatif | Data latih tidak memiliki variasi yang cukup | Tambah data latih, periksa normalisasi target scaler |
| Replika tidak pernah berubah | Query Prometheus `rps_*` selalu return 0 | Verifikasi nama metrik dengan `curl http://localhost:9090/api/v1/query?query=<nama_metrik>` |
| Scale-up terlalu agresif | `MAX_CAPACITY` terlalu kecil | Ukur ulang kapasitas per kontainer dengan load test |
| Scale-up terlalu lambat | `AGGREGATION_WINDOW` atau `LOOK_BACK` terlalu besar | Kurangi resolusi agregasi (dari 30s menjadi 15s) dan latih ulang model |
| Cold pool tidak berfungsi | `COMPOSE_PROJECT_NAME` salah | Pastikan sesuai persis dengan nama project Docker Compose Anda (`docker compose ls`) |
| Model overfit, prediksi buruk di data baru | Data latih tidak representatif | Kumpulkan data lebih banyak mencakup pola hari kerja + akhir pekan + peak hours |


