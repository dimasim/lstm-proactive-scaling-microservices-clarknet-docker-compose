# Machine Learning-Based Auto-Scaling for Containerized Applications

## 1. Metadata Publikasi

| Field | Nilai |
|---|---|
| Judul | Machine learning-based auto-scaling for containerized applications |
| Penulis | Mahmoud Imdoukh, Imtiaz Ahmad, Mohammad Gh. Alfailakawi |
| Afiliasi | Department of Computer Engineering, College of Engineering and Petroleum, Kuwait University, Kuwait City, Kuwait |
| Jurnal | Neural Computing and Applications (Springer) |
| DOI | 10.1007/s00521-019-04507-z |
| Tipe artikel | Original Article |
| Diterima | 30 Desember 2018 |
| Accepted | 21 September 2019 |
| Diterbitkan online | 8 Oktober 2019 |
| Penerbit | Springer-Verlag London Ltd., part of Springer Nature 2019 |
| Kata kunci | Containerization, Auto-scaling, Proactive controller, Prediction, Neural network, Long short-term memory |

## 2. Ringkasan Abstrak

Paper ini mengusulkan pendekatan **auto-scaling proaktif berbasis machine learning** untuk kontainer Docker, sebagai respons terhadap fluktuasi beban kerja (workload) secara dinamis. Arsitektur auto-scaler mengikuti loop kontrol **MAPE** (Monitor, Analyze, Plan, Execute). Pada fase analisis digunakan model prediksi berbasis **LSTM (Long Short-Term Memory)** untuk memprediksi beban HTTP di masa depan guna menentukan jumlah kontainer yang dibutuhkan lebih awal, sehingga menghilangkan delay akibat proses start/stop kontainer. Pada fase perencanaan, diusulkan strategi **Gradually Decreasing Strategy (GDS)** untuk menghindari osilasi akibat operasi scaling yang terlalu sering.

Temuan utama:
- Akurasi prediksi LSTM setara dengan model ARIMA, tetapi **600 kali lebih cepat**.
- LSTM lebih unggul dibanding ANN dalam metrik auto-scaler terkait provisioning dan elastic speedup.
- Penggunaan model LSTM membantu menggunakan jumlah replika minimum untuk menangani beban kerja mendatang.
- GDS efektif menjaga performa dengan biaya lebih rendah pada kasus lonjakan/penurunan beban kerja mendadak.

## 3. Latar Belakang & Kontribusi (Section 1–2)

### 3.1 Konteks
- Container-based virtualization (mis. Docker) dianggap alternatif ringan dibanding VM berbasis hypervisor: lebih hemat resource, cepat di-deploy, portabel, cocok untuk microservices.
- Elastisitas (auto-scaling) adalah fitur kunci cloud computing: mengakuisisi/melepas resource secara dinamis sesuai kebutuhan beban kerja.
- Dua kategori auto-scaling:
  - **Reactive**: bereaksi terhadap workload/utilization berdasarkan rule & threshold real-time.
  - **Proactive**: memprediksi beban masa depan dari data historis.
- Kebanyakan auto-scaler container yang ada bersifat **reactive threshold-based** — sulit menentukan threshold yang tepat untuk workload dinamis.

### 3.2 Kontribusi Paper
1. Arsitektur high-level auto-scaler khusus untuk container-based virtualization.
2. Model prediksi time series baru menggunakan **LSTM** (jenis RNN yang mengatasi masalah vanishing gradient).
3. **Gradually Decreasing Strategy (GDS)** untuk menangani lonjakan/penurunan beban HTTP secara mendadak.

### 3.3 Struktur Loop MAPE
| Fase | Deskripsi |
|---|---|
| Monitor | Mengumpulkan indikator scaling: resource utilization, HTTP request rate, jumlah transaksi database — pada level fisik/kontainer (CPU, memori) maupun level aplikasi (request rate, response time) |
| Analyze | Memproses data untuk menentukan status saat ini / memprediksi beban masa depan. Keputusan kunci: **scaling time** (reactive vs proactive), **oscillation mitigation**, **adaptivity** |
| Plan | Menentukan jumlah resource yang perlu di-provision/de-provision. Keputusan kunci: **resource estimation**, **scaling method** (vertical vs horizontal) |
| Execute | Eksekusi perintah scaling melalui API cloud provider |

