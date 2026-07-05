# PROPOSAL & RENCANA DEPLOYMENT SISTEM: VIRTUAL SERVICE TESTBED FOR PROACTIVE AUTO-SCALING MICROSERVICES
**Studi Kasus: Pengujian Proactive Auto-scaling Berbasis LSTM Menggunakan Dataset Beban Kerja ClarkNet**

---

## 1. Pendahuluan & Abstraksi Sistem

Riset tugas akhir/skripsi ini bertujuan untuk membangun dan menguji efektivitas sistem **Proactive Auto-scaling** pada arsitektur *microservices* menggunakan model peramalan *Long Short-Term Memory* (LSTM). Untuk melatih dan menguji model AI tersebut, diimplementasikan sebuah *virtual service testbed* yang stabil, terukur, dan mampu mereproduksi beban kerja dunia nyata secara presisi.

Dokumen ini memaparkan rencana *deployment* terperinci dari arsitektur *testbed* virtual tersebut. Seluruh layanan dikemas dalam bentuk kontainer (*containerized services*) menggunakan **Docker Compose**, disalurkan melalui gerbang beban **HAProxy**, dipantau menggunakan **Prometheus & cAdvisor**, serta beban kerjanya disimulasikan menggunakan generator beban berbasis python yang mereproduksi trafik **ClarkNet Web Server Dataset (1995)**.

---

## 2. Arsitektur Deployment (Deployment Architecture)

Sistem di-deploy sebagai lingkungan virtual terisolasi yang terdiri dari 6 komponen utama yang saling berinteraksi:

```mermaid
graph TD
    Client[Python Load Generator] -->|Port 8000: HTTP Traffic| HAProxy[HAProxy Load Balancer]
    
    subgraph Microservices Layer
        HAProxy -->|Route /media| MediaService[Media Service - FastAPI]
        HAProxy -->|Route /content| ContentService[Content Service - FastAPI]
    end

    subgraph Monitoring & Telemetry Layer
        cAdvisor[cAdvisor Container Metrics] -->|Scrape Container Stats| DockerEngine[Docker Engine /cgroups]
        Prometheus[Prometheus DB] -->|Scrape Metrics Port 9090| HAProxy
        Prometheus -->|Scrape Metrics Port 8088| cAdvisor
        Dashboard[Go Dashboard Service - Port 3002] -->|Query Metrics| Prometheus
    end

    subgraph AI Scaling Controller (Future)
        LSTMController[LSTM Scaling Engine] -->|Predictive Scaling Decisions| DockerSocket[Docker Daemon Socket]
        LSTMController -->|Get Historical Telemetry| Prometheus
    end
```

### Detail Komponen Arsitektur:
1. **Load Balancer (HAProxy):** Berfungsi sebagai *Single Entry Point* sistem. HAProxy menerima semua trafik masuk dari klien pada port `8000`, melakukan penyaringan URL (*path-based routing*), dan mendistribusikan beban secara *round-robin* ke replika microservice yang aktif.
2. **Media Service (FastAPI):** Layanan mikro yang khusus bertugas untuk melayani permintaan aset media (gambar JPG besar berukuran 2MB - 4.5MB). Setiap permintaan akan memicu perhitungan hash SHA-256 secara asinkron untuk menyimulasikan beban I/O dan CPU pemrosesan media.
3. **Content Service (FastAPI):** Layanan mikro yang menangani permintaan halaman konten HTML dinamis bergaya portal ISP ClarkNet tahun 1995. Menggunakan mesin template Jinja2 untuk Server-Side Rendering (SSR) dan menjalankan kalkulasi enkripsi MD5 ringan untuk mensimulasikan proses otentikasi billing pelanggan.
4. **cAdvisor (Container Advisor):** Agen pengumpul statistik resource kontainer yang berjalan secara *daemon*. cAdvisor langsung membaca data pemakaian CPU, memori, dan I/O dari kernel cgroups Linux untuk setiap kontainer microservice yang sedang berjalan.
5. **Prometheus:** Database *time-series* yang mengumpulkan (*scrape*) data telemetri dari cAdvisor dan HAProxy secara berkala (interval 1 detik) untuk kebutuhan penyimpanan histori performa.
6. **Dashboard Service:** Aplikasi visualisasi web *real-time* berbasis bahasa pemrograman Go (port `3002`) untuk memantau grafik metrik (RPS, CPU, RAM, jumlah replika aktif) selama pengujian berlangsung.

