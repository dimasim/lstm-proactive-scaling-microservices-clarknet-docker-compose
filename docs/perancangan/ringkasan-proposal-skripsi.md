# Ringkasan Proposal Skripsi: Implementasi LSTM-Based Proactive Auto-Scaling untuk SLA pada Arsitektur Microservices di Docker Compose

## 1. Metadata

| Field | Nilai |
|---|---|
| Judul | Implementasi LSTM-Based Proactive Auto-Scaling untuk SLA pada Arsitektur Microservices di Docker Compose |
| Penyusun | Dimas Irsyad Maulana / NIM 4.33.22.0.06 / Kelas TI-4A |
| Program Studi | D4-Teknologi Rekayasa Komputer |
| Jurusan | Teknik Elektro |
| Institusi | Politeknik Negeri Semarang |
| Pembimbing I | Suko Tyas Pernanda, S.ST, M.CS. |
| Pembimbing II | Ir. Prayitno, S.ST., M.T., PH.D. |
| Tahun | 2026 |
| Periode pelaksanaan | Maret – Agustus 2026 (6 bulan) |

## 2. Latar Belakang (Ringkasan)

- Arsitektur **microservices** semakin banyak diadopsi karena fleksibel & skalabel; Docker menjadi fondasi kontainerisasinya.
- **Docker Compose** dipilih (bukan Kubernetes) karena cocok untuk industri skala menengah dengan sumber daya terbatas — overhead operasional lebih rendah dibanding control plane Kubernetes.
- **Masalah utama**: mekanisme auto-scaling reaktif berbasis threshold (mis. HPA) baru bertindak **setelah** metrik CPU/memori melampaui batas → menimbulkan *provisioning lag* (bisa puluhan detik), memicu latensi tinggi, antrean membengkak, dan pelanggaran **SLA**.
- Kegagalan satu layanan bisa memicu **cascading failure** pada infrastruktur terbatas (VPS low–mid spec). Anomali seperti memory leak, stuck thread, lonjakan CPU sering tidak terdeteksi dini oleh monitoring konvensional.
- Solusi yang diusulkan: **proactive auto-scaling berbasis LSTM** — memprediksi kebutuhan resource dari pola historis, sehingga scaling bisa dieksekusi *sebelum* lonjakan terjadi.
- **Osilasi Resource & Solusi Mitigasi:** Pengurangan jumlah kontainer secara mendadak saat workload turun dapat memicu ketidakstabilan (osilasi) jika terjadi lonjakan trafik susulan. Untuk mengatasinya, penelitian ini menerapkan strategi **Gradually Decreasing Strategy (GDS)** dan **Cooldown Timer (CDT)** dari jurnal rujukan utama untuk menurunkan jumlah replika kontainer secara bertahap demi efisiensi resource.

### Landasan literatur kunci
| Studi | Temuan relevan |
|---|---|
| Imdoukh et al. (2020), *Neural Computing and Applications* (Q1, Springer) | LSTM dalam MAPE loop memprediksi kebutuhan container akurat, replika minimal, biaya turun |
| Nguyen et al. (2023), *Mathematics* (Q1, MDPI) | ARIMA vs LSTM vs BiLSTM vs GRU pada Google Cluster Data 2011 — LSTM & varian konsisten unggul dari ARIMA |
| Golshani & Ashtiani (2021), *JPDC* (Q1, Elsevier) | Keputusan scaling optimal harus menggabungkan 3 kriteria sekaligus: pencegahan SLA violation, efisiensi resource, minimisasi biaya |
| Nobre et al. (2023), *Applied Sciences* (Scopus) | Anomali memory leak & CPU spike pada Docker tidak terdeteksi dini tanpa mekanisme deteksi anomali khusus |
| Pintye et al. (2024), *Journal of Grid Computing* (Scopus) | Pemilihan metrik telemetri (CPU, RAM, latensi) sangat bergantung karakteristik platform → hasil dari Kubernetes tidak otomatis berlaku di Docker Compose |

