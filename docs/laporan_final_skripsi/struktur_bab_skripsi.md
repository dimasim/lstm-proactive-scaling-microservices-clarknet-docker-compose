# Rancangan Struktur Bab & Sub-Bab Skripsi

## Judul Skripsi
**IMPLEMENTASI LSTM-BASED PROACTIVE AUTO-SCALING UNTUK SLA PADA ARSITEKTUR MICROSERVICES DI DOCKER COMPOSE**

> Dirumuskan berdasarkan format skripsi **Nafiis Abyan Ilyasa** (Program Studi Teknologi Rekayasa Komputer, Politeknik Negeri Semarang, 2026) yang menggunakan struktur **5 Bab** dengan pola *Pendahuluan → Tinjauan Pustaka → Kegiatan Pelaksanaan → Analisis & Pembahasan → Kesimpulan*.

---

## HALAMAN AWAL (Pra-Bab)
- Halaman Judul
- Halaman Pernyataan Keaslian
- Halaman Pengesahan Pembimbing & Penguji
- Kata Pengantar
- Abstrak (Bahasa Indonesia & Bahasa Inggris)
- Daftar Isi
- Daftar Gambar
- Daftar Tabel
- Daftar Lampiran

---

## BAB I — PENDAHULUAN

### 1.1 Latar Belakang
Narasi problem statement: pertumbuhan arsitektur *microservices*, tantangan *bursty workload*, keterbatasan *reactive auto-scaling* (cold start ~25s di Google Borg), motivasi pendekatan proaktif berbasis LSTM. Diakhiri dengan justifikasi pemilihan dataset ClarkNet HTTP.

### 1.2 Tujuan Penelitian
Butir-butir tujuan: (1) merancang & mengimplementasikan sistem *proactive auto-scaling* berbasis LSTM pada Docker Compose, (2) mengevaluasi dampak terhadap SLA (*Error Rate* & Latency P99), (3) membandingkan performa LSTM dengan model *baseline* (ARIMA, GRU, BiLSTM, DUCFF).

### 1.3 Manfaat Penelitian
Manfaat teoritis (pengembangan literatur proaktif auto-scaling berbasis DL) dan manfaat praktis (blueprint implementasi sistem proaktif pada Docker Compose).

### 1.4 Batasan Masalah
- Dataset: ClarkNet HTTP (7 hari, trafik riil)
- Platform: Docker Compose (bukan Kubernetes/Swarm)
- Model prediksi: LSTM 1-step ahead (bukan *multi-step*)
- Skala: uji pada 2 layanan (*media-service* dan *content-service*)
- SLA Target: *Error Rate* < 5% dan Latency P99 < 500 ms

### 1.5 Sistematika Penulisan
Paragraf singkat menjelaskan isi tiap bab.

---

## BAB II — TINJAUAN PUSTAKA

### 2.1 Penelitian Terkait *(Related Work)*
Tabel/ringkasan 7–9 paper terkait, dibandingkan dari dimensi: Platform, Dataset, Model, Metrik Evaluasi, Kelebihan & Kelemahan. *(Sumber: Imdoukh [1], Ahmad [5], Guruge [10], Stefan [2], Singh [3], Trivedi [9], Saxena [8])*

### 2.2 Dasar Teori

#### 2.2.1 Arsitektur Microservices & Docker Compose
Definisi *microservices*, keunggulan vs monolitik, peran Docker Compose sebagai orkestrasi ringan.

#### 2.2.2 Service Level Agreement (SLA)
Definisi SLA, metrik utama (*Error Rate*, Latency P50/P90/P99), konsekuensi pelanggaran SLA.

#### 2.2.3 Auto-Scaling: Reaktif vs Proaktif
Perbandingan paradigma *reactive threshold-based* (HPA) vs *proactive prediction-based*. Konsep *cold start* dan dampaknya terhadap SLA.

#### 2.2.4 MAPE-K Control Loop
Fase *Monitor-Analyze-Plan-Execute* sebagai kerangka arsitektur sistem kontrol adaptif. Referensi: Guruge [10], Imdoukh [1].

#### 2.2.5 Long Short-Term Memory (LSTM)
Arsitektur LSTM: *forget gate*, *input gate*, *output gate*, *cell state*. Persamaan matematis (f(t), i(t), C(t), o(t), h(t)). Keunggulan LSTM atas RNN biasa (*vanishing gradient*) dan atas ARIMA (kecepatan 600×).

#### 2.2.6 Dataset ClarkNet HTTP
Asal-usul dataset, karakteristik (7 hari, trafik web server NASA-Clarknet, ~1.7 juta req/jam), tingkat volatilitas yang tinggi vs WorldCup98 milik Imdoukh.

#### 2.2.7 Metrik Evaluasi Model
- **Prediksi**: MSE, RMSE, MAE, R² — definisi dan persamaan
- **Auto-Scaler**: θ_U (*Under-Provisioning*), θ_O (*Over-Provisioning*), T_U, T_O, η (*Elasticity Speedup*) — persamaan lengkap dari Imdoukh [1]

#### 2.2.8 Teknologi Pendukung
HAProxy, Prometheus, cAdvisor, K6 (*load testing*), Docker Socket API.

---

## BAB III — METODOLOGI / KEGIATAN PELAKSANAAN

### 3.1 Kerangka Kerja Penelitian
Diagram alur keseluruhan tahapan penelitian (dari pengumpulan data → pelatihan model → implementasi sistem → evaluasi SLA).

### 3.2 Dataset dan Preprocessing Data

#### 3.2.1 Sumber dan Karakteristik Dataset ClarkNet
Deskripsi lengkap dataset, rentang waktu, volume, format log HTTP.

