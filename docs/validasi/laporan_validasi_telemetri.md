# Laporan Verifikasi & Validasi Data Telemetri Testbed ClarkNet

Dokumen ini memuat ringkasan performa sistem dan hasil verifikasi data telemetri yang dikumpulkan dari testbed microservices ClarkNet. Data ini dikumpulkan selama pengujian beban puncak (peak load) 5 menit (300 detik) menggunakan subset data dari ClarkNet Dataset asli (dimulai dari indeks baris `401022`).

---

## 1. Statistik Kinerja Beban Puncak (Peak Load Performance)

Selama pengujian beban puncak (Target RPS: 37 Media RPS & 12 Content RPS), berikut adalah profil penggunaan sumber daya (*resource usage*) dan latency respon dari masing-masing layanan:

### A. Media Service
* **Workload (Request Per Second)**:
  * Minimum (Min): **0.00 RPS**
  * Maksimum (Peak): **19.00 RPS**
  * Rata-rata (Avg): **5.40 RPS**
* **Penggunaan CPU**:
  * Minimum (Min): **0.00%**
  * Maksimum (Peak): **66.35%**
  * Rata-rata (Avg): **7.16%**
* **Penggunaan RAM**:
  * Minimum (Min): **198.58 MB**
  * Maksimum (Peak): **207.99 MB**
  * Rata-rata (Avg): **206.39 MB**
* **Latency Respon (RTT)**:
  * Minimum (Min): **26.00 ms**
  * Maksimum (Peak): **40.00 ms**
  * Rata-rata (Avg): **30.22 ms**

### B. Content Service
* **Workload (Request Per Second)**:
  * Minimum (Min): **0.00 RPS**
  * Maksimum (Peak): **6.00 RPS**
  * Rata-rata (Avg): **1.26 RPS**
* **Penggunaan CPU**:
  * Minimum (Min): **0.00%**
  * Maksimum (Peak): **15.39%**
  * Rata-rata (Avg): **1.52%**
* **Penggunaan RAM**:
  * Minimum (Min): **34.84 MB**
  * Maksimum (Peak): **35.12 MB**
  * Rata-rata (Avg): **34.89 MB**
* **Latency Respon (RTT)**:
  * Minimum (Min): **130.00 ms**
  * Maksimum (Peak): **176.00 ms**
  * Rata-rata (Avg): **148.69 ms**

---

## 2. Deskripsi dan Karakteristik Layanan (Service Specifications)

Berikut adalah detail teknis dan mekanisme internal dari masing-masing microservice yang digunakan dalam testbed ClarkNet:

### A. Media Service
* **Endpoint**: `/media` (HTTP GET)
* **Karakteristik Beban**: *CPU-bound* dan *RAM-heavy*
* **Mekanisme Kerja**:
  1. **Pemilihan Gambar Acak**: Layanan memilih salah satu file gambar secara acak dari repositori (`IMAGES` yang berisi file jpeg berukuran 2MB hingga 4.5MB).
  2. **Konsumsi Memori (RAM)**: Seluruh byte gambar dibaca langsung ke dalam memori server untuk mensimulasikan penggunaan RAM yang tinggi pada proses pemrosesan/dekoding citra.
  3. **Pemrosesan CPU**: Melakukan komputasi *hashing* kriptografi SHA-256 sebanyak 1 kali pada data gambar tersebut untuk mensimulasikan overhead komputasi CPU.
  4. **Pemberian Respon**: Mengembalikan file gambar menggunakan `FileResponse` dengan menambahkan custom HTTP Header `X-Image-Hash` berisi nilai hash yang dihitung.

### B. Content Service
* **Endpoint**: `/content` (HTTP GET)
* **Karakteristik Beban**: *CPU-bound* dan *Server-Side Rendering (SSR)*
* **Mekanisme Kerja**:
  1. **Generasi Data Dinamis**: Menghasilkan 150 sesi pengguna dial-up secara dinamis (berdasarkan data username, IP, node, baud rate, dan connection duration).
  2. **Pemrosesan CPU Keras**: Melakukan komputasi enkripsi/billing check simulatif dengan menghitung *hash* MD5 secara berulang sebanyak 120 kali untuk setiap sesi pengguna (total 18.000 iterasi MD5 per request) untuk memberikan beban kerja CPU yang signifikan.
  3. **Sorting**: Mengurutkan seluruh sesi pengguna berdasarkan connection duration secara descending.
  4. **Render Template**: Melakukan rendering dokumen HTML (`clarknet.html`) secara server-side menggunakan framework template Jinja2 sebelum dikirimkan kembali ke klien.

---

## 3. Hasil Akurasi Pengiriman Beban (Detik-demi-Detik)

Untuk membuktikan keabsahan data telemetri sebelum digunakan sebagai dataset pelatihan LSTM/GRU, dilakukan pencocokan data RPS yang terekam di Prometheus dengan data RPS dari dataset asli.

### Koreksi Penyelarasan Waktu (*Time-Shift Alignment*)
Karena adanya lag alami pada arsitektur monitoring pull-based Prometheus (frekuensi scrape `500ms` & query window `[2s]`), terdapat delay pencatatan sebesar **2 detik** antara pengiriman request oleh load generator dan visualisasi di database. Setelah dilakukan pergeseran indeks sebesar 2 detik (`lag_shift = 2`), tingkat akurasi pencocokan detik-ke-detik adalah sebagai berikut:

* **Media Service Accuracy**: **99.62%** Rata-rata Akurasi Detik-ke-Detik
* **Content Service Accuracy**: **97.04%** Rata-rata Akurasi Detik-ke-Detik

### Validasi Total Volume Data
* **Media Service**: Total terkirim **1,625** request | Tercatat di Prometheus **1,625** request.
* **Content Service**: Total terkirim **380** request | Tercatat di Prometheus **381** request.

---

## 4. Kesimpulan untuk Pengajuan Pengumpulan Data
1. **Akurasi Sangat Tinggi (>97%)**: Membuktikan bahwa generator beban mensimulasikan dataset ClarkNet asli dengan sangat presisi.
2. **Korelasi Positif**: Terlihat korelasi yang jelas antara peningkatan RPS dengan naiknya CPU usage dan Latency, yang membuktikan data telemetri ini valid secara operasional untuk digunakan melatih model prediksi skalabilitas (*proactive auto-scaling*).
