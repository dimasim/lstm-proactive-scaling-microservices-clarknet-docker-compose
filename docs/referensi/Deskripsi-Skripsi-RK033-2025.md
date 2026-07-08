# Deskripsi Skripsi

## Identitas Umum

| Item | Keterangan |
|---|---|
| **Judul** | Analisis Performa Dan Skalabilitas Horizontal Aplikasi Web Dengan Orkestrasi Kubernetes Pada Infrastruktur Cloud |
| **Judul (Inggris)** | Performance And Horizontal Scalability Analysis Of A Kubernetes-Orchestrated Web Application On Cloud Infrastructure |
| **Penulis** | Fajar Fatoni Pratama (NIM 4.33.21.0.09, Kelas TI-4A) |
| **Program Studi** | S.Tr Teknologi Rekayasa Komputer |
| **Jurusan** | Teknik Elektro |
| **Institusi** | Politeknik Negeri Semarang |
| **Dosen Pembimbing I** | Kuwat Santoso, S.Kom., M.Kom. |
| **Dosen Pembimbing II** | Suko Tyas Pernanda, M.Cs. |
| **Tahun** | 2025 (disahkan 11 Agustus 2025) |
| **Jumlah Halaman** | 111 halaman (termasuk lampiran) |

---

## 1. Ringkasan / Abstrak

Skripsi ini menganalisis secara kuantitatif performa dan efektivitas skalabilitas horizontal pada infrastruktur **cloud-native** modern. Objek yang diuji adalah aplikasi **Ujian Daring (Computer Based Test/CBT) berbasis Laravel** yang di-deploy pada VPS menggunakan orkestrasi **Kubernetes ringan (K3s)** dengan **Horizontal Pod Autoscaler (HPA)** dan kontainerisasi **Podman**.

Aplikasi diuji dalam **9 skenario eksperimental** dengan variabel yang dimanipulasi berupa:
- 3 runtime PHP (Nginx+PHP-FPM, FrankenPHP, Swoole)
- 2 profil tuning kernel (default/virtual-host vs custom)
- Ada/tidaknya HPA (1 pod tetap vs skalabilitas hingga 6 pod)

Pengujian beban dilakukan dengan **Grafana k6**, mengukur *Requests Per Second* (RPS), *Response Time* (p95 latency), dan *Error Rate*.

**Temuan utama:**
- Implementasi HPA meningkatkan throughput hingga **180%** pada beban puncak dibanding konfigurasi single-pod.
- Runtime PHP modern (**Swoole** dan **FrankenPHP**) secara konsisten mengungguli **PHP-FPM** tradisional, dengan latensi lebih rendah dan throughput lebih tinggi.
- Optimasi kernel memberi peningkatan performa tambahan yang terukur, terutama dalam menangani koneksi konkuren dalam jumlah besar.
- Kombinasi *runtime* modern + HPA + kernel tuning terbukti paling performan dan resilien.

**Kata kunci:** Performa Aplikasi Web, Skalabilitas Horizontal, Kubernetes, K3s, Horizontal Pod Autoscaler (HPA), Podman, Load Testing, Infrastruktur Cloud, Runtime PHP.

---

## 2. BAB I — Pendahuluan

### 2.1 Latar Belakang
Penelitian dilatarbelakangi oleh paradoks transformasi digital Indonesia: penetrasi internet tinggi (79,5% menurut APJII 2024) namun infrastruktur layanan digital publik masih rapuh. Penulis mengangkat contoh nyata kegagalan sistem seperti insiden **serangan ransomware "Brain Cipher" pada Pusat Data Nasional Sementara (PDNS) Juni 2024** dan kegagalan berulang sistem **PPDB online** akibat lonjakan trafik (*bursty traffic*) yang tidak tertangani infrastruktur tradisional berbasis Virtual Machine (VM).