#### 3.2.2 Eksplorasi Data (EDA)
Analisis distribusi, plot trafik per jam/hari, deteksi anomali & puncak lonjakan.

#### 3.2.3 Preprocessing & Agregasi
- Resample 1-detik → 1-menit (agregasi *Max*)
- Normalisasi *MinMaxScaler*
- Penerapan *Savitzky-Golay Filter* (Window=61, Poly=3)
- Split data: 70% train (M1/S1) — 30% test (M2/S2), mengacu Imdoukh [1]

### 3.3 Perancangan Sistem Proactive Auto-Scaling

#### 3.3.1 Arsitektur Sistem MAPE-K
Diagram arsitektur lengkap: K6 → HAProxy → Prometheus → Brain Orchestrator (LSTM Predictor) → Docker Socket API.

#### 3.3.2 Komponen [MONITOR]: Metrics Collector
Peran HAProxy dan Prometheus dalam mengumpulkan metrik RPS secara *real-time*.

#### 3.3.3 Komponen [ANALYZE]: LSTM Predictor Engine
Desain arsitektur model: Input (60 langkah), Hidden (1 layer LSTM, 30 units), Output (1 prediksi). Justifikasi *window size* 60 menit (vs 10 menit Imdoukh).

#### 3.3.4 Komponen [PLAN & EXECUTE]: GDS Auto-Scaler
- Rumus estimasi replika: R_est = ⌈W_total_pred / W_max_container⌉
- Algoritma GDS (*Gradually Decreasing Strategy*): pseudocode/flowchart
- Parameter: CDT=10s, SDR=0.40, R_min=1

### 3.4 Pelatihan Model LSTM

#### 3.4.1 Konfigurasi Model dan Hyperparameter
Tabel lengkap: Epochs, Batch Size, Optimizer, Loss Function, Early Stopping, dll.

#### 3.4.2 Model Pembanding (Baseline)
Deskripsi singkat model ARIMA, GRU, BiLSTM, DUCFF yang diuji sebagai *baseline*.

### 3.5 Lingkungan dan Konfigurasi Pengujian

#### 3.5.1 Spesifikasi Perangkat Keras dan Perangkat Lunak
Tabel III (GCP AMD EPYC 7B12, 16 vCPU, 32GB RAM, Ubuntu 22.04, Docker v29.1.3, TensorFlow ≥ 2.16.1, K6, HAProxy v2.8, Prometheus v2.45.0).

#### 3.5.2 Konfigurasi Layanan Kontainer
Limit CPU & Memory untuk *media-service* dan *content-service*.

#### 3.5.3 Skenario Load Testing K6
Konfigurasi K6: executor *ramping-arrival-rate*, Pre-allocated VUs=100, Max VUs=2000.

---

## BAB IV — ANALISIS DAN PEMBAHASAN

### 4.1 Evaluasi Performa Model Prediksi (Offline)

#### 4.1.1 Hasil pada Resolusi 1-Menit (M1 & M2)
**Tabel I** — MSE, R² untuk DUCFF, ARIMA, ANN, LSTM, GRU, BiLSTM. Narasi: LSTM mencapai R²=0.997 tertinggi.

#### 4.1.2 Hasil pada Resolusi 1-Detik (S1 & S2)
Analisis mengapa R² negatif (domain shift), dan mengapa MSE jadi acuan primer. LSTM mencatat MSE terendah.

### 4.2 Evaluasi Performa Auto-Scaler (Simulasi Offline)

#### 4.2.1 Hasil Provisioning Metrics
**Tabel II** — θ_U, θ_O, T_U, T_O, η untuk semua model. Analisis komparatif: LSTM unggul dengan η=1.15.

#### 4.2.2 Analisis Demand vs Supply (Kualitatif)
Grafik perbandingan demand vs supply untuk LSTM (langsung merespons lonjakan, GDS saat turun).

### 4.3 Evaluasi SLA via K6 (Online)

#### 4.3.1 Analisis Error Rate
*Zero downtime* (0.00%) — interpretasi dan korelasi dengan θ_U=8.89%.

#### 4.3.2 Analisis Latency Distribution
Latency rata-rata 162.68 ms, P90=294.53 ms, P99=2.86 detik. Grafik distribusi P50-P99. Analisis penyebab outlier latency tinggi (0.17% *cold start* gap).

#### 4.3.3 Perbandingan dengan Target SLA
Tabel validasi: Error Rate 0.00% < target 5% ✓, P99 2.86 s < target tidak terpenuhi sesaat saat *spike* — analisis penyebab dan dampak terhadap SLA keseluruhan.

---

## BAB V — KESIMPULAN

### 5.1 Kesimpulan
Butir-butir ringkasan temuan utama: keberhasilan menekan Under-Provisioning, mempertahankan SLA, dan superioritas LSTM atas model *baseline*.

### 5.2 Saran
- Eksplorasi *time-window granularity* menengah (5-detik/10-detik + *Max Aggregation*) untuk menekan θ_U lebih jauh
- Implementasi prediksi *Multivariate* dengan metrik CPU/RAM
- Eksplorasi *Vertical Scaling* sebagai instrumen pelengkap horizontal scaling
- Uji pada dataset yang lebih panjang (> 7 hari) untuk validasi generalisasi

---

## DAFTAR PUSTAKA
Semua referensi ([1]–[12+]) sesuai format IEEE.

## LAMPIRAN
- Lampiran A: Kode Sumber Model LSTM (Notebook 02)
- Lampiran B: Kode Sumber Auto-Scaler (Brain Orchestrator)
- Lampiran C: Konfigurasi Docker Compose (`docker-compose.yml`)
- Lampiran D: Skrip K6 Load Testing
- Lampiran E: Tabel Data Lengkap Evaluasi (jika tidak muat di bab utama)
