# Edge Agent Runbook

## Installation

1. Copy `.env.example` to `.env` and update values for the target site.
2. Place TLS materials under `secrets/` (`ca.crt`, `client.crt`, `client.key`).
3. Build and launch:
   ```
   docker compose -f edge_agent/docker-compose.yml up -d --build
   ```
4. Confirm container logs show `MQTT connected` and `Telemetry loop active`.

## Upgrade

1. Pull latest changes from `feature/mqtt-control-plane`.
2. Rebuild image: `docker compose -f edge_agent/docker-compose.yml build`.
3. Redeploy: `docker compose -f edge_agent/docker-compose.yml up -d`.
4. Monitor container logs for anomalies during the first 10 minutes.

## Certificate Rotation

1. Replace files inside `edge_agent/secrets/`.
2. Run `docker compose -f edge_agent/docker-compose.yml restart edge-agent`.
3. Verify new certificate expiry with `openssl x509 -in secrets/client.crt -noout -enddate`.

## Health Checks

- MQTT: `mosquitto_sub -h <broker> -t wsn/<site>/openhab/status -q 1`.
- Command probe:
  ```
  python edge_agent/examples/publish_command.py \
    --host <broker> --port 8883 --command-topic wsn/<site>/openhab/command \
    --response-topic wsn/<site>/openhab/response \
    --endpoint /rest/systeminfo
  ```

## Troubleshooting

| Symptom | Checks |
| --- | --- |
| MQTT connection refused | Validate credentials, TLS paths, broker ACLs. |
| Commands hang | Ensure `CleanSession=false`; verify controller subscribes to correct `response` topic. |
| HTTP 401/403 responses | Confirm openHAB token scope and expiry. |
| Telemetry gaps | Review logs for publish errors; ensure telemetry interval is not > 300 seconds. |

## Disaster Recovery

1. Stop container: `docker compose -f edge_agent/docker-compose.yml down`.
2. Inspect cached responses: located in-memory only; restart resets cache (no persistent storage).
3. Restore `.env` and secrets from secure backup.
4. Recreate container and verify telemetry resumes.