Solusi yang diajukan adalah paradigma **cloud-native**: kontainerisasi + orkestrasi Kubernetes dengan kemampuan **penskalaan otomatis horizontal (HPA)**. Penulis mengidentifikasi *research gap*: penelitian terdahulu banyak membahas kontainerisasi/orkestrasi secara konseptual atau komparatif tingkat tinggi, namun belum ada yang menganalisis secara **kuantitatif dan holistik** dampak gabungan dari kombinasi orkestrator ringan (K3s) + *runtime* PHP modern + optimasi kernel OS dalam satu rangkaian eksperimen terkontrol.

### 2.2 Rumusan Masalah
1. Bagaimana implementasi arsitektur sistem aplikasi web *highly-available* dengan penskalaan horizontal otomatis (K3s + HPA) pada VPS Alma Linux?
2. Bagaimana perbedaan performa & skalabilitas kuantitatif antara konfigurasi default vs teroptimasi (variasi *runtime* PHP dan tuning kernel)?
3. Rekomendasi praktis apa yang dapat dihasilkan untuk optimasi konfigurasi *scaling* aplikasi web di lingkungan K3s?

### 2.3 Tujuan
1. Mengimplementasikan sistem web dengan *scaling* otomatis K3s + HPA di VPS Alma Linux.
2. Membandingkan performa (response time, throughput, error rate) sebelum vs sesudah tuning.
3. Mengevaluasi dampak tuning secara kuantitatif.
4. Memvalidasi pemenuhan *Service Level Objective* (SLO).
5. Memberikan rekomendasi praktis berbasis data.

### 2.4 Manfaat
- Model arsitektur teruji & dapat direplikasi untuk sistem web *highly-available*.
- Bukti performa kuantitatif sebagai dasar keputusan teknis pemilihan *runtime*.
- Rekomendasi praktis untuk optimasi *scaling* di lingkungan K3s berbasis Alma Linux/RHEL.

### 2.5 Batasan Masalah
- Fokus pada satu aplikasi Ujian Online untuk lingkungan kampus.
- Orkestrasi: **K3s**; kontainerisasi: **Podman**; load testing: **k6**.
- Mekanisme scaling yang dianalisis: **HPA berbasis CPU utilization**.
- Tidak membandingkan K3s/Podman dengan platform lain (fokus optimasi mendalam pada satu *tech stack*).
- Host: VPS **Alma Linux**, konfigurasi standar.
- Kriteria kelulusan (SLO): **p95 latency < 3 detik** dan **error rate < 0,02%**.

---

## 3. BAB II — Tinjauan Pustaka

### 3.1 Penelitian Terkait
Tabel perbandingan (Tabel 2.1) memuat 8 penelitian terdahulu (Kandi dkk. 2023; Koneru & Murali 2025; Mantha 2024; Woo & Lee 2023; Marella 2024; Cherukuri 2024; Thallapally 2024; Singh & Agrawal), yang sebagian besar bersifat survei/konseptual/komparatif platform secara umum. Posisi orisinalitas penelitian ini: eksperimen praktis dan kuantitatif yang berfokus pada satu ekosistem (K3s) untuk menguji dampak tuning konfigurasi internal (HPA, runtime, kernel) secara mendalam.

### 3.2 Dasar Teori
Landasan teori yang dibahas meliputi:
- **Skalabilitas Aplikasi Web** — perbandingan penskalaan vertikal vs horizontal (Tabel 2.2), serta implikasi arsitektur *stateless* vs *stateful*.
- **Teknologi Kontainerisasi** — konsep & manfaat (portabilitas, efisiensi sumber daya, isolasi proses), perbandingan kontainer vs VM, serta studi komparatif **Docker vs Podman** (Podman: *daemonless* & *rootless*, lebih aman).
- **Orkestrasi Kontainer** — Kubernetes sebagai standar industri (berakar dari Borg/Omega Google), fitur kunci (self-healing, penskalaan horizontal, service discovery/load balancing, rolling update/rollback), mekanisme **HPA**, dan **K3s** sebagai distribusi ringan (biner <100MB, RAM minimal ~512MB, SQLite menggantikan etcd).
- **Runtime PHP Modern** — arsitektur tradisional Nginx+PHP-FPM vs *application server* modern **FrankenPHP** (worker mode, berbasis Caddy/Go) dan **Swoole** (async, event-driven, coroutine-based).
- **Metodologi Evaluasi Kinerja & Load Testing** — pendekatan *tiered load profile*: Baseline Load, Peak Load, dan Stress Testing.

