import { SharedArray } from 'k6/data';
import http from 'k6/http';
import { check } from 'k6';

// Read the extracted 3-minute demo dataset
const trafficData = new SharedArray('demo traffic', function () {
    return JSON.parse(open('./k6_demo_sidang.json'));
});

// Dynamically generate stages for ramping-arrival-rate
let mediaStages = [];
let contentStages = [];

// Start with 1s at target 0 (or first target) to warmup
let first_media = trafficData[0].rps_media;
let first_content = trafficData[0].rps_content;

trafficData.forEach((row) => {
    mediaStages.push({ target: row.rps_media, duration: '1s' });
    contentStages.push({ target: row.rps_content, duration: '1s' });
});

export const options = {
    // Drop thresholds to ensure k6 doesn't abort early if SLA fails
    thresholds: {
        'http_req_duration': ['p(99)<2000'], // P99 < 2s
        'http_req_failed': ['rate<0.05'],    // Errors < 5%
    },
    scenarios: {
        media_workload: {
            executor: 'ramping-arrival-rate',
            startRate: first_media,
            timeUnit: '1s',
            preAllocatedVUs: 100, // Preallocate enough VUs to handle peak concurrency
            maxVUs: 2000,         // Absolute max VUs
            stages: mediaStages,
            exec: 'media_req',
        },
        content_workload: {
            executor: 'ramping-arrival-rate',
            startRate: first_content,
            timeUnit: '1s',
            preAllocatedVUs: 100,
            maxVUs: 2000,
            stages: contentStages,
            exec: 'content_req',
        },
    },
};

export function media_req() {
    let res = http.get('http://localhost:8000/media');
    check(res, { 'status is 200': (r) => r.status === 200 });
}

export function content_req() {
    let res = http.get('http://localhost:8000/content');
    check(res, { 'status is 200': (r) => r.status === 200 });
}
