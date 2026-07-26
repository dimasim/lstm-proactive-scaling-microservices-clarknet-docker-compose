# Phase 4: Brain Orchestrator (LSTM-Based Proactive Auto-Scaling)

Tujuan dari fase ini adalah membangun otak utama dari sistem (Brain Orchestrator) menggunakan bahasa pemrograman Python. Sistem ini akan membaca metrik (RPS dan CPU) secara langsung (real-time), memprediksi beban masa depan dengan model LSTM, dan menjalankan auto-scaling sebelum SLA 500ms terlanggar.

## User Review Required

> [!IMPORTANT]
> Karena Anda ingin melanjutkan pembuatan *Brain Orchestrator* ini di **CHAT BARU**, mohon jadikan dokumen rencana implementasi ini sebagai referensi awal (bisa di-*copy/paste*) saat Anda membuka sesi chat baru nanti. Anda tidak perlu menyetujui eksekusi di chat ini.

## Open Questions

> [!WARNING]
> Sebelum melanjutkan ke chat baru, ada dua keputusan desain utama yang perlu Anda tentukan nanti:
> 1. **Framework ML:** Apakah Anda lebih memilih **PyTorch** atau **TensorFlow/Keras** untuk membangun model LSTM-nya? (Secara default saya sarankan TensorFlow/Keras karena integrasi datanya biasanya lebih ramah pemula, namun PyTorch lebih populer di riset akademik).
> 2. **Sumber Metrik Real-time:** Untuk membaca RPS saat ini, apakah kita akan me-*scrape* halaman statistik CSV bawaan dari **HAProxy** (`/stats;csv`), atau kita *inject* trafik buatan *ClarkNet* secara bertahap menggunakan *script test* sambil langsung memberikan nilai RPS-nya ke *Brain Orchestrator*? (Opsi *scrape* HAProxy jauh lebih realistis).

## Proposed Changes

Arsitektur Brain Orchestrator akan terdiri dari 1 _service_ (atau _script_) Python baru di dalam repositori proyek, yang dijalankan di *background*.

### 1. `brain-orchestrator/` (Service Baru)

Pembuatan direktori baru untuk otak sistem, terpisah dari *microservices* Golang.

#### [NEW] `brain-orchestrator/requirements.txt`
Berisi dependensi utama:
- `pandas` dan `numpy` (Untuk pengolahan data deret waktu ClarkNet)
- `tensorflow` atau `torch` (Untuk model LSTM)
- `requests` (Untuk mengambil metrik HTTP dari HAProxy & cAdvisor)
- `docker` (Library resmi Python Docker untuk menjalankan komando _scale_ API secara native tanpa `os.system`)

#### [NEW] `brain-orchestrator/lstm_model.py`
Modul AI murni yang bertanggung jawab untuk:
- Mendefinisikan arsitektur jaringan saraf (Neural Network) dengan layer `LSTM` dan `Dense`.
- Menyediakan fungsi `train_model(dataset)` untuk proses *pre-training* menggunakan dataset ClarkNet HTTP.
- Menyediakan fungsi `predict(time_series_window)` untuk memprediksi trafik 10-30 detik ke depan.

#### [NEW] `brain-orchestrator/metrics_collector.py`
Modul monitoring yang:
- Mengambil *Request Per Second (RPS)* secara real-time dari endpoint HAProxy Stats (`http://localhost:8404/stats;csv`).
- Mengambil penggunaan CPU kontainer Docker saat ini (bisa via Docker SDK atau HTTP API cAdvisor lokal).

#### [NEW] `brain-orchestrator/main.py`
Titik eksekusi (Main Loop) dari *Brain Orchestrator*:
- Berjalan tanpa henti (*infinite loop*) setiap misal 5 detik.
- Mengumpulkan data dari `metrics_collector.py`.
- Memasukkan rekaman trafik ke `lstm_model.py`.
- Menerima hasil prediksi (misal: "30 detik lagi trafik akan mencapai 28 RPS!").
- Menghitung kebutuhan Pod (misal: Kapasitas aman = 10 RPS/Pod. Prediksi = 28 RPS. Maka butuh = ceil(28/10) = 3 Pod).
- Memanggil perintah auto-scaling Docker: `docker-compose up -d --scale media-service=3 --scale content-service=3`.

## Verification Plan

### Automated Tests
1. Menjalankan *test script* `calibrate.js` namun dengan mode "Ramp-Up" (trafik bertambah seiring waktu dari 5 RPS ke 25 RPS perlahan).
2. Memastikan log *Brain Orchestrator* berhasil memprediksi lonjakan tersebut di menit-menit awal.
3. Memastikan SLA (Latensi) k6 tetap di bawah 500ms saat di titik 25 RPS karena kontainer sudah bertambah sebelum beban 25 RPS tersebut benar-benar tiba.

### Manual Verification
1. Menjalankan perintah `docker ps` sambil melihat secara *live* apakah jumlah kontainer bertambah dengan sendirinya tanpa intervensi manual.
2. Mengecek log dari HAProxy untuk memastikan _traffic_ dibagi secara merata (Round-Robin) ke kontainer-kontainer baru tersebut.
