# Laporan Verifikasi & Validasi Data Telemetri Testbed ClarkNet (Triple Load - 3x RPS)

Dokumen ini memuat ringkasan performa sistem dan hasil verifikasi data telemetri yang dikumpulkan dari testbed microservices ClarkNet dengan beban kerja puncak yang **dikalikan tiga (3x RPS)**. Data ini dikumpulkan selama pengujian beban puncak (peak load) 5 menit (300 detik) menggunakan subset data dari ClarkNet Dataset asli (dimulai dari indeks baris `401022`).

---

## 1. Statistik Kinerja Beban Puncak Tiga Kali Lipat (Triple Peak Load Performance)

Selama pengujian beban puncak dengan skala 3x lipat (Target RPS: maks 57 Media RPS & 18 Content RPS pada subset 5 menit), berikut adalah profil penggunaan sumber daya (*resource usage*) dan latency respon dari masing-masing layanan:

### A. Media Service
* **Workload (Request Per Second)**:
  * Minimum (Min): **0.00 RPS**
  * Maksimum (Peak): **38.00 RPS** (Tercatat di Prometheus per detik)
  * Rata-rata (Avg): **13.79 RPS**
* **Penggunaan CPU**:
  * Minimum (Min): **0.00%**
  * Maksimum (Peak): **97.87%**
  * Rata-rata (Avg): **21.95%**
* **Penggunaan RAM**:
  * Minimum (Min): **206.63 MB**
  * Maksimum (Peak): **214.22 MB**
  * Rata-rata (Avg): **210.71 MB**
* **Latency Respon (RTT)**:
  * Minimum (Min): **20.00 ms**
  * Maksimum (Peak): **91.00 ms**
  * Rata-rata (Avg): **43.90 ms**

### B. Content Service
* **Workload (Request Per Second)**:
  * Minimum (Min): **0.00 RPS**
  * Maksimum (Peak): **17.00 RPS**
  * Rata-rata (Avg): **3.23 RPS**
* **Penggunaan CPU**:
  * Minimum (Min): **0.00%**
  * Maksimum (Peak): **43.66%**
  * Rata-rata (Avg): **3.73%**
* **Penggunaan RAM**:
  * Minimum (Min): **34.86 MB**
  * Maksimum (Peak): **35.95 MB**
  * Rata-rata (Avg): **35.48 MB**
* **Latency Respon (RTT)**:
  * Minimum (Min): **130.00 ms**
  * Maksimum (Peak): **206.00 ms**
  * Rata-rata (Avg): **158.99 ms**

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

Untuk membuktikan keabsahan data telemetri sebelum digunakan sebagai dataset pelatihan LSTM/GRU, dilakukan pencocokan data RPS yang terekam di Prometheus dengan data RPS dari dataset asli (dikalikan pengali 3x).

### Akurasi Pencocokan Volume (3x Target)
Setelah disesuaikan dengan faktor pengali 3x dari dataset asli:

* **Media Service Accuracy**: **99.01%** Rata-rata Akurasi Total Volume (4.923 request tercatat vs 4.875 target request).
* **Content Service Accuracy**: **98.77%** Rata-rata Akurasi Total Volume (1.154 request tercatat vs 1.140 target request).

### Validasi Total Volume Data
* **Media Service**: Total target (3x) **4,875** request | Tercatat di Prometheus **4,923** request.
* **Content Service**: Total target (3x) **1,140** request | Tercatat di Prometheus **1,154** request.

---

## 4. Kesimpulan untuk Pengajuan Pengumpulan Data
1. **Keandalan Tinggi**: Load generator mampu mempertahankan stabilitas pengiriman beban kerja sangat tinggi (3x RPS) dengan Success Rate mencapai **99.98%** (hanya 1 connection error dari total 6.084 request terkirim).
2. **Karakteristik Resource yang Lebih Kontras**: Penggunaan CPU di Media Service didorong hingga **97.87%** dan Content Service hingga **43.66%**. Pola ini memberikan data telemetri yang sangat dinamis untuk melatih model LSTM/GRU memprediksi auto-scaling secara proaktif.
