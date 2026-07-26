# Referensi Jurnal: Predictive Autoscaling of Microservices Hosted in Fog Microdata Center

**Penulis:** Muhammad Abdullah, Waheed Iqbal, Arif Mahmood, Faisal Bukhari, dan Abdelkarim Erradi
**Jurnal:** IEEE Systems Journal, Vol. 15, No. 1, March 2021

## Ringkasan Eksekutif
Penelitian ini mengusulkan metode *predictive autoscaling* untuk arsitektur *microservices* berbasis kontainer di infrastruktur *Fog Computing* (Microdata Center). Tujuannya adalah untuk meminimalkan pelanggaran *Service Level Objective* (SLO) terkait waktu respons (latensi).

## Relevansi dengan Skripsi Anda
Paper ini **sangat relevan** dan merupakan referensi sempurna (sebagai *State-of-the-Art*) untuk skripsi Anda tentang "Implementasi LSTM-Based Proactive Auto-scaling untuk SLA pada Arsitektur Microservices di Docker Compose".

*   **Persamaan:** 
    *   Sama-sama bertujuan menjaga SLA/SLO (Waktu respons / latensi).
    *   Sama-sama menggunakan pendekatan proaktif/prediktif menggunakan *Machine Learning*.
    *   Sama-sama diterapkan pada lingkungan *microservices* dan kontainer (Docker).
    *   Sama-sama menggunakan **Dataset ClarkNet** untuk evaluasi trafik.
*   **Perbedaan (Keterbaruan / Novelty Anda):** 
    *   Penelitian ini menggunakan model prediksi **Decision Tree Regression (DTR)** untuk menentukan *scaling* dan **Elastic Net (EN)** untuk prediksi trafik.
    *   Skripsi Anda mengusulkan penggunaan **Long Short-Term Memory (LSTM)** yang secara teori jauh lebih superior dalam menangani data *time-series* berurutan dibandingkan *Decision Tree*. Ini bisa menjadi nilai jual utama (novelty) skripsi Anda!

## Metodologi Penelitian di Paper
1.  **Pengumpulan Data Latih:** Peneliti menggunakan metode *reactive autoscaling* (sebagai *baseline*) dengan trafik yang terus meningkat (*increasing synthetic workload*) untuk mendapatkan log penggunaan resource dan latensi. CPU Threshold yang digunakan adalah 75% untuk *scale-out* dan 50% untuk *scale-in*.
2.  **Penetapan SLA/SLO:** SLA diatur sebagai **User-Defined Threshold ($\tau_{slo}$)**. Cara mereka melatih model sangat unik: mereka menyaring data log historis, lalu **membuang semua baris data yang mengalami pelanggaran SLA**. Dengan demikian, model ML hanya dilatih menggunakan log data dari kondisi sistem yang sehat, sehingga model belajar: *"Untuk melayani request sebanyak $X$ dengan target SLA sebesar $Y$, sistem butuh jumlah kontainer $Z$"*.
3.  **Pemodelan Prediksi Trafik & Jeda Waktu:** Mereka memprediksi beban untuk **interval waktu berikutnya ($t+1$)**. Berdasarkan skenario pengujiannya, satu interval waktu ($t$) bernilai **1 Menit**. Artinya sistem ini meramalkan beban untuk **1 menit ke depan**. 
    *   Sistem memonitor 2 jenis *window size* historis: $k=3$ (melihat data 3 menit terakhir untuk tren jangka pendek) dan $k=11$ (melihat 11 menit terakhir untuk tren panjang) lalu prediksi keduanya dirata-ratakan.
4.  **Pemodelan Autoscaling Policy:** Model DTR dilatih untuk menerima *input*: `(Prediksi jumlah request, Target Waktu Respons)` dan menghasilkan *output*: `(Jumlah kontainer yang dibutuhkan)`.
5.  **Skenario Uji:** Menggunakan 2 *microservices* (FFT dan Machine Learning App) dan 5 jenis dataset: *Increasing, Periodic, Wikipedia, World Cup, dan ClarkNet*.

## Hasil Evaluasi
*   Metode prediktif mereka terbukti menurunkan persentase pelanggaran SLO secara drastis dibandingkan autoscaling reaktif.
*   Pada kasus **ClarkNet Workload**: Autoscaling reaktif menghasilkan 5.577% (untuk aplikasi FFT) dan 17.845% (untuk aplikasi ML) pelanggaran SLO. Sedangkan metode prediktif mereka menurunkannya menjadi hanya **0.174%** dan **13.679%**.
*   Sistem prediktif menggunakan rata-rata sekitar 9.20% resource tambahan di server dibandingkan reaktif, namun menghemat penolakan request hingga 75.51% dan pelanggaran SLO hingga 77.53%.

## Pelajaran untuk Implementasi Skripsi Anda
1.  **Baseline Reaktif:** Pastikan Anda membandingkan hasil LSTM Anda dengan sistem *autoscaling reaktif* (seperti *CPU-based autoscaling*). Paper ini membuktikan bahwa metode prediktif jauh mengungguli metode reaktif yang sering terlambat *scaling*.
2.  **Kombinasi 2 Tahap:** Paper ini secara implisit melakukan 2 hal: (1) Memprediksi beban trafik dulu, baru kemudian (2) Menghitung berapa kontainer yang dibutuhkan dari prediksi tersebut. Skema "Brain Orchestrator" Anda sudah sejalan dengan konsep ini.
3.  **Metrik Evaluasi:** Selain latensi (SLA), Anda juga bisa mencantumkan "Jumlah persentase pelanggaran SLA" atau jumlah *request* yang di-*drop* (error) sebagai metrik evaluasi yang kuat, meniru paper ini.