### 3.4 Ringkasan Related Work (Tabel 1)

| Ref | Platform | Indikator | Timing | Adaptif | Mitigasi Osilasi | Teknik Estimasi | Metode Scaling |
|---|---|---|---|---|---|---|---|
| [23] Kan (DoCloud) | Docker | CPU, Mem | Hybrid | ✓ | ✓ | ARMA | Horizontal |
| [24] Li & Xia | Docker | Req.Rate, CPU, Mem | Hybrid | ✓ | ✓ | ARMA | Horizontal |
| [25/34] Ye et al. | Kubernetes | CPU | Proactive | ✓ | ✗ | ARMA | Hor. & Ver. |
| [26] Ciptaningtyas et al. | Docker | – | Hybrid | ✓ | ✗ | ARIMA | Horizontal |
| [27] Meng et al. (CRUPA) | Docker | CPU | Proactive | ✓ | ✗ | ARIMA | Horizontal |
| [36] Baresi et al. | Docker | CPU, Mem, Appl | Proactive | ✓ | ✓ | Control theory | Hor. & Ver. |
| [37] Wu et al. | Docker | CPU | Proactive | ✓ | ✗ | Gray prediction | Horizontal |
| [19] Klinaku et al. (CAUS) | – | Workload intensity | Reactive | ✓ | ✓ | Rule-based | Horizontal |
| [20] Al-Dhuraibi et al. | Docker | CPU, Mem | Reactive | ✓ | ✓ | Rule-based | Vertical |
| [21] Taherizadeh et al. | Kubernetes | CPU, Mem, Appl | Proactive | ✓ | ✗ | Rule-based | Horizontal |
| [22] Zhang et al. | Docker | CPU, Mem | Reactive | ✓ | ✓ | Rule-based | Horizontal |
| [29] Borkowski et al. | – | Task duration | Proactive | ✓ | ✗ | ANN | Horizontal |
| [30] Sangpetch et al. (Thoth) | Docker, Kubernetes | Req, CPU, Mem, Service Time | Proactive | ✓ | ✗ | Q-learning, NN, rule-based | Horizontal |
| [28] Kim et al. (COTA/LTLB) | Docker | Network traffic/bandwidth | Proactive | ✓ | ✗ | Moving Average | Horizontal |

**Kesimpulan gap penelitian**: mayoritas pendekatan reactive rule-based (sulit menentukan threshold) atau statistical (ARMA/ARIMA — lambat, butuh konfigurasi kompleks). Penggunaan machine learning untuk auto-scaling container masih terbatas → motivasi paper ini.

## 4. Arsitektur Sistem (Section 3)

Menggunakan **Docker Swarm** sebagai orchestrator. Terdiri dari 2 jenis node:

1. **Manager Node**
   - Mengorkestrasi cluster & kontainer (deploy/remove/start/stop, ubah jumlah replika).
   - Hosting **auto-scaler** yang menambah elastisitas dengan menyesuaikan jumlah replika berdasarkan prediksi beban.

2. **Worker Node**
   - Hanya menjalankan kontainer Docker.
   - Node 1: hosting **load balancer (HAProxy)** sebagai gateway sistem yang menerima semua incoming request lalu mendistribusikan ke worker node lain.
   - Node 2 & 3: hosting replika **Web application container**; masing-masing punya container balancer lokal untuk distribusi lebih lanjut.

Tools yang digunakan: **HAProxy** (load balancer open-source, juga menangkap statistik request), **Docker Engine**, **Docker Swarm**.

(Diagram: Fig. 1 System architecture)

## 5. Arsitektur Auto-Scaler (Section 4)

Loop MAPE + **Time Series Database** (Fig. 2). Kontribusi utama ada di fase **Analyzer** dan **Planner**.

### 5.1 Monitor
Mengumpulkan dua jenis data:
1. Data jaringan: statistik HTTP request (request per second) dari load balancer.
2. CPU & memory utilization seluruh kontainer di semua node (via Docker Remote RESTful API dari manager node).

