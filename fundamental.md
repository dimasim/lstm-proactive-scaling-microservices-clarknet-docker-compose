# Proyek Antigravity - Spesifikasi Acuan Fase 1: Data Collection Engine

Dokumen ini berisi poin-poin acuan arsitektur dan logika pengumpulan data telemetri untuk proyek Antigravity dalam Mode Pengumpulan Data (Data Collection Mode).

---

## 1. Poin Utama Infrastruktur & Lingkungan Testbed
* **Platform Utama:** Menggunakan Docker Compose secara eksklusif sebagai basis Infrastructure as Code (IaC).
* **Prinsip Isolasi Database:** Menggunakan satu kontainer PostgreSQL terpusat, namun secara logis dibagi menjadi dua basis data terpisah (auth_db dan quiz_db) untuk memenuhi prinsip Database-per-Service.
* **Tumpukan Pemantauan:** Mengintegrasikan Prometheus versi slim dengan retensi data jangka pendek (3 hari) untuk efisiensi penyimpanan, serta Grafana sebagai pusat visualisasi utama.

---

## 2. Definisi Strik 8 Fitur Data Telemetri (Multivariate Input)
Pengumpulan data tidak digabung, melainkan dipisahkan per kontainer menggunakan label PromQL untuk membentuk vektor input bertipe $(4 \times 2)$ fitur:

* **Metrik Layanan Go (Quiz Service):**
    1. `go_cpu_usage`: Persentase beban kerja CPU pada kontainer Go (diambil dari Docker API).
    2. `go_ram_usage`: Konsumsi memori RAM (Working Set) pada kontainer Go (diambil dari Docker API).
    3. `go_rps`: Jumlah total request per detik yang masuk ke rute kuis (diambil dari load balancer HAProxy).
    4. `go_current_container`: Jumlah kontainer Go yang aktif saat ini (diambil dari Docker API).
* **Metrik Layanan NestJS (Auth Service):**
    5. `nestjs_cpu_usage`: Persentase beban kerja CPU pada kontainer NestJS (diambil dari Docker API).
    6. `nestjs_ram_usage`: Konsumsi memori RAM pada kontainer NestJS (diambil dari Docker API).
    7. `nestjs_rps`: Jumlah total request per detik yang masuk ke rute login (diambil dari load balancer HAProxy).
    8. `nestjs_current_container`: Jumlah kontainer NestJS yang aktif saat ini (diambil dari Docker API).

---

## 3. Logika Penyuntikan Beban & Manajemen Token di Locust
Locust dikonfigurasi untuk membaca profil dataset industri dari file CSV secara sekuensial dan menjalankan manajemen status user secara stateful:

* **Skenario Kasus 1 (Proses Login / Token Expired):**
    * Terjadi ketika virtual user baru aktif atau saat token dinyatakan kedaluwarsa oleh sistem.
    * Locust akan menembak endpoint login NestJS. Proses ini memicu komputasi berat di sisi NestJS (Query DB, hashing password, dan signing JWT).
    * Token JWT yang diterima disimpan di dalam memori internal masing-masing virtual user.
* **Skenario Kasus 2 (Token Valid / Operasional Kuis):**
    * Terjadi ketika user melakukan interaksi reguler membaca atau mengisi kuis.
    * Locust langsung mengirim request ke layanan Go dengan menyertakan Bearer Token di HTTP Header.
    * Proses verifikasi signature JWT dilakukan di memori internal layanan Go secara instan (komputasi sangat ringan).
* **Mekanisme Reset Token Otomatis:**
    * Locust memanfaatkan kolom flag khusus pada file CSV untuk mensimulasikan kondisi token habis massal (Force Expire) guna memicu badai login ulang secara serentak.

---

## 4. Standar Visualisasi Grafana (Dashboard Requirements)
Dashboard Grafana dikonfigurasi secara otomatis (Provisioning) dan wajib menyediakan visualisasi korelasi berikut:

* **Panel Perbandingan Kriptografi (Case 1):** Grafik dual-axis yang memetakan hubungan langsung antara lonjakan RPS login NestJS dengan kenaikan drastis CPU usage NestJS.
* **Panel Efisiensi Verifikasi (Case 2):** Grafik yang membuktikan bahwa tingginya RPS pada layanan Go tidak menyebabkan kenaikan beban CPU yang signifikan pada NestJS karena sifat verifikasi JWT yang stateless.
* **Panel Profil Sumber Data:** Menampilkan nama profil beban kerja aktif dari dataset yang sedang disimulasikan oleh Locust beserta progres baris datanya.

---

## 5. Protokol Validasi Keberhasilan Koleksi Data
Sistem dinyatakan berhasil mengumpulkan data jika memenuhi tiga kriteria pengecekan:
1. Docker API (atau cAdvisor) dan HAProxy exporter berhasil mengekspos data metrik pada Prometheus.
2. Status target pada dashboard manajemen Prometheus menunjukkan status **UP** (hijau) untuk semua pengekspor metrik (Docker API/cAdvisor dan HAProxy).
3. Grafik di Grafana menampilkan tren naik-turun metrik yang sinkron secara real-time dengan fluktuasi RPS yang disuntikkan oleh Locust.