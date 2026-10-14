import http from 'k6/http';
import { check, group, sleep } from 'k6';

const BASE = __ENV.BASE_URL || 'http://localhost:8000';
const USERS = parseInt(__ENV.USERS || '50');
const PASSWORD = 'LoadTest#12345';
const PREFIX = 'lt' + (__ENV.RUN_ID || 'a');
const OK = http.expectedStatuses({ min: 200, max: 299 }, 400, 402, 404, 409);

const profiles = {
  smoke: [{ duration: '30s', target: 5 }],
  ramp: [
    { duration: '1m', target: 20 },
    { duration: '2m', target: 50 },
    { duration: '2m', target: 100 },
    { duration: '2m', target: 200 },
    { duration: '2m', target: 400 },
    { duration: '1m', target: 0 },
  ],
  soak: [
    { duration: '2m', target: 50 },
    { duration: '30m', target: 50 },
    { duration: '1m', target: 0 },
  ],
};

export const options = {
  scenarios: {
    app: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: profiles[__ENV.PROFILE || 'smoke'],
      gracefulRampDown: '30s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<800'],
  },
};

const json = { headers: { 'Content-Type': 'application/json' } };

export function setup() {
  const tokens = [];
  for (let i = 0; i < USERS; i++) {
    const username = `${PREFIX}_${i}`;
    const body = { username, email: `${username}@loadtest.example.com`, password: PASSWORD };
    http.post(`${BASE}/auth/register`, JSON.stringify(body), { ...json, responseCallback: OK });
    const r = http.post(
      `${BASE}/auth/login`,
      JSON.stringify({ username, password: PASSWORD }),
      json,
    );
    if (r.status === 200) tokens.push(r.json('access_token'));
  }
  if (tokens.length === 0) throw new Error('no users could log in');
  return { tokens };
}

function auth(token) {
  return { headers: { Authorization: `Bearer ${token}` }, responseCallback: OK };
}

export default function (data) {
  const token = data.tokens[(__VU - 1) % data.tokens.length];
  const p = auth(token);

  group('shop', () => {
    const list = http.get(`${BASE}/clothing?limit=20`, p);
    check(list, { 'clothing 200': (r) => r.status === 200 });
    http.get(`${BASE}/wardrobe`, p);
    http.get(`${BASE}/users/me/coins`, p);
    if (list.status === 200 && Math.random() < 0.2) {
      const items = list.json('items') || [];
      if (items.length > 0) {
        const item = items[Math.floor(Math.random() * items.length)];
        const id = item.item_id || item.id || item.clothing_id;
        if (id) http.post(`${BASE}/clothing/${id}/purchase`, null, p);
      }
    }
  });
  sleep(Math.random() * 2 + 0.5);

  group('battles', () => {
    const c = http.get(`${BASE}/competitions`, p);
    check(c, { 'competitions 200': (r) => r.status === 200 });
    http.get(`${BASE}/competitions/discover`, p);
    http.get(`${BASE}/leaderboard`, p);
    http.get(`${BASE}/competition-requests/incoming`, p);
  });
  sleep(Math.random() * 2 + 0.5);
}