### 3.3 Alat dan Teknologi
Mencakup landasan pemilihan: VPS (DigitalOcean), Alma Linux, Podman, Kubernetes/K3s, PHP + Laravel (MVC), Nginx/FrankenPHP/Swoole, MySQL, Redis, dan k6.

---

## 4. BAB III — Metodologi Penelitian

### 4.1 Metode Penelitian
Pendekatan **eksperimental kuantitatif**, dengan tiga variabel bebas yang dimanipulasi:
1. **Runtime PHP**: Nginx+PHP-FPM, FrankenPHP, Swoole
2. **Profil kernel**: default (*virtual-host*) vs custom
3. **Konfigurasi skalabilitas**: tanpa HPA (1 pod tetap) vs dengan HPA (min=1, max=6 pod)

Variabel kontrol: spesifikasi perangkat keras, versi perangkat lunak, aplikasi CBT yang sama, konfigurasi HPA (target CPU 60%), dan skrip k6 yang identik. Variabel terikat (metrik performa client-side): RPS, p95 Response Time, Error Rate.

### 4.2 Objek Penelitian — Aplikasi CBT
Aplikasi Ujian Daring melayani 3 peran: **Admin** (manajemen data & soal), **Pengajar** (koreksi esai & rekap nilai), **Siswa** (login → dashboard → mengerjakan soal satu per satu dengan auto-save → submit). Alur kunci yang diuji beban adalah siswa mengerjakan ujian (siklus GET soal + POST jawaban berulang), karena ini menghasilkan beban paling intensif.

**Arsitektur & teknologi aplikasi:**
- Backend: **Laravel 11**
- Frontend: Blade + Vite + Bootstrap 5
- Kontainerisasi: **Podman**, image di-push ke Docker Hub

### 4.3 Perangkat Keras & Lunak

| Komponen | Spesifikasi |
|---|---|
| VPS Server Aplikasi (DigitalOcean) | 4 vCPU, 8 GB RAM, 80 GB SSD — Alma Linux 9.6, K3s (go1.23.8) |
| VPS Load Test (DigitalOcean) | 1 vCPU, 1 GB RAM, 25 GB SSD — Ubuntu 22.04.5 LTS |
| Mesin Lokal | Alma Linux 9.5, Podman 5.4.0, kubectl |

Perangkat lunak lain: PHP 8.2.29, Laravel 11.45.1, Nginx release-1.29.0, FrankenPHP v1.8.0, Swoole v6.0.2, MySQL/MariaDB 10.6.22, Redis 7.4.4, k6 v1.1.0.

