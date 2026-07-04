# Rancangan Layanan & Fitur Microservices (ClarkNet-HTTP Dataset)

Dokumen ini berisi spesifikasi perancangan rute akses dari dataset log akses **ClarkNet-HTTP (1 Minggu Penuh)** menjadi 3 layanan microservices virtual untuk kebutuhan pengujian proactive auto-scaling Anda.

---

## 1. Pemetaan Rute ke Virtual Microservices

Berdasarkan ekstensi file (`extension`) dan HTTP method (`method`) dari log asli ClarkNet-HTTP, trafik didekomposisi menjadi 3 jenis layanan dengan karakteristik beban kerja (*workload profile*) yang berbeda:

| Nama Layanan (Microservice) | Ekstensi / Rute Log ClarkNet | Karakteristik Beban Kerja | Perilaku Auto-Scaling |
| :--- | :--- | :--- | :--- |
| **1. DynamicAPI_Service** | Ekstensi `.cgi`, `.pl`, `.php` ATAU HTTP `POST` | **CPU-Heavy & Computational Bound** | Memproses logika backend dinamis (skrip CGI/Perl). Sangat sensitif terhadap load CPU karena setiap request menjalankan proses CGI baru. |
| **2. Content_Service** | Ekstensi `.html`, `.htm`, `.txt`, `.shtml`, atau `/` (direktori) | **I/O-Heavy & Database-Bound** | Menyajikan artikel berita, petunjuk web, dokumen FAQ. Membaca data teks dari disk/database (Read-Heavy). |
| **3. Media_Service** | Ekstensi `.gif`, `.jpg`, `.jpeg`, `.xbm`, `.png` | **Network-Heavy & Memory Bound** | Menyajikan file gambar/grafik pendukung halaman web. Merupakan request paling dominan (~75% trafik). |
| **Others** | Ekstensi `.wav`, `.au` (Audio), `.zip`, dll. | **General / Diabaikan** | Trafik umum yang tidak dipetakan ke layanan utama. |

---

## 2. Catatan Historis & Konseptual (Untuk Argumen Skripsi)

### A. Karakteristik Trafik ISP Era 1995
* **Koneksi Pengguna**: Pada tahun 1995, ClarkNet merupakan ISP regional komersial. Trafik log ini mencakup aktivitas pengguna nyata yang menjelajah web menggunakan modem Dial-up (33.6 - 56 Kbps).
* **Weekly Seasonality (Pola Mingguan)**: Karena merupakan ISP, log ini merepresentasikan siklus kehidupan pengguna mingguan secara akurat. Trafik cenderung tinggi di hari kerja (weekdays) saat jam kerja, dan mengalami penurunan yang signifikan pada akhir pekan (weekend). Pola ini sangat penting untuk melatih model prediksi LSTM/GRU Anda dalam mengenali tren musiman mingguan.

### B. Transparansi URL Akses (Human-Readable Paths)
* Berbeda dengan WorldCup98 yang menyembunyikan identitas file ke bentuk ID biner, ClarkNet-HTTP menyajikan URL asli (contoh: `/pub/atomicbk/catalog/sleazbk.html`). Hal ini memudahkan pengujian Locust Anda karena profil request dapat menirukan path URL yang nyata.

---

## 3. Hasil Analisis Statistik RPS per-Layanan (1 Minggu Penuh)

Berdasarkan pemrosesan log 7 hari penuh, berikut adalah metrik beban kerja per detik untuk masing-masing microservice virtual:

* **Trafik Akumulasi (`total_rps`)**:
  * Rata-rata: **2.73 RPS**
  * Puncak (Peak): **45.00 RPS**
* **`Media_Service`** (Aset Gambar):
  * Puncak (Peak): **37.00 RPS**
* **`Content_Service`** (Halaman HTML):
  * Puncak (Peak): **12.00 RPS**
* **`DynamicAPI_Service`** (API Dinamis / CGI):
  * Puncak (Peak): **3.00 RPS**
* **`Others`** (Layanan Lainnya):
  * Puncak (Peak): **4.00 RPS**
