# Laporan Verifikasi & Validasi Data Telemetri Testbed ClarkNet

Dokumen ini memuat ringkasan performa sistem dan hasil verifikasi data telemetri yang dikumpulkan dari testbed microservices ClarkNet. Data ini dikumpulkan selama pengujian beban puncak (peak load) 5 menit (300 detik) menggunakan subset data dari ClarkNet Dataset asli (dimulai dari indeks baris `401022`).

---

## 1. Statistik Kinerja Beban Puncak (Peak Load Performance)

Selama pengujian beban puncak (Target RPS: 37 Media RPS & 12 Content RPS), berikut adalah profil penggunaan sumber daya (*resource usage*) dan latency respon dari masing-masing layanan:

### A. Media Service
* **Workload (Request Per Second)**:
  * Maksimum (Peak): **36.00 RPS**
  * Rata-rata (Avg): **15.42 RPS**
* **Penggunaan CPU**:
  * Maksimum (Peak): **96.73%**
  * Rata-rata (Avg): **25.79%**
* **Penggunaan RAM**:
  * Maksimum (Peak): **551.23 MB**
  * Rata-rata (Avg): **536.16 MB**
* **Latency Respon (RTT)**:
  * Maksimum (Peak): **78.00 ms**
  * Rata-rata (Avg): **52.49 ms**

### B. Content Service
* **Workload (Request Per Second)**:
  * Maksimum (Peak): **12.00 RPS**
  * Rata-rata (Avg): **5.00 RPS**
* **Penggunaan CPU**:
  * Maksimum (Peak): **39.58%**
  * Rata-rata (Avg): **5.92%**
* **Penggunaan RAM**:
  * Maksimum (Peak): **103.27 MB**
  * Rata-rata (Avg): **103.00 MB**
* **Latency Respon (RTT)**:
  * Maksimum (Peak): **118.00 ms**
  * Rata-rata (Avg): **62.25 ms**

---

## 2. Hasil Akurasi Pengiriman Beban (Detik-demi-Detik)

Untuk membuktikan keabsahan data telemetri sebelum digunakan sebagai dataset pelatihan LSTM/GRU, dilakukan pencocokan data RPS yang terekam di Prometheus dengan data RPS dari dataset asli.

### Koreksi Penyelarasan Waktu (*Time-Shift Alignment*)
Karena adanya lag alami pada arsitektur monitoring pull-based Prometheus (frekuensi scrape `500ms` & query window `[2s]`), terdapat delay pencatatan sebesar **2 detik** antara pengiriman request oleh load generator dan visualisasi di database. Setelah dilakukan pergeseran indeks sebesar 2 detik (`lag_shift = 2`), tingkat akurasi pencocokan detik-ke-detik adalah sebagai berikut:

* **Media Service Accuracy**: **99.62%** Rata-rata Akurasi Detik-ke-Detik
* **Content Service Accuracy**: **97.04%** Rata-rata Akurasi Detik-ke-Detik

### Validasi Total Volume Data
* **Media Service**: Total terkirim **1,625** request | Tercatat di Prometheus **1,625** request.
* **Content Service**: Total terkirim **380** request | Tercatat di Prometheus **381** request.

---

## 3. Kesimpulan untuk Pengajuan Pengumpulan Data
1. **Akurasi Sangat Tinggi (>97%)**: Membuktikan bahwa generator beban mensimulasikan dataset ClarkNet asli dengan sangat presisi.
2. **Korelasi Positif**: Terlihat korelasi yang jelas antara peningkatan RPS dengan naiknya CPU usage dan Latency, yang membuktikan data telemetri ini valid secara operasional untuk digunakan melatih model prediksi skalabilitas (*proactive auto-scaling*).
