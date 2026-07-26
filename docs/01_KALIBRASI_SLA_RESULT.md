# Hasil Eksperimen Kalibrasi SLA (Service Level Agreement)

**Judul Proyek:** IMPLEMENTASI LSTM-BASED PROACTIVE AUTO-SCALING UNTUK SLA PADA ARSITEKTUR MICROSERVICES DI DOCKER COMPOSE
**Tujuan Pengujian:** Menemukan *bottleneck* kapasitas 1 Pod (Container) per-service dan batas toleransi SLA (500ms).
**Environment Limit:** Limit CPU Docker: `cpus="0.1"` dan Memory: `64M` per kontainer.

---

## 1. Latar Belakang & Setup
Untuk mensimulasikan lingkungan *microservices* yang nyata dan berat, setiap request ke `media-service` dan `content-service` diinjeksi dengan beban komputasi CPU buatan (MD5/SHA256 Hashing) melalui parameter `CPU_LOAD_ITERATIONS`.
Beban CPU ini di-kalibrasi sedemikian rupa agar batas atas kapasitas 1 kontainer (0.1 CPU) terpenuhi pada kisaran **10-14 RPS (Requests Per Second)**.

Berdasarkan kalibrasi presisi terakhir yang disesuaikan dengan arsitektur `maxconn 18` di HAProxy:
- `media-service`: Membutuhkan `CPU_LOAD_ITERATIONS=51000` (karena *payload* balasan hanya *binary image* yang ringan).
- `content-service`: Membutuhkan `CPU_LOAD_ITERATIONS=17000` (lebih rendah karena *service* ini juga harus melakukan *rendering* HTML Template untuk ratusan data secara dinamis, yang memakan CPU cukup besar).

Berikut adalah bukti hasil *Load Testing* menggunakan **K6** untuk masing-masing *service*.

---

## 2. Kalibrasi Single Container (Toleransi & Choking Point)

### A. Beban Normal (17 RPS) - AMAN
Simulasi 17 *Virtual Users* selama 30 detik untuk mengukur kinerja tepat di bawah limit `maxconn 18`.
* **Hasil `media-service`:** P99 Latency berada di angka **61 ms**.
* **Hasil `content-service`:** P99 Latency berada di angka **16 ms**.
* **Kesimpulan:** Latensi sangat aman dan responsif. Batas SLA 500ms **tidak terlanggar**. Sistem masih stabil karena *request* sanggup diproses seketika tanpa masuk antrean HAProxy.

### B. Beban Limit (18 RPS) - HANCUR (Bottleneck)
Skenario yang sama dinaikkan perlahan hingga menyentuh angka 18 RPS.
* **Hasil `media-service`:** P99 Latency melonjak ekstrem menjadi **3.36 detik**.
* **Hasil `content-service`:** P99 Latency melonjak ekstrem menjadi **6.78 detik** (sempat dicoba di angka komputasi yang lebih berat).
* **Kesimpulan:** Container telah mencapai 100% dari limit komputasi 0.1 CPU dan tersedak (*choking*). *Request* yang masuk tertahan di *queue* HAProxy sehingga merusak SLA seketika.

---

## 3. Hasil Pengujian Ekstrem: K6 S2 Peak Slice (39 RPS Spike)

Untuk menguji apakah arsitektur Proactive Auto-scaling kita benar-benar berfungsi melindungi SLA dari lonjakan mendadak, kami mengeksekusi beban kerja riil 5 menit yang diambil tepat dari Puncak Tertinggi *Dataset* S2 ClarkNet (mencapai **39 RPS**).

**Skenario Simulasi:**
1. K6 dijalankan berdampingan dengan *Metrics Exporter* lokal, menembakkan trafik dan melaporkan RPS secara langsung ke Prometheus per detik agar `brain-orchestrator` tidak buta (*blind*).
2. Di siklus ke-96, trafik stabil di kisaran 15-20 RPS.
3. Menjelang detik ke-100, trafik melesat menjadi **30-39 RPS** secara tajam.

**Hasil Observasi Skala (Dari File `peak_39_rps.csv`):**
1. **Prediksi Super Cepat:** Model LSTM memprediksi lonjakan tersebut dalam < 1 detik berdasarkan rekam jejak fluktuasi menit sebelumnya.
2. **Eksekusi Skala Instan:** *Brain Orchestrator* mengeluarkan perintah *Scale-Up*. Berkat arsitektur **Cold Pool via Docker Socket** yang kita bangun, kontainer baru langsung berubah dari `Stopped` ke `Running` dalam **orde milidetik**. Ini sukses menyingkirkan kelemahan `docker-compose scale` biasa yang memakan waktu 3-4 detik.
3. **Queue Ditelan Habis:** Kapasitas maksimal HAProxy seketika naik dari `maxconn 18` menjadi `maxconn 36` tepat sebelum 39 RPS menghantam. 
4. **SLA Aman:** Beban ditelan instan tanpa ada antrean panjang.

---

## 4. Kesimpulan Kebutuhan *Proactive Auto-scaling*
Lonjakan dari 17 RPS ke 18 RPS (selisih hanya 1 RPS) pada arsitektur *microservices* terbukti sudah cukup untuk menyebabkan _CPU Starvation_ di *container*, yang secara instan merusak latensi keseluruhan API hingga berdetik-detik.

Apabila autoscaling dilakukan secara **Reaktif** (berbasis penggunaan CPU historis), HAProxy keburu menahan paket dan *downtime* SLA (latensi 3-6 detik) akan dirasakan oleh klien.

Inilah justifikasi definitif mengapa pendekatan **LSTM-BASED PROACTIVE AUTO-SCALING** ditambah dengan metode **DOCKER SOCKET COLD POOL** sangat krusial. Prediksi lalu lintas di masa depan memungkinkan arsitektur untuk memanaskan kontainer **sebelum** limit *choking* 18 RPS ini terlewati, sehingga SLA tetap terjaga sempurna di bawah 500ms.
