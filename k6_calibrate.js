import http from 'k6/http';
import { check } from 'k6';

export const options = {
  scenarios: {
    calibrate: {
      executor: 'constant-arrival-rate',
      rate: __ENV.TARGET_RPS, 
      timeUnit: '1s',
      duration: '15s',
      preAllocatedVUs: 10,
      maxVUs: 100,
    },
  },
};

export default function () {
  const target = __ENV.TARGET_SERVICE; 
  const url = `http://localhost:8000/${target}`; 
  const res = http.get(url);
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
}
