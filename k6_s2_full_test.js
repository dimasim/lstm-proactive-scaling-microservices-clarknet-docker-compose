import { SharedArray } from 'k6/data';
import http from 'k6/http';
import { sleep } from 'k6';

// Read the FULL 30% test dataset (4.2 days of data) -> Dimuat HANYA 1 KALI ke memori
const trafficData = new SharedArray('full test traffic', function () {
    return JSON.parse(open('./k6_s2_full_data.json'));
});

export const options = {
    // Pengaturan resource-efficient: Hanya gunakan 1 VU untuk mengatur ritme, tapi izinkan tembakan batch paralel tinggi
    batch: 500,          // Maksimal 500 koneksi paralel per batch
    batchPerHost: 500,
    scenarios: {
        dataset_replay: {
            executor: 'shared-iterations',
            vus: 1, // 1 Pekerja Cerdas (VU) yang akan terus berlari selama 4.2 hari
            iterations: trafficData.length,
            maxDuration: '120h', // Batas aman 5 Hari
        },
    },
};

export default function () {
    // Rekam waktu mulai detik ini
    let start = new Date().getTime();
    
    // Ambil data untuk detik ini sesuai urutan iterasi
    let item = trafficData[__ITER];
    if (!item) return;

    let reqs = [];
    
    // Kumpulkan seluruh peluru (request) Media Service
    for (let i = 0; i < item.rps_media; i++) {
        reqs.push(['GET', 'http://localhost:8000/media']);
    }
    
    // Kumpulkan seluruh peluru (request) Content Service
    for (let i = 0; i < item.rps_content; i++) {
        reqs.push(['GET', 'http://localhost:8000/content']);
    }
    
    // Tembakkan semuanya SECARA BERSAMAAN (Paralel) dalam 1 milidetik
    if (reqs.length > 0) {
        http.batch(reqs);
    }
    
    // Hitung berapa lama proses menembak tadi memakan waktu
    let elapsed = new Date().getTime() - start;
    
    // Sisa waktu dari 1 detik (1000 ms) digunakan untuk "tidur" agar sinkronisasi waktu tetap sempurna 1 detik
    let sleepTime = (1000 - elapsed) / 1000.0;
    if (sleepTime > 0) {
        sleep(sleepTime);
    }
}
