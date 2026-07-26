import http from 'k6/http';
import { sleep, check } from 'k6';
import { SharedArray } from 'k6/data';

// Load dataset (CSV)
const data = new SharedArray('S2 Dataset', function() {
    // In actual implementation, we read the CSV and split the array.
    // For now, we mock the logic or read the pre-split S2 dataset if available.
    return [
        { rps_content: 10, rps_media: 5 },
        { rps_content: 15, rps_media: 8 },
        // ... (data generated from S2)
    ];
});

export const options = {
    scenarios: {
        dataset_replay: {
            executor: 'shared-iterations',
            vus: 10,
            iterations: data.length,
            maxDuration: '10m',
        },
    },
};

export default function() {
    const item = data[__ITER];
    
    // Simulate content request
    for (let i = 0; i < item.rps_content; i++) {
        http.get('http://localhost:8000/content');
    }

    // Simulate media request
    for (let i = 0; i < item.rps_media; i++) {
        http.get('http://localhost:8000/media');
    }
    
    // Wait exactly 1 second to mimic the 1-second interval
    sleep(1);
}