---

## 3. Rencana Kontainerisasi (Containerization Plan)

Setiap komponen dikemas menggunakan image Docker yang dioptimalkan untuk meminimalkan *resource footprint* (skala ukuran image kecil) dan meningkatkan kecepatan proses *startup*:

| Service | Base Image | Metode Build | Port Internal | Deskripsi Port Eksternal |
| :--- | :--- | :--- | :---: | :---: |
| `haproxy` | `haproxy:2.8-alpine` | Pre-built Image | `80`, `8404` | `8000` (HTTP), `8404` (Prometheus Exporter) |
| `media-service` | `python:3.10-slim` | Custom Dockerfile | `8000` | Tidak diekspos langsung (Lewat HAProxy) |
| `content-service`| `python:3.10-slim` | Custom Dockerfile | `8000` | Tidak diekspos langsung (Lewat HAProxy) |
| `cadvisor` | `gcr.io/cadvisor/cadvisor` | Pre-built Image | `8080` | `8088` (Metrik Container) |
| `prometheus` | `prom/prometheus:v2.45.0` | Pre-built Image | `9090` | `9090` (Prometheus Web UI) |
| `dashboard` | `golang:1.20-alpine` | Custom Dockerfile | `3002` | `3002` (Dashboard Visualisasi) |

### Strategi Pembatasan Resource (Resource Limiting) untuk Pengujian LSTM:
Untuk mensimulasikan kondisi kegagalan SLA dan memicu *auto-scaling* secara nyata selama pengujian LSTM, batas atas kapasitas kontainer (*resource limit*) diatur pada file `docker-compose.yml` saat pengujian model dimulai:
```yaml
  content-service:
    deploy:
      resources:
        limits:
          cpus: '0.20'      # Membatasi container maksimal menggunakan 20% dari 1 Core CPU Host
          memory: 128M      # Membatasi memori maksimal 128 MegaBytes
```
*Catatan: Pembatasan ini sengaja dinonaktifkan pada tahap pengumpulan dataset awal agar data penggunaan CPU/RAM murni mencerminkan kebutuhan asli beban kerja tanpa terpotong (*throttling*).*

---

## 4. Jaringan Sistem (Networking Plan)

Jaringan virtual diisolasi menggunakan **Docker Bridge Network** khusus bernama `clarknet-net`. Keuntungan dari metode ini adalah:

1. **Internal DNS Resolution:** Layanan dapat saling berkomunikasi satu sama lain menggunakan nama service Docker mereka (misalnya, HAProxy menghubungi `content-service:8000` secara internal). HAProxy memanfaatkan DNS resolver Docker (`127.0.0.11:53`) untuk memantau IP kontainer baru yang ditambahkan selama proses *scaling*.
2. **Isolasi Keamanan:** `media-service` dan `content-service` sengaja tidak memetakan (*mapping*) port mereka ke port host fisik. Satu-satunya akses masuk dari luar host menuju microservices harus melewati `haproxy` di port `8000`. Ini mencegah manipulasi trafik pengujian di luar load balancer.

---

## 5. Rencana Keamanan (Security Plan)

Meskipun di-deploy sebagai lingkungan virtual untuk tugas akhir, standar keamanan minimal tetap diterapkan:

