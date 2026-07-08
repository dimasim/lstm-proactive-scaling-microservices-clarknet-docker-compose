# Proyek Antigravity - Spesifikasi Acuan Fase 1: Data Collection Engine

Dokumen ini berisi poin-poin acuan arsitektur dan logika pengumpulan data telemetri untuk proyek Antigravity dalam Mode Pengumpulan Data (Data Collection Mode).

---

## 1. Poin Utama Infrastruktur & Lingkungan Testbed
* **Platform Utama:** Menggunakan Docker Compose secara eksklusif sebagai basis Infrastructure as Code (IaC).
* **Arsitektur Layanan:** Menggunakan arsitektur microservices stateless dengan dua layanan mandiri, yaitu `media-service` dan `content-service` (FastAPI - Python).
* **Tumpukan Pemantauan:** Mengintegrasikan Prometheus versi slim dengan retensi data jangka pendek (3 hari) untuk efisiensi penyimpanan, cAdvisor untuk data performa kontainer, serta dashboard visualisasi utama.

---

## 2. Definisi Strik 8 Fitur Data Telemetri (Multivariate Input)
Pengumpulan data tidak digabung, melainkan dipisahkan per kontainer menggunakan label PromQL untuk membentuk vektor input bertipe $(4 \times 2)$ fitur:

* **Metrik Layanan Media (Media Service):**
    1. `media_cpu_usage`: Persentase beban kerja CPU pada kontainer Media Service (diambil dari cAdvisor).
    2. `media_ram_usage`: Konsumsi memori RAM (Working Set) pada kontainer Media Service (diambil dari cAdvisor).
    3. `media_rps`: Jumlah total request per detik yang masuk ke rute `/media` (diambil dari load balancer HAProxy).
    4. `media_current_container`: Jumlah kontainer Media Service yang aktif saat ini (diambil dari cAdvisor/Prometheus).
* **Metrik Layanan Konten (Content Service):**
    5. `content_cpu_usage`: Persentase beban kerja CPU pada kontainer Content Service (diambil dari cAdvisor).
    6. `content_ram_usage`: Konsumsi memori RAM pada kontainer Content Service (diambil dari cAdvisor).
    7. `content_rps`: Jumlah total request per detik yang masuk ke rute `/content` (diambil dari load balancer HAProxy).
    8. `content_current_container`: Jumlah kontainer Content Service yang aktif saat ini (diambil dari cAdvisor/Prometheus).

---

## 3. Logika Penyuntikan Beban di Locust
Locust dikonfigurasi untuk membaca profil dataset ClarkNet dari file CSV (`aggregated_clarknet_rps.csv`) dan mengirimkan beban kerja secara proporsional sesuai pola fluktuasi RPS:

* **Skenario Kasus 1 (Media Service - File/Aset Media):**
    * Menyerang endpoint `/media`. Proses ini memicu simulasi kalkulasi hash SHA-256 secara asinkron untuk menyimulasikan beban I/O dan CPU pemrosesan media berukuran besar.
* **Skenario Kasus 2 (Content Service - Halaman HTML):**
    * Menyerang endpoint `/content`. Proses ini memicu render template Jinja2 dan kalkulasi MD5 ringan untuk mensimulasikan proses otentikasi billing pelanggan atau request dinamis.

---

## 4. Standar Visualisasi Dashboard (Dashboard Requirements)
Dashboard monitoring terintegrasi dikonfigurasi secara otomatis dan wajib menyediakan visualisasi korelasi berikut:

* **Panel Metrik Media Service:** Grafik dual-axis yang memetakan hubungan langsung antara lonjakan RPS pada rute `/media` dengan kenaikan CPU usage dan RAM usage pada Media Service.
* **Panel Metrik Content Service:** Grafik yang memetakan relasi antara RPS rute `/content` dengan pemakaian resource CPU/RAM pada Content Service.
* **Panel Profil Sumber Data:** Menampilkan nama profil beban kerja aktif dari dataset ClarkNet yang sedang disimulasikan oleh Locust beserta progres baris datanya.

---

## 5. Protokol Validasi Keberhasilan Koleksi Data
Sistem dinyatakan berhasil mengumpulkan data jika memenuhi tiga kriteria pengecekan:
1. Docker API (melalui cAdvisor) dan HAProxy exporter berhasil mengekspos data metrik pada Prometheus.
2. Status target pada dashboard manajemen Prometheus menunjukkan status **UP** (hijau) untuk semua pengekspor metrik (cAdvisor dan HAProxy).
3. Grafik di dashboard menampilkan tren naik-turun metrik yang sinkron secara real-time dengan fluktuasi RPS yang disuntikkan oleh Locust.