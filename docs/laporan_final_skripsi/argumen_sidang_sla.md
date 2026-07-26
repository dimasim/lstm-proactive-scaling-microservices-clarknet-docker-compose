# Argumen Pertahanan Sidang: Pertanyaan-Pertanyaan Kritis

Dokumen ini berisi draf argumen / jawaban yang harus Anda sampaikan ketika dosen penguji menanyakan perihal hasil SLA latensi dan metrik model.

---

## 1. Skenario Pertanyaan: Pelanggaran SLA Latensi P99
*"Sistem Anda menetapkan SLA maksimal 500 ms. Tapi di hasil K6, terlihat P95 menyentuh 1.28 detik dan P99 menyentuh 2.86 detik. Kenapa Anda menyimpulkan bahwa sistem ini berhasil?"*

### Jawaban Pembelaan (Defense):
"Terima kasih atas pertanyaannya, Bapak/Ibu. Memang betul bahwa pada persentil ke-95 (P95) dan persentil ke-99 (P99), waktu respons melambat hingga melewati batas 500 ms. Namun, ada tiga alasan krusial mengapa sistem ini dikategorikan sangat berhasil secara *engineering*:"

1. **Mayoritas Absolut Memenuhi SLA (P90 Lulus):**
   "Selama simulasi badai Skenario 2 (volatilitas ekstrem S2), rata-rata latensi sistem berhasil dijaga di angka sangat cepat yakni **162 milidetik**. Bahkan untuk 90% dari keseluruhan beban (*Request*), metrik P90 mencatat angka **294 milidetik**, yang artinya 90% pengguna sama sekali tidak merasakan kelambatan dan sepenuhnya sesuai dengan target SLA 500 ms."

2. **Dampak dari 0.17% Under-Provisioning (Miss-Prediction):**
   "Pelambatan yang menimpa sisa 5-10% *request* (P95 dan P99) murni merupakan dampak dari **0.17% Under-Provisioning** yang dihasilkan oleh model. Karena model diuji pada data 1-detik yang sangat ekstrem (S2), terdapat sepersekian detik di mana model sedikit keliru (*miss-prediction*) dalam menebak puncak tertinggi, sehingga sistem kekurangan pasokan kontainer. Kekurangan sesaat inilah yang memicu penumpukan antrean koneksi di *Load Balancer*, yang pada akhirnya mendongkrak angka latensi P99."

3. **Error Rate 0.00% (The Ultimate Victory):**
   "Meski terdapat antrean selama 1-2 detik akibat keterlambatan prediksi (*under-provisioning*), arsitektur *Load Balancer* (HAProxy) sukses besar menahan koneksi tersebut hingga kontainer tambahan akhirnya menyala. Hasil K6 membuktikan **Error Rate = 0.00%**. Jika kita menggunakan model *baseline* lain (seperti ARIMA dengan *under-provisioning* 0.45%) atau tanpa *auto-scaling* sama sekali (11.99%), antrean ini pasti akan berujung pada memori penuh dan koneksi *timeout / HTTP 503* (Downtime). Namun dengan LSTM, kelambatan 5-10% request berhasil dikompromikan tanpa ada **satu pun** request yang terputus atau tertolak."

---

## 2. Skenario Pertanyaan: Kekurangan Metrik CPU dan RAM
*"Di skripsi Anda, model LSTM hanya membaca metrik Request Per Second (RPS). Bukankah seharusnya Auto-Scaling modern juga membaca CPU dan RAM?"*

### Jawaban Pembelaan (Defense):
"Pertanyaan yang sangat tajam, Bapak/Ibu. Betul sekali, di industri sesungguhnya, metrik utilisasi CPU dan RAM sangat krusial. Namun, ada alasan ilmiah spesifik mengapa pada penelitian ini metrik CPU dan RAM tidak dimasukkan sebagai *input* model:"

1. **Beban Tersimulasi Homogen (Redundansi Fitur):**
   "Pada batasan masalah penelitian saya, *endpoint* dari setiap *microservices* (`media-service` dan `content-service`) disimulasikan memiliki beban komputasi yang seragam (homogen). Artinya, setiap *request* yang masuk memberikan beban CPU yang identik. Secara matematis, grafik penggunaan CPU dan RAM pada simulasi ini akan berbanding lurus (korelasi linear 1:1) dengan lonjakan RPS. Memasukkan metrik CPU/RAM ke dalam LSTM pada simulasi ini hanya akan menghasilkan data redundan (mubazir) yang tidak memberikan informasi multidimensi baru bagi model."

2. **Jalan Keluar untuk Beban Heterogen (Future Work):**
   "Akan tetapi, pada bagian *Saran* di Bab 5, saya secara eksplisit merekomendasikan peneliti selanjutnya—yang mungkin menggunakan aplikasi sungguhan dengan beban heterogen (seperti kompresi video versus pemuatan teks)—untuk wajib memasukkan CPU dan RAM. Karena pada beban heterogen, 1.000 *request* teks mungkin hanya memakan 5% CPU, sedangkan 1.000 *request* kompresi memakan 90% CPU. Pada skenario itulah prediksi *Multivariate* (RPS + CPU + RAM) akan bersinar terang."

### Pesan Kunci:
Sistem yang berhasil menahan 0% *Error Rate* pada *peak load* S2 yang ekstrem adalah sebuah pencapaian luar biasa. Di ranah arsitektur sesungguhnya (*Production*), pelambatan sesaat (P99) jauh lebih bisa ditolerir secara bisnis dibandingkan terputusnya transaksi pengguna (*Error*). Anda juga membuktikan bahwa Anda memahami betul batasan simulasi Anda dan tahu cara meningkatkannya di level *Enterprise* sesungguhnya.