### 4.4 Arsitektur Sistem
- **Lapisan Infrastruktur**: 2 VPS terpisah (server aplikasi & load generator) agar pengujian tidak mengganggu resource server yang diukur.
- **Lapisan Orkestrasi**: klaster K3s single-node pada VPS aplikasi, mengelola siklus hidup & scaling.
- **Lapisan Aplikasi**: pod terpisah untuk Laravel, MySQL (StatefulSet + PVC 5GB), Redis.
- **Lapisan Jaringan**: **Traefik Ingress Controller** + **cert-manager** (SSL/TLS via Let's Encrypt) pada domain publik `ujian.bluehat.engineer`.
- **Lapisan Pengujian**: k6 dijalankan dari VPS terpisah untuk mensimulasikan trafik nyata dari internet.

Deployment diatur secara deklaratif via manifest YAML (db-deployment, db-pvc, db-configmap, redis-deployment, app-deployment, app-hpa, app-ingress, letsencrypt-issuer, dsb).

### 4.5 Profil Kernel Custom
Dibangun di atas profil `latency-performance` (tool **tuned**), dengan tuning agresif:
- **Antrian koneksi**: `net.core.somaxconn`, `net.core.netdev_max_backlog`, `net.ipv4.tcp_max_syn_backlog` dinaikkan hingga 65535.
- **Buffer TCP**: `net.core.rmem_max/wmem_max`, `tcp_rmem/tcp_wmem` diperbesar.
- **File descriptor**: `fs.file-max`, `fs.nr_open` dinaikkan hingga 1.000.000.
- **Manajemen memori**: `vm.swappiness` diturunkan ke 10, *transparent hugepages* dinonaktifkan.

### 4.6 Desain 9 Skenario Pengujian (Tabel 3.2)

| Skenario | Runtime | Kernel | Pod | Fokus |
|---|---|---|---|---|
| A | Nginx+PHP-FPM | Virtual Host | 1 | Baseline tradisional |
| B | FrankenPHP | Virtual Host | 1 | Baseline runtime modern |
| C | Swoole | Virtual Host | 1 | Baseline runtime modern |
| D | Nginx+PHP-FPM | Virtual Host | 6 (HPA) | Dampak HPA pada runtime tradisional |
| E | FrankenPHP | Virtual Host | 6 (HPA) | Dampak HPA pada runtime modern |
| F | Swoole | Virtual Host | 6 (HPA) | Dampak HPA pada runtime modern |
| G | Nginx+PHP-FPM | Custom | 6 (HPA) | HPA + kernel tuning (tradisional) |
| H | FrankenPHP | Custom | 6 (HPA) | HPA + kernel tuning (modern) — kandidat performa puncak |
| I | Swoole | Custom | 6 (HPA) | HPA + kernel tuning (modern) — kandidat performa puncak |

**Kriteria kelulusan (SLO) per skenario:** p95 latency < 3.000 ms dan error rate < 0,02%.

### 4.7 Pelaksanaan Pengujian Beban
- Level beban: **100 VU** (baseline, ±1–2 kelas ujian serentak), **300 VU** (peak), **500 VU** (stress test).
- Durasi per iterasi: **5 menit** (ramp-up 1 menit, steady-state 3 menit, ramp-down 1 menit).
- **10 kali repetisi** per skenario per level beban; hasil akhir = rata-rata.

### 4.8 Teknik Pengumpulan & Analisis Data
Data dikumpulkan dari sisi klien (client-side) melalui ringkasan akhir k6 (RPS, p95 response time, error rate). Analisis dilakukan bertahap: agregasi data → analisis komparatif (performa mentah → efektivitas HPA → dampak kernel) → evaluasi & verifikasi SLO.

---

## 5. BAB IV — Hasil dan Pembahasan

### 5.1 Implementasi Antarmuka
Ditampilkan 4 antarmuka aplikasi yang telah diimplementasikan: Halaman Login, Dashboard Siswa (daftar ujian format kartu), Halaman Pengerjaan Soal (area soal + panel navigasi), dan Halaman Konfirmasi Ujian (ringkasan status jawaban), semuanya konsisten dengan rancangan *wireframe* pada Bab III.

### 5.2 Data Agregasi Hasil Pengujian (Tabel 4.1, ringkas)

| Skenario | Runtime | Kernel | Pod | RPS @500VU | p95 @500VU (detik) |
|---|---|---|---|---|---|
| A | Nginx+PHP-FPM | Virtual Host | 1 | 28,58 | 20,55 |
| B | FrankenPHP | Virtual Host | 1 | 41,23 | 14,00 |
| C | Swoole | Virtual Host | 1 | 48,97 | 12,07 |
| D | Nginx+PHP-FPM | Virtual Host | 6 | 80,14 | 9,49 |
| E | FrankenPHP | Virtual Host | 6 | 102,27 | 6,16 |
| F | Swoole | Virtual Host | 6 | 108,87 | 6,60 |
| G | Nginx+PHP-FPM | Custom | 6 | 84,31 | 8,89 |
| H | FrankenPHP | Custom | 6 | 110,65 | 6,14 |
| I | Swoole | Custom | 6 | 109,49 | 6,56 |

### 5.3 Analisis Komparatif
1. **Performa mentah (single-pod, A/B/C):** Swoole > FrankenPHP > Nginx+PHP-FPM secara konsisten pada semua level beban. Semua *error rate* = 0,00%, namun latensi memburuk drastis seiring naiknya beban (tanpa scaling, sistem tidak sanggup menangani beban menengah–tinggi).
2. **Efektivitas HPA (single-pod vs HPA-aktif kernel default):** Peningkatan throughput dramatis pada 500 VU — Nginx+PHP-FPM naik **180%** (28,58 → 80,14 RPS), FrankenPHP **148%**, Swoole **122%**. Latensi Nginx+PHP-FPM turun dari 20,55 detik menjadi 9,49 detik.
3. **Dampak optimasi kernel (HPA kernel default vs custom):** Peningkatan lebih moderat; paling signifikan pada FrankenPHP (Skenario H, +8,2% RPS @500VU). Latensi turun tipis — mengindikasikan setelah HPA aktif, *bottleneck* bergeser ke efisiensi *runtime*, bukan lagi kapasitas kernel.

### 5.4 Verifikasi Service Level Objective (SLO)
- **Error Rate < 0,02%:** **BERHASIL** di semua 9 skenario & semua level beban (0,00%).
- **p95 < 3 detik (Tabel 4.2):**
  - Skenario single-pod (A, B, C): A **GAGAL** di semua beban; B & C **BERHASIL** hanya di 100 VU, **GAGAL** di 300/500 VU.
  - Skenario HPA-aktif (D–I): **BERHASIL** di 100 VU, tetapi **GAGAL** di 300 dan 500 VU untuk semua konfigurasi — meski Skenario H (FrankenPHP+Custom, 3,53 dtk) dan I (Swoole+Custom, 3,65 dtk) paling mendekati target pada 300 VU.
- **Kesimpulan verifikasi:** HPA sangat efektif memenuhi SLO pada beban rendah, tetapi kapasitas infrastruktur yang digunakan pada penelitian ini belum cukup untuk memenuhi target latensi pada beban tinggi (300–500 VU).

### 5.5 Rekomendasi Praktis
1. Prioritaskan *runtime* PHP modern (FrankenPHP/Swoole) dibanding Nginx+PHP-FPM.
2. Jadikan HPA sebagai standar wajib, bukan opsi, untuk skalabilitas.
3. Terapkan optimasi kernel (`net.core.somaxconn`, `fs.file-max`, dll.) untuk koneksi konkuren tinggi.
4. Lakukan pemantauan berkelanjutan (Prometheus/Grafana) untuk terus menyetel konfigurasi.

### 5.6 Pengujian oleh Ahli (Expert Judgment)
Validasi dilakukan oleh **Andri Triyono, S.T., M.T.** (Kepala UPT Sistem Informasi, Universitas An Nuur). Penilaian mencakup tiga aspek:
- **Arsitektur & Metodologi:** kombinasi K3s/Podman/Alma Linux dinilai sesuai; 9 skenario dianggap cukup menjawab rumusan masalah.
- **Pengujian Performa & Analisis:** metrik (RPS, p95, error rate) dan repetisi 10x dinilai tepat & valid; urutan pengaruh (HPA > runtime > kernel) dinilai masuk akal secara teknis.
- **Implikasi & Kontribusi Praktis:** temuan dan rekomendasi dinilai layak diterapkan di lingkungan produksi nyata.

**Saran ahli untuk pengembangan lanjutan:**
1. Lengkapi menjadi desain faktorial 3×2×2 (12 skenario) atau tambahkan skenario "kernel custom tanpa HPA" & "statis multi-replica" untuk memisahkan efek jumlah replika dari mekanisme HPA.
2. Tambahkan analisis **Cluster Autoscaler** (penambahan node, bukan hanya pod).
3. Pecah target SLO antara *critical path* (login, simpan jawaban, submit) vs *non-critical*, dan gunakan metrik latensi lebih ketat (p99/p99.9).

---

## 6. BAB V — Penutup

### 6.1 Kesimpulan
1. Sistem web dengan penskalaan horizontal otomatis (K3s + HPA) di VPS Alma Linux **berhasil diimplementasikan**, terbukti mampu menciptakan lingkungan elastis-reaktif yang menggantikan pendekatan scaling manual.
2. Perbandingan kondisi default vs teroptimasi menunjukkan perbedaan **signifikan**: tanpa scaling sistem mengalami degradasi parah di beban menengah; dengan HPA + kernel tuning, throughput melonjak dan latensi turun tajam.
3. Dampak tuning bersifat **transformatif**: HPA saja meningkatkan throughput hingga **180%** (Nginx+PHP-FPM); runtime modern (FrankenPHP/Swoole) konsisten unggul; optimasi kernel memberi peningkatan tambahan terukur.
4. **Tidak semua konfigurasi memenuhi SLO** (p95 < 3 dtk): semua konfigurasi single-pod gagal di beban menengah ke atas; konfigurasi HPA berhasil di beban rendah tapi belum di beban tinggi (300–500 VU), meski jauh lebih stabil.
5. Rekomendasi praktis berhasil dirumuskan: (a) adopsi runtime PHP modern, (b) HPA sebagai standar wajib, (c) optimasi parameter kernel relevan — kombinasi ketiganya memberi solusi paling performan & andal.

### 6.2 Saran Penelitian Lanjutan
1. Pengujian pada **klaster K3s multi-node** (representasi produksi skala besar).
2. Eksplorasi **metrik HPA lanjutan** (custom metrics seperti RPS, atau metrik eksternal seperti panjang antrian message broker).
3. Analisis pada **jenis beban kerja berbeda** (I/O-bound, memory-bound).
4. **Pengujian durasi panjang** (beberapa jam) untuk mendeteksi isu stabilitas jangka panjang seperti memory leak.

---

## 7. Daftar Pustaka & Lampiran

- Daftar pustaka memuat sekitar **60+ referensi** (jurnal internasional, prosiding konferensi, dan sumber akademik lain) seputar kontainerisasi, Kubernetes/K3s, HPA, Docker vs Podman, runtime PHP, dan load testing — sebagian besar terbitan 2020–2025.
- Lampiran (8 buah): Lembar Uji Expert, Lembar Kontrol Pembimbing 1 & 2, Lembar Selesai Bimbingan, Lembar Siap Sidang, Lembar Surat Tugas, Lembar Revisi Skripsi, Lembar Selesai Revisi Skripsi, dan Dokumentasi Sidang.

---

## 8. Catatan Metodologis Singkat

Skripsi ini adalah penelitian **eksperimental-kuantitatif** dengan desain faktorial parsial (bukan penuh 3×2×2, melainkan 9 dari 12 kemungkinan kombinasi, karena kombinasi single-pod hanya diuji pada kernel *virtual-host*). Kekuatan utamanya adalah pengujian empiris nyata (bukan sekadar studi literatur/simulasi) dengan repetisi 10x per skenario dan validasi oleh pakar eksternal. Keterbatasan yang diakui penulis sendiri: hanya satu jenis aplikasi (I/O-bound web), klaster single-node, HPA hanya berbasis metrik CPU, dan durasi uji relatif singkat (5 menit/iterasi).