* **Minimal Exposed Ports:** Hanya port yang krusial untuk pemantauan dan pengujian beban saja yang diekspos ke host OS luar (Port `8000` untuk load balancer, `3002` untuk dashboard, dan `9090` untuk Prometheus).
* **Read-Only Volumes:** File konfigurasi sensitif seperti `haproxy.cfg` dan `prometheus.yml` dipasang (*mounted*) ke dalam container dengan hak akses **Read-Only (`:ro`)** untuk mencegah modifikasi tidak sah oleh proses runtime container.
* **Network Partitioning:** Pemisahan fungsionalitas jaringan di mana generator beban hanya dapat mengakses frontend HTTP HAProxy tanpa memiliki akses langsung ke port metrik Prometheus atau cAdvisor.

---

## 6. Pemantauan & Pencatatan (Monitoring & Logging Plan)

Sistem pengumpulan metrik dirancang secara efisien menggunakan pendekatan **Pull-Based Metrics Collection**:

```text
+--------------+                   +------------+
|  cAdvisor    |<--[Scrapes]-------|            |
+--------------+                   |            |
                                   | Prometheus |<--[Poll Metrics]-- Go Dashboard
+--------------+                   |            |
|  HAProxy     |<--[Scrapes]-------|            |
+--------------+                   +------------+
```

### Metrik Kunci yang Dipantau:
1. **Metrik Beban Trafik (HAProxy):**
   * `haproxy_backend_http_requests_total`: Mengukur total request per detik (RPS) masuk untuk memvalidasi kesesuaian beban kerja dengan dataset ClarkNet.
2. **Metrik Kinerja Kontainer (cAdvisor):**
   * `container_cpu_usage_seconds_total`: Digunakan untuk menghitung persentase beban CPU kontainer secara berkala.
   * `container_memory_working_set_bytes`: Mengukur jumlah memori RAM aktif yang digunakan oleh kontainer secara akurat (menghindari kesalahan deteksi dari memori cache virtual).
3. **Metrik Replikasi (cAdvisor):**
   * `count(container_last_seen{container_label_...} > time() - 15)`: Mengukur jumlah instans/replika kontainer yang saat ini aktif beroperasi di dalam Docker Engine.

---

## 7. Rencana Skalabilitas (Scalability Plan)

Sistem auto-scaling dirancang untuk menangani beban kerja fluktuatif secara adaptif dengan dua pendekatan utama:

### A. Reactive Auto-scaling (Baseline / Pembanding)
* Menggunakan nilai ambang batas (*threshold*) CPU statis (misalnya, jika rata-rata penggunaan CPU kontainer di atas **70%** selama 15 detik berturut-turut, sistem akan menambah 1 replika kontainer baru).

### B. Proactive Auto-scaling (Fokus Utama Penelitian AI)
* **Prediksi Beban Kerja:** Model LSTM dilatih menggunakan data histori RPS dari `collected_metrics.csv` untuk memprediksi trafik 15 hingga 30 detik ke depan.
* **Skalabilitas Preventif:** Jika LSTM mendeteksi akan terjadi lonjakan trafik di atas ambang kapasitas aman dalam 30 detik mendatang, sinyal skalabilitas dikirimkan ke Docker Daemon Socket untuk melakukan replikasi kontainer **sebelum** lonjakan trafik yang sebenarnya tiba di server. Hal ini meniadakan latensi waktu tunggu *bootup* kontainer (Cold-Start Delay) sehingga SLA tetap terjaga di level 100%.
* **Strategi Cooldown & Pelemahan Beban (CDT & GDS):** 
  * *Cooldown Timer (CDT):* Menetapkan jeda waktu (misal 30 detik) setelah aksi scaling agar sistem stabil terlebih dahulu sebelum memutuskan aksi scaling berikutnya.
  * *Gradually Decreasing Strategy (GDS):* Pengurangan jumlah kontainer secara bertahap (satu per satu) saat trafik menurun untuk menghindari pemutusan koneksi yang mendadak bagi user aktif.


