# Spesifikasi & Konfigurasi Teknis Final (Tuning SLA)

Dokumen ini berisi rekapitulasi seluruh konfigurasi teknis mendalam yang telah ditala (*tuned*) secara matematis demi menguji arsitektur Proactive Auto-Scaling menggunakan batasan SLA 500ms. Nilai-nilai di bawah ini merupakan fondasi utama sistem.

## 1. Limitasi Resource & Beban Artifisial (Choking Point)

Untuk memaksa sistem bertekuk lutut dan mencapai *bottleneck* pada titik yang bisa dikendalikan (18 RPS), dilakukan pembatasan kapasitas perangkat keras dan penambahan iterasi komputasi buatan (*artificial load*).

*   **Docker Container Limit:**
    *   CPU Limit: `cpus="0.1"` (10% dari 1 inti CPU) per kontainer.
    *   RAM Limit: `mem_limit="64M"` per kontainer.
*   **Media Service (`/media`):**
    *   `CPU_LOAD_ITERATIONS`: **51.000** iterasi (Algoritma SHA256 Hashing).
    *   Sifat komputasi: Berat di perulangan CPU, respon I/O ringan (hanya melempar balik file statis *binary image* JPEG 500KB).
*   **Content Service (`/content`):**
    *   `CPU_LOAD_ITERATIONS`: **17.000** iterasi (Algoritma SHA256 Hashing).
    *   Sifat komputasi: Lebih rendah karena *service* ini sudah memakan banyak CPU bawaan untuk men-*generate* ratusan baris data ke dalam *HTML Template rendering*.

## 2. Parameter Antrean (Queue) HAProxy

Karena *auto-scaling* sangat bergantung pada antrean saat sistem tersedak, HAProxy ditala secara agresif:

*   **Connection Limit (`maxconn`):** Ditetapkan tepat di angka **18** per kontainer *backend*.
    *   *Penjelasan Matematis:* Pada limit komputasi `CPU_LOAD_ITERATIONS` di atas, 1 kontainer akan menggunakan 100% dari 0.1 CPU limitnya saat melayani 18 *request* serentak. Jika trafik melebihi batas 18, permintaan ke-19 akan tertahan di pintu HAProxy dan tidak diteruskan ke *backend*, menyebabkan P99 latensi meledak karena menunggu.
*   **Load Balancing Algorithm:** `leastconn` (memastikan trafik dikirim ke kontainer yang koneksinya paling lengang).

## 3. Konfigurasi Cold Pool (Warming Pool) via Docker Socket

Alih-alih menggunakan perintah `docker-compose scale` standar yang lambat (membutuhkan waktu 3 - 5 detik untuk membuat kontainer dari nol), digunakan teknik **Cold Pool**:

*   **Pre-allocation:** `docker-compose.yml` dikonfigurasi untuk menyalakan 13 replika `media-service` dan 5 replika `content-service` di awal.
*   **Orchestrator Manipulation:** Skrip `brain-orchestrator` menancap ke `/var/run/docker.sock` dan langsung melakukan *Pause/Stop* pada kontainer ekstra tersebut di detik pertama sistem menyala.
*   **Zero-Second Scale-Up:** Ketika LSTM memprediksi lonjakan, orchestrator mengirimkan *HTTP POST* ke Docker Socket (`/containers/{id}/start`). Kontainer berubah status dalam hitungan **milidetik**, menghancurkan *Cold Start Penalty* hingga ke akarnya.

## 4. Parameter Prediksi LSTM (Long Short-Term Memory)

Model LSTM di dalam *Brain Orchestrator* membaca trafik yang masuk (dari metrik Prometheus) dengan parameter observasi sebagai berikut:

*   **Interval Prediksi:** Berjalan setiap **1 detik** (*tick rate*). 
*   **Lookback Window:** Model mengobservasi jejak fluktuasi RPS mundur ke belakang (contoh: 60 detik) untuk menebak 1 langkah ke depan (*next second RPS*).
*   **Safety Margin Scaling:** Konversi dari RPS Prediksi ke jumlah replika dipetakan menggunakan `math.ceil(Predicted_RPS / 15)`. 
    *   *Catatan:* Angka pembagi menggunakan **15** (bukan 18), sebagai sabuk pengaman (*safety margin*) agar kontainer tidak pernah dipaksa bekerja di batas maksimal 100%.

## 5. Parameter Pengujian Load Generator (K6)

Pengujian SLA pamungkas ditala menggunakan K6 dengan eksekusi sinkron terhadap metrik (Prometheus Exporter):

*   **Dataset:** ClarkNet HTTP S2 (Ekstrak Titik Puncak).
*   **Spike Maksimal:** **39 RPS** (Terjadi instan dari 15 RPS).
*   **Timeout & SLA Target:** SLA diukur pada `P99 < 500ms`. Untuk mencegah K6 *hang* akibat koneksi menggantung berjam-jam saat sistem *crash*, ditambahkan batas waktu (*timeout*) pada level *request* sebesar 1.5 detik.
