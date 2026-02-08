/**
 * CompanySearch load test – 60 RPS search + 60 RPS filter (tags) in parallel
 *
 * Run: k6 run load-test/k6-search-and-filters.js
 * Override base URL: k6 run -e BASE_URL=https://companysearch.example.com load-test/k6-search-and-filters.js
 *
 * Targets:
 * - 60 RPS search (POST /search)
 * - 60 RPS filter operations (GET /tags) in parallel
 * No performance degradation = low error rate, stable p95 latency.
 */
import http from 'k6/http';
import { check } from 'k6';
import { Rate } from 'k6/metrics';
import { execution } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

const searchErrorRate = new Rate('search_errors');
const tagsErrorRate = new Rate('tags_errors');

export const options = {
  scenarios: {
    search_60_rps: {
      executor: 'constant-rate',
      rate: 60,
      timeUnit: '1s',
      duration: '1m',
      preAllocatedVUs: 20,
      maxVUs: 40,
      startTime: '0s',
    },
    tags_60_rps: {
      executor: 'constant-rate',
      rate: 60,
      timeUnit: '1s',
      duration: '1m',
      preAllocatedVUs: 20,
      maxVUs: 40,
      startTime: '0s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<2000'],
    search_errors: ['rate<0.01'],
    tags_errors: ['rate<0.01'],
  },
};

export function setup() {
  return { userId: `load-test-${Date.now()}` };
}

export default function (data) {
  if (execution.scenario.name === 'search_60_rps') {
    const res = http.post(
      `${BASE_URL}/search`,
      JSON.stringify({
        query: 'tech companies',
        page: 1,
        size: 20,
        sort: 'relevance',
      }),
      { headers: { 'Content-Type': 'application/json' } }
    );
    const ok = check(res, { 'search status 200': (r) => r.status === 200 });
    searchErrorRate.add(!ok);
  } else {
    const res = http.get(`${BASE_URL}/tags/${data.userId}`);
    const ok = check(res, { 'tags status 200': (r) => r.status === 200 });
    tagsErrorRate.add(!ok);
  }
}