### Research Gap yang diklaim
1. Mayoritas riset proactive auto-scaling LSTM dijalankan di atas **Kubernetes** atau cloud komersial skala besar → representasi untuk **Docker Compose** dengan resource terbatas masih minim.
2. Sebagian besar studi hanya fokus pada **akurasi model prediksi**, belum banyak yang mengintegrasikannya ke mekanisme **self-healing otomatis** yang terukur.

## 3. Rumusan Masalah

1. Bagaimana merancang & mengimplementasikan mekanisme proactive auto-scaling berbasis LSTM yang mampu memprediksi pelanggaran SLA sebelum terjadi pada arsitektur microservices di Docker Compose?
2. Sejauh mana integrasi LSTM ke dalam MAPE loop meningkatkan kemampuan self-healing untuk mencegah cascading failure akibat anomali (memory leak, CPU spike)?
3. Bagaimana dampak sistem ini terhadap efisiensi biaya infrastruktur & kepatuhan SLA, dibanding auto-scaling reaktif threshold konvensional, menggunakan ClarkNet Web Server Dataset sebagai profil beban kerja?
4. Bagaimana perbandingan performa model LSTM, GRU, dan Bi-LSTM dalam konteks prediksi beban kerja untuk auto-scaling proaktif pada lingkungan Docker Compose?

## 4. Batasan Masalah

1. Platform orkestrasi **eksklusif Docker Compose** (tidak mencakup Kubernetes, Docker Swarm, AWS ECS/GKE/AKS).
2. Model deep learning yang dikembangkan dan dievaluasi adalah **LSTM (univariat dan multivariat), GRU, serta Bi-LSTM sebagai pembanding arsitektur recurrent**. Perbandingan dengan arsitektur lain seperti Transformer, TCN, atau GNN berada di luar cakupan penelitian ini, meskipun dapat dijadikan acuan dalam analisis komparatif literatur.
3. Parameter SLA didefinisikan sebagai pemeliharaan kinerja sistem agar berada pada batas optimal (menghindari degradasi performa/latency) berdasarkan kapasitas beban kerja maksimum per kontainer ($W_{container}^{max}$). Mengikuti jurnal Imdoukh (2019), tingkat kepatuhan SLA dievaluasi melalui metrik under-provisioning ($\theta_U$), over-provisioning ($\theta_O$), serta durasi penyimpangan SLA ($T_U$ dan $T_O$). Label target prediksi: 1 = berpotensi melanggar SLA / under-provisioned (workload melebihi total kapasitas kontainer aktif, yaitu $W_{predicted}^{total} > R_{current} \times W_{container}^{max}$), 0 = normal.
4. Data beban kerja: **ClarkNet Web Server Dataset (1995)** (`aggregated_clarknet_rps.csv`) berupa pola log akses selama satu minggu penuh yang mencerminkan profil request riil. Dataset ini diagregasikan ke tingkat detik (Requests Per Second - RPS).
5. Layanan microservices dibangun dengan Python/FastAPI: **media-service** (network-heavy/memory bound) dan **content-service** (I/O-heavy/dynamic rendering).
6. Monitoring terbatas pada **Prometheus + Grafana**; metrik: CPU, memori, latensi HTTP, jumlah replika.
7. Evaluasi pada testbed VPS spesifikasi menengah (RAM 8–16GB, CPU 4–8 core) — bukan data center fisik/produksi komersial.
8. Mekanisme penurunan skala kontainer (*scale-down*) dibatasi menggunakan algoritma **Gradually Decreasing Strategy (GDS)** dan **Cooldown Timer (CDT)** demi menghindari osilasi sistem.

## 5. Tujuan

