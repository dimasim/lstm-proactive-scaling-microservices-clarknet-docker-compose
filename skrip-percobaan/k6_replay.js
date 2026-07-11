
import http from 'k6/http';

export const options = {
  scenarios: {
    media_scenario: {
      executor: 'ramping-arrival-rate',
      startRate: 0,
      timeUnit: '1s',
      preAllocatedVUs: 150,
      maxVUs: 400,
      stages: [
        { target: 9, duration: '1s' },
        { target: 6, duration: '1s' },
        { target: 3, duration: '1s' },
        { target: 0, duration: '1s' },
        { target: 3, duration: '1s' }
      ],
      exec: 'media_request',
    },
    content_scenario: {
      executor: 'ramping-arrival-rate',
      startRate: 0,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      maxVUs: 150,
      stages: [
        { target: 0, duration: '1s' },
        { target: 0, duration: '1s' },
        { target: 0, duration: '1s' },
        { target: 0, duration: '1s' },
        { target: 0, duration: '1s' }
      ],
      exec: 'content_request',
    },
  },
};

export function media_request() {
  http.get('http://localhost:8000/media', { timeout: '1.5s' });
}

export function content_request() {
  http.get('http://localhost:8000/content', { timeout: '1.5s' });
}