### 5.2 Time Series Database
Database khusus timestamp untuk menyimpan data historis. Digunakan untuk melatih ulang model prediksi agar sesuai pola tiap aplikasi (application-specific prediction model).

### 5.3 Analyzer
- Mengambil data terbaru dengan **window size w** secara periodik.
- Preprocessing: normalisasi.
- Model prediksi menggunakan data time series `d0, d1, ..., dw` untuk memprediksi `d(w+1)`.
- Model yang dipakai: **LSTM neural network**.

### 5.4 Planner
Menggunakan output analyzer (predicted workload), bukan current workload, untuk memutuskan jumlah replika. Scaling **horizontal only**.

**Persamaan (1) — Estimasi Replika:**
```
R_estimated = ceil( W_total_predicted / W_max_container )
```
- `W_total_predicted` = total predicted incoming workload (dari analyzer)
- `W_max_container` = kapasitas maksimum workload per kontainer per detik (ditentukan dari stress test saat development)

**Algorithm 1 — Planner Algorithm**
```
Input: R_min, R_current, W_total_predicted, W_max_container, CDT, SDR
Output: Scaling commands

1: R_estimated = ceil(W_total_predicted / W_max_container)
2: if R_estimated == R_current then
3:     sendCommand(NONE)
4: else if R_estimated > R_current then
5:     sendCommand(SCALE_UP, R_estimated)
6:     restart CDT
7: else if CDT timed out then
8:     restart CDT
9:     R_estimated = floor((R_current - R_estimated) * (1 - SDR))
10:    R_estimated = max(R_current - R_estimated, R_min)
11:    sendCommand(SCALE_DOWN, R_estimated)
12: else
13:    sendCommand(NONE)
14: end if
```

Penjelasan logika:
- Jika `R_estimated == R_current` → tidak ada perintah scaling.
- Jika `R_estimated > R_current` → **scale-up**, cooldown timer (CDT) direstart.
- Jika `R_estimated < R_current` → **scale-down** hanya dieksekusi jika CDT sudah timeout; scale-down mengikuti **Gradually Decreasing Strategy (GDS)** dengan **Scale-Down Ratio (SDR)** agar jumlah kontainer yang dihentikan tidak sekaligus banyak, hingga mencapai `R_min`.

**Parameter eksperimen**: CDT = 10 detik, SDR = 0.40 (40%), R_min = 5 replika.

Tujuan GDS: mencegah osilasi akibat scaling operation yang terlalu sering.

### 5.5 Executor
Menerima command dari planner, mengubah jumlah replika aktual via API Docker daemon (Docker Engine).

## 6. Model Prediksi (Section 5)

### 6.1 LSTM — Dasar Teori
LSTM adalah pengembangan dari RNN yang mengatasi masalah **vanishing gradient**. Cell state (garis putus merah pada Fig. 3) menyimpan informasi yang mengalir dari 3 gate: **forget, input, output**. Setiap gate berisi fungsi sigmoid + operasi perkalian.

Langkah pemrosesan tiap unit LSTM (input x(t) & hidden state sebelumnya h(t-1)):

**(2) Forget gate:**
```
f(t) = sigmoid( W_f · [h(t-1), x(t)] + b_f )
```

**(3) Kandidat cell state baru:**
```
C̃(t) = tanh( W_C · [h(t-1), x(t)] + b_C )
```

**(4) Input gate:**
```
i(t) = sigmoid( W_i · [h(t-1), x(t)] + b_i )
```

**(5) Cell state final:**
```
C(t) = f(t) * C(t-1) + i(t) * C̃(t)
```

**(6) Output gate:**
```
o(t) = sigmoid( W_o · [h(t-1), x(t)] + b_o )
```

**(7) Hidden state final:**
```
h(t) = o(t) * tanh(C(t))
```

### 6.2 Arsitektur Neural Network (Fig. 4)
- **Input layer**: 10 neural cells (menerima 10 langkah waktu workload sebelumnya)
- **Hidden layer**: 30 LSTM units
- **Output layer**: 1 neural cell (prediksi 1 langkah waktu ke depan)