1. Merancang & mengimplementasikan sistem proactive auto-scaling berbasis LSTM dalam siklus MAPE loop otomatis di atas Docker Compose dengan penerapan **Gradually Decreasing Strategy (GDS)** untuk mitigasi osilasi, serta membandingkan performa model LSTM dengan model GRU dan Bi-LSTM sebagai pembanding arsitektur recurrent dari sisi akurasi prediksi (MAE, RMSE, MAPE) dan kecepatan inferensi.
2. Mengevaluasi efektivitas self-healing dalam mencegah pelanggaran SLA & cascading failure lewat injeksi anomali terstruktur — metrik: **Time-To-Scale (TTS)**, **SLA Violation Rate**, latensi respons rata-rata.
3. Menganalisis & mengkuantifikasi efisiensi biaya infrastruktur dibanding auto-scaling reaktif threshold, memakai ClarkNet Web Server Dataset sebagai profil beban simulasi.

## 6. Manfaat

**Teoritis**: bukti empiris efektivitas MAPE loop + LSTM/GRU/Bi-LSTM untuk self-healing di Docker Compose; kontribusi ke ranah **AIOps**; protokol evaluasi komparatif model deep learning recurrent; referensi evaluasi fault injection.

**Praktis**: solusi langsung pakai untuk IT skala menengah tanpa migrasi ke orkestrasi kompleks; blueprint arsitektur untuk tim DevOps; referensi implementasi Python/FastAPI dengan self-healing; peningkatan UX lewat layanan lebih andal.

## 7. Metode Penelitian

### 7.1 Pendekatan
**Research and Development (R&D)** + eksperimental kuantitatif data-driven, dikembangkan dengan **lightweight Agile** (sprint mingguan per komponen). Strategi validasi inti: **Digital Twin Data** — dataset industri diposisikan sebagai "kembaran digital" trafik nyata.

### 7.2 Tahapan SDLC (5 Tahap)

**Tahap 1 — Inisialisasi**
- Studi literatur & identifikasi research gap (jurnal Scopus 2020–2025).
- Akuisisi dataset: ClarkNet Web Server Dataset (1995) berupa berkas log akses yang diagregasikan ke tingkat detik (RPS) guna menyelaraskan dengan pola request web server riil.
- Perancangan arsitektur sistem terintegrasi: (i) App Services (media-service & content-service berbasis FastAPI), (ii) Monitoring Stack (cAdvisor, HAProxy Exporter, dan Prometheus slim), (iii) **Dashboard Service (Golang backend dengan embedded HTML/JS frontend)** untuk monitoring real-time, visualisasi perbandingan, dan kontrol autoscaling, (iv) **The Brain (AI Engine asinkronus berbasis Python)** untuk memuat model prediksi LSTM, GRU, dan Bi-LSTM secara aman.
- Penetapan SLA kuantitatif: berdasarkan kapasitas beban kerja maksimum per kontainer ($W_{container}^{max}$) untuk menjaga latensi tetap optimal, serta evaluasi kestabilan menggunakan metrik under-provisioning ($\theta_U$) dan over-provisioning ($\theta_O$) seperti pada jurnal rujukan. Parameter mitigasi osilasi mengacu pada eksperimen Imdoukh: Cooldown Timer (CDT) = 10 detik dan Scale-Down Ratio (SDR) = 0.40 (40%).

**Tahap 2 — Pra-Produksi** *(3 sprint paralel)*
- **Sprint 1**: pra-pemrosesan data — pembersihan anomali, Min-Max Scaling, sliding window, split 80/20 (train/test). **Re-labeling** target berdasarkan rasio beban terhadap kapasitas kontainer aktif untuk mengantisipasi under-provisioning sesuai parameter kapasitas kontainer milik Imdoukh (scale_up / watch / scale_down / no_action).
- **Sprint 2**: pelatihan dan validasi model **stacked LSTM**, **GRU**, dan **Bi-LSTM**: Model stacked LSTM, GRU, dan Bi-LSTM dibangun menggunakan TensorFlow/Keras. Optimasi hyperparameter dilakukan melalui grid search untuk masing-masing model. Kualitas ketiga model dievaluasi dan dibandingkan menggunakan MAE, RMSE, MAPE, serta waktu inferensi rata-rata. Model terbaik dipilih untuk diintegrasikan ke komponen The Brain.
- **Sprint 3**: pembangunan infrastruktur Docker Compose (IaC via `docker-compose.yml`) + **Workload Injector** berbasis Python Script/Locust (membaca dataset baris per baris dan memutarnya sebagai concurrent request nyata ke media-service dan content-service).

