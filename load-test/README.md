# Load test: k6 + Prometheus + Grafana

1. Start Grafana and Prometheus on your PC:
   `docker compose up -d` (in this folder). Grafana: http://localhost:3000
   (no login). In Grafana: Dashboards, New, Import, ID `19665` (k6 Prometheus), pick the `prometheus` datasource.

2. Install k6: `winget install k6`

3. Run (from `load-test/k6`):
   `$env:K6_PROMETHEUS_RW_SERVER_URL="http://localhost:9090/api/v1/write"`
   `$env:K6_PROMETHEUS_RW_TREND_AS_NATIVE_HISTOGRAM="true"`
   `k6 run -o experimental-prometheus-rw -e BASE_URL=http://SERVER:PORT -e PROFILE=smoke script.js`

   Profiles: `ramp5k` (up to 5000 VU, 17 min), `smoke` (5 VU, 30s), `ramp` (up to 400 VU, 10 min), `soak` (50 VU, 30 min).
   Use `-e USERS=100` to change the number of test accounts, `-e RUN_ID=b` for a fresh set.

4. On the server in parallel: `docker stats` and `htop`.

## Open the port for the test (on the server, in the cci project folder)
Create `docker-compose.override.yml` next to `docker-compose.yml`:

    services:
      api:
        ports:
          - "18080:8000"

Then `docker compose up -d api`, and run k6 with `-e BASE_URL=http://173.249.42.44:18080`.
Afterwards delete the override file and run `docker compose up -d api` again (the port closes).
Optionally restrict it: `ufw allow from <your IP> to any port 18080`.

## Cleanup (removes all `@loadtest.example.com` users and their data)
    docker exec -i cci-postgres psql -U cci -d cci < cleanup.sql

Check `left_over = 0` in the output. QR codes redeemed by test users are reset to ACTIVE
(verify the status value against your enum before running if you load-test /qr/redeem).