Arsitektur dibuat sederhana agar model generalisasi baik & menghindari overfitting untuk dataset input berbeda-beda.

### 6.3 Prediksi Single-Step vs Multi-Step
- **Single-step**: memprediksi 1 nilai berikutnya dari 10 observasi lalu (Fig. 5).
- **Multi-step** (lebih relevan untuk auto-scaler): dua strategi:
  - **Direct**: melatih model langsung memprediksi nilai N-langkah ke depan (Fig. 6).
  - **Recursive**: prediksi nilai berikutnya ditambahkan kembali ke histori untuk memprediksi nilai selanjutnya, dst. **Kelemahan**: error terakumulasi tiap langkah (Fig. 7).

## 7. Eksperimen & Evaluasi (Section 6)

### 7.1 Dataset — Worldcup98
- ~1.3 miliar total HTTP request log dari situs Web FIFA World Cup 1998 (30 April – 26 Juli 1998).
- Preprocessing: agregasi log per detik → 1 record = total workload (request) per detik.

**Tabel 2 — Pembagian Dataset**

| Ref | Dataset | Ukuran | Penggunaan |
|---|---|---|---|
| S1 | Workload per detik | 5.244.199 record (1998-04-30 21:30:00 s.d. 1998-06-30 19:30:59, ~70%) | Evaluasi |
| S2 | Workload per detik | 2.255.274 record (1998-06-30 19:31:00 s.d. 1998-07-26 21:59:00, ~30%) | Evaluasi |
| M1 | Workload per menit (simplifikasi: max workload tiap 60 detik) | 87.710 record | Training |
| M2 | Workload per menit | 37.590 record | Evaluasi |

Dataset disederhanakan dengan mengambil **nilai maksimum workload per menit** — mempercepat training, meningkatkan generalisasi, mengurangi overfitting, tetap mempertahankan pola dataset asli (Fig. 8 vs Fig. 9).

Data M1 diskalakan ke rentang [-1, 1]; 10% M1 dipakai validasi. S1, S2, M2 dipakai evaluasi.

### 7.2 Desain Eksperimen

**Eksperimen 1** — Melatih & mengevaluasi model prediksi (LSTM vs ANN vs ARIMA).

Konfigurasi **ANN** (Tabel 3):
| Parameter | Nilai |
|---|---|
| Input size | 10 |
| Output size | 1 |
| Hidden layers | 1 |
| Hidden neural cells | 30 |
| Activation function | ReLU |
| Loss function | MSE |
| Optimizer | Adam |
| Batch size | 64 |
| Epochs | 50 |
| Early stopping patience | 2 |

Konfigurasi **LSTM** (Tabel 4):
| Parameter | Nilai |
|---|---|
| Input size | 10 |
| Output size | 1 |
| LSTM layers | 1 |
| LSTM units | 30 |
| Kernel initializer | Lecun uniform |
| Loss function | MSE |
| Optimizer | Adam |
| Batch size | 64 |
| Epochs | 50 |
| Early stopping patience | 2 |

Dua varian tiap model dilatih: **1-step** (prediksi 1 menit ke depan) dan **5-step** (prediksi 5 menit ke depan, strategi direct multi-step). Implementasi: Keras + TensorFlow backend, dilatih pada TPU Colab. ARIMA: Python StatsModel, p=4, d=1, q=0 (sesuai [26]).

**Eksperimen 2** — Simulasi + lingkungan nyata (real environment) untuk menguji responsivitas auto-scaler penuh.
- Simulasi: Python, mensimulasikan MAPE loop menggunakan subset dataset worldcup98. Delay ditambahkan untuk mensimulasikan startup time kontainer. 3 worker node → penambahan 3 kontainer dilakukan paralel.
- Real environment: 4 virtual node dengan Docker Engine, diorkestrasi Docker Swarm (1 manager, 3 worker). Manager menjalankan kontainer auto-scaler (MAPE loop + time series DB kustom). Analyzer mengambil workload HTTP 5 detik terakhir untuk memprediksi detik berikutnya (opsional: recursive multi-step untuk beberapa detik ke depan). Eksekusi via Docker-Py API. Beban HTTP di-generate menggunakan **Apache JMeter**.