**Tahap 3 — Produksi (Integrasi Sistem)**
- Integrasi MAPE loop penuh: The Brain (REST API, prediksi N-langkah ke depan) ↔ Dashboard Service (sebagai orkestrator dan eksekutor scaling melalui Docker Engine API). Komponen decision maker (planner) menerapkan logika GDS dan CDT: jika hasil prediksi memerlukan scale-down, jumlah replika dikurangi bertahap sesuai SDR (40%) setelah CDT habis.
- Aktivasi Workload Injection: replay pola trafik dataset, Prometheus mengumpulkan metrik real-time, model proaktif (LSTM/GRU/Bi-LSTM) membandingkan kondisi aktual vs pola dataset untuk keputusan proaktif.
- Pembangunan **Dashboard Service** 3 panel: **Source Profile** (identitas profil beban), **Live Comparison** (grafik aktual vs prediksi vs SLA threshold), **Healing Log** (audit trail aksi AI, mis. "02:15 AM – Predicted Spike – Scaled up media-service to 3 instances").

**Tahap 4 — Testing & Evaluasi**
- Uji akurasi prediksi (MAE, RMSE, MAPE) pada partisi test (20%).
- **Workload Injection Test**: 3 skenario (normal, ramp-up bertahap, spike mendadak) → ukur **TTS** & jumlah pelanggaran SLA.
- **Fault Injection Test**: simulasi CPU spike & memory leak via **stress-ng** → validasi self-healing mencegah cascading failure.
- **Uji Perbandingan Model Prediksi**: LSTM, GRU, dan Bi-LSTM dievaluasi pada partisi data pengujian (20%) yang identik untuk membandingkan performa akurasi dan waktu inferensi.
- **Semua skenario dijalankan 2×**: sistem proaktif (LSTM/GRU/Bi-LSTM) vs sistem reaktif threshold (pembanding), untuk perbandingan kuantitatif adil.
- Kriteria lolos: **MAPE <10% & SLA Violation turun**; jika belum, masuk siklus tuning model/perbaikan komponen (iteratif hingga semua skenario lulus).

**Tahap 5 — Analisis & Pelaporan**
- Uji statistik: **Wilcoxon signed-rank** atau **uji-t berpasangan**.
- Interpretasi hasil terhadap rumusan masalah, dokumentasi laporan & naskah publikasi.

### 7.3 Cara Kerja Sistem (4 Komponen)

| # | Komponen | Fungsi |
|---|---|---|
| 1 | **App Services** | Layanan media-service & content-service (Python/FastAPI) sebagai kontainer ringan; menerima beban dari Locust; mengekspos metrik telemetri |
| 2 | **Monitoring Stack** | Prometheus (slim) scraping tiap 15 detik (CPU%, memori MB, latensi HTTP ms, RPS) dari cAdvisor dan HAProxy |
| 3 | **The Brain** | Kontainer Python (AI Engine) — memuat model stacked LSTM / GRU / Bi-LSTM, mengambil data time-series dari Prometheus, menghasilkan prediksi M langkah ke depan, dan mengirimkan rekomendasi scaling |
| 4 | **Dashboard Service** | Layanan terintegrasi (Golang backend + embedded HTML/JS frontend) — menyajikan visualisasi 3 panel (Source Profile, Live Comparison, Healing Log), menerima rekomendasi dari The Brain, dan melakukan eksekusi perintah scaling via Docker Engine API secara aman |

## 8. Tinjauan Pustaka (20 Referensi Utama)