### 7.3 Metrik Evaluasi

**Prediksi:**
```
(8)  MSE(y, ŷ) = (1/n) Σ (yi - ŷi)²
(9)  R² = 1 - [Σ(yi - ŷi)²] / [Σ(yi - ȳi)²]
(10) MAE(y, ŷ) = (1/n) Σ |yi - ŷi|
(11) RMSE(y, ŷ) = sqrt[(1/n) Σ (yi - ŷi)²]
```
Kecepatan prediksi: rata-rata waktu dari 30 percobaan.

**Auto-scaler (provisioning & elastic speedup, mengacu [47, 48]):**
```
(12) θ_U [%] = under-provisioning metric
     = (100/T) Σ max(demand(t) - supply(t), 0)/demand(t) · Δt

(13) θ_O [%] = over-provisioning metric
     = (100/T) Σ max(supply(t) - demand(t), 0)/demand(t) · Δt

(14) T_U [%] = time share under-provisioned
(15) T_O [%] = time share over-provisioned

(16) η (elasticity speedup) =
     [ (θ_U,n/θ_U,a) · (θ_O,n/θ_O,a) · (T_U,n/T_U,a) · (T_O,n/T_O,a) ]^(1/4)
```
Subscript `a` = dengan auto-scaler, `n` = tanpa auto-scaler. η > 1 → auto-scaler memberi keuntungan; η < 1 → kerugian performa.

## 8. Hasil Eksperimen (Section 6.4)

### 8.1 LSTM vs ARIMA (Tabel 5)

| Model | LSTM (Single) | ARIMA (Single) | LSTM (Multiple) | ARIMA (Multiple) |
|---|---|---|---|---|
| MAE | 0.0141 | **0.0136** | 0.0186 | **0.0181** |
| RMSE | 0.0185 | **0.0177** | 0.0246 | **0.0238** |
| Speed (ms) | **4.9** | 3364.7 | **47.5** | 6205.3 |

→ Akurasi LSTM ≈ ARIMA, tetapi LSTM **600× lebih cepat** (single-step) dan **130× lebih cepat** (multi-step). ARIMA dianggap tidak layak untuk real-time sehingga tidak dipakai di tahap selanjutnya.

### 8.2 LSTM vs ANN — Kecepatan (Tabel 6)

| Model | ANN 1-step | LSTM 1-step | ANN 5-step | LSTM 5-step |
|---|---|---|---|---|
| Speed (ms) | **0.8** | 1.6 | **0.8** | 1.7 |

ANN lebih cepat, tapi LSTM tetap < 2 ms → cukup cepat untuk real-time auto-scaling.

### 8.3 LSTM vs ANN — Akurasi (Tabel 7)

| Dataset | Metrik | ANN 1-step | LSTM 1-step | ANN 5-step | LSTM 5-step |
|---|---|---|---|---|---|
| M1 | MSE | 0.0017 | **0.0006** | **0.0009** | 0.0010 |
| M1 | R² | 0.9430 | **0.9790** | **0.9690** | 0.9650 |
| M2 | MSE | 0.0017 | **0.0005** | 0.0018 | 0.0020 |
| M2 | R² | 0.9360 | **0.9810** | **0.9320** | 0.9270 |
| S1 | MSE | 0.0018 | **0.0009** | **0.0006** | 0.0009 |
| S1 | R² | 0.9320 | **0.9670** | **0.9760** | 0.9660 |
| S2 | MSE | 0.0019 | **0.0014** | 0.0012 | **0.0014**† |
| S2 | R² | 0.9100 | **0.9330** | **0.9410** | 0.9320 |

Untuk prediksi 1-step, LSTM konsisten unggul (MSE 1.5–3.5× lebih rendah dari ANN). Untuk 5-step, ANN sedikit lebih baik tapi selisihnya kecil (dianggap tidak signifikan).

### 8.4 Evaluasi Auto-Scaler (Tabel 8)