| # | Studi | Fokus relevan |
|---|---|---|
| 1 | Imdoukh et al. (2020) — *Neural Computing and Applications* | LSTM + MAPE loop untuk Docker auto-scaling (rujukan utama proposal) |
| 2 | Golshani & Ashtiani (2021) — *JPDC* | Proactive auto-scaling berbasis **TCN**, 3 kriteria keputusan (SLA, under-utilization, biaya) |
| 3 | Dang-Quang & Yoo (2022) — *Applied Sciences* | Framework **Bi-LSTM** multivariat untuk cegah over/under-provisioning |
| 4 | Nguyen et al. (2023) — *Mathematics* | Perbandingan ARIMA vs **LSTM vs BiLSTM vs GRU** di Google Cluster Data 2011 |
| 5 | Ahmad et al. (2025) — *Journal of Systems and Software* | Perbandingan reactive vs proactive HPA; identifikasi kerentanan HPA reaktif |
| 6 | Suleiman et al. (2024) — LNCS (ICSOC) | LSTM multi-step forecasting untuk keputusan scaling proaktif |
| 7 | Pintye et al. (2023) — *Journal of Grid Computing* | Auto-scaling microservices berbasis ML, referensi **GraphPHPA (LSTM-GNN)** |
| 8 | ProScale (2023) — *IEEE TPDS* | Proactive autoscaling microservices di edge, time-varying workload |
| 9 | GRAF (2024) — IEEE Xplore | Framework autoscaling berbasis **GNN** dengan SLO-awareness |
| 10 | Nobre et al. (2023) — *Applied Sciences* | Deteksi anomali (memory leak, CPU spike) via fault injection pada Docker |
| 11 | ILP-LSTM (2025) — *JTIT* | LSTM + **Integer Linear Programming** untuk edge-cloud scheduling |
| 12 | Pintye et al. (2024) — *Journal of Grid Computing* | Justifikasi pemilihan metrik telemetri untuk model ML autoscaling |
| 13 | e-Informatica (2022) | LSTM vs ARIMA untuk workload microservices |
| 14 | Frontiers (2025) | Kombinasi **Facebook Prophet + LSTM** dalam MAPE loop dengan Prometheus |
| 15 | CNN-LSTM (2024) — *Procedia Computer Science* | Arsitektur hybrid **CNN-LSTM** untuk cloud workload |
| 16 | Al Qassem & Lamees (2023) — *IEEE Access* | Proactive autoscaling berbasis **Random Forest** (non-deep learning) |
| 17 | Kumar & Rana (2018) — *Procedia Computer Science* | Fondasi teoritis LSTM-RNN untuk workload forecasting datacenter |
| 18 | Al-Omari (2025) — *ETASR* | Deteksi anomali microservices berbasis **GCN + LSTM-AE** |
| 19 | Marie-Magdelaine & Ahmed (2020) — IEEE GLOBECOM | Landasan historis ML menggantikan reactive autoscaling |
| 20 | Jani (2024) — *Journal of AI, ML and Data Science* | Implementasi Prometheus + Grafana untuk monitoring microservices |

## 9. Jadwal Kegiatan (Maret–Agustus 2026)

| Tahap | Mar | Apr | Mei | Jun | Jul | Agu |
|---|---|---|---|---|---|---|
| Inisialisasi | ● | | | | | |
| Pra-Produksi | | ● | ● | | | |
| Produksi | | | ● | ● | | |
| Testing & Evaluasi | | | | ● | ● | |
| Analisis & Pelaporan | | | | | ● | ● |

## 10. Anggaran Biaya

| Uraian | Jumlah | Harga Satuan | Total |
|---|---|---|---|
| Cloud VPS IDCloudHost (4 core/8GB RAM/80GB Storage) | 5 bulan | Rp 692.000/bulan | Rp 3.460.000 |
| Lain-lain | 1 | Rp 500.000 | Rp 500.000 |
| **Total** | | | **Rp 3.960.000** |