| Metrik | No auto-scaling | ANN (1 step) | LSTM (1 step) | ANN (5 steps) | LSTM (5 steps) |
|---|---|---|---|---|---|
| θ_U | 3.29 | 0.94 | **0.48** | 5.07 | **1.88** |
| θ_O | 3.06 | **3.51** | 4.28 | **1.42** | 2.62 |
| T_U | 57.95 | 26.50 | **15.85** | 76.50 | **42.55** |
| T_O | 57.05 | **73.20** | 89.10 | **32.55** | 57.25 |
| η (elasticity speedup) | 1.00 | 1.50 | **1.84** | 1.17 | **1.29** |

Interpretasi:
- **LSTM lebih baik** dalam θ_U dan T_U → jarang under-provisioned, dan durasi under-provisioning lebih singkat.
- **ANN lebih baik** dalam θ_O dan T_O → jarang over-provisioned, durasi over-provisioning lebih singkat.
- Namun secara keseluruhan **LSTM unggul** karena skor elasticity speedup (η) lebih tinggi baik untuk 1-step (1.84 vs 1.50) maupun 5-step (1.29 vs 1.17).

### 8.5 Hasil Kualitatif Lain
- Fig. 13–14: jumlah kontainer yang di-start oleh ANN vs LSTM auto-scaler pada dataset M2.
- Fig. 15–16: perbandingan supply vs demand kontainer — LSTM lebih match dengan demand dibanding ANN.
- Fig. 17 (real environment): jumlah replika merespons instan saat workload naik; namun saat workload turun mendadak, replika **tidak langsung diturunkan** (efek GDS) — replika diturunkan secara bertahap untuk mengantisipasi lonjakan susulan.

## 9. Kesimpulan & Rencana Riset Selanjutnya (Section 7)

**Kesimpulan:**
- Diusulkan arsitektur sistem auto-scaler untuk aplikasi Docker berbasis model machine learning, dikemas dalam kontainer agar mudah di-deploy/migrasi.
- Model prediksi berbasis LSTM belajar dari time series historis (statistik request) untuk memprediksi workload masa depan secara akurat.
- GDS efektif mencegah osilasi akibat lonjakan workload mendadak.
- LSTM mencapai akurasi setara ARIMA dengan speedup 600× dalam waktu prediksi.
- LSTM unggul atas ANN dalam metrik provisioning & elastic speedup.
- Arsitektur mampu menurunkan jumlah replika kontainer secara bertahap, efisien menangani lonjakan tajam.

**Rencana riset ke depan:**
1. Menerapkan model **bidirectional LSTM** untuk prediksi yang lebih akurat.
2. Studi ini hanya mengeksplorasi **horizontal scaling**; perluasan ke **vertical scaling** (menambah/mengurangi resource CPU/memori pada kontainer yang sama) dan/atau kombinasi horizontal+vertical scaling menjadi arah penelitian berikutnya.

## 10. Referensi Kunci yang Disebut dalam Ringkasan Ini

- [23] Kan (2016) — DoCloud, ARMA reactive+proactive
- [26] Ciptaningtyas et al. (2017) — ARIMA lag order 4, error rate 7.83%
- [27] Meng et al. (2016) — CRUPA, ARIMA, error CRUPA 6.5% vs TBA 16.9%
- [29] Borkowski et al. (2016) — ANN untuk prediksi task duration & resource utilization
- [30] Sangpetch et al. (2017) — Thoth: Q-learning, ANN, rule-based (Q-learning unggul 22%/29%)
- [32] Hochreiter & Schmidhuber (1997) — LSTM original paper
- [42] Arlitt & Jin (2000) — Worldcup98 dataset characterization
- [47] Herbst et al. (2016) — metrik provisioning/elastic speedup
- [48] Bauer et al. (2018) — nilai service demand estimation untuk auto-scaling

*(Daftar referensi lengkap [1]–[48] tersedia di dokumen asli, tidak direproduksi penuh di sini untuk mematuhi batasan hak cipta.)*

---
**Catatan konversi**: Dokumen ini adalah ringkasan terstruktur dari file PDF asli (`imdoukh2019.pdf`) yang disusun ulang dalam Bahasa Indonesia dengan istilah teknis dipertahankan dalam Bahasa Inggris, ditujukan untuk memudahkan pembacaan presisi oleh sistem AI (mempertahankan seluruh angka, persamaan, dan struktur tabel penting).
