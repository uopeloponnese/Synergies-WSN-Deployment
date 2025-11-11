# Security Quickstart

This guide highlights the minimum steps required to deploy the edge agent with TLS, authentication, and least-privilege access controls.

## 1. Provision Certificates

1. Generate a dedicated device key pair.
2. Sign the CSR with the MQTT broker's CA.
3. Distribute the following to each site agent host:
   - `mqtt_ca.crt` (trusted CA bundle)
   - `mqtt_client.crt` (client certificate)
   - `mqtt_client.key` (private key, 0600 permissions)

## 2. Configure Broker ACLs

Grant the device permissions scoped to its namespace:

```
allow publish wsn/<site>/openhab/response
allow publish wsn/<site>/openhab/status
allow publish wsn/<site>/openhab/data
allow subscribe wsn/<site>/openhab/command
```

Reject all other topics by default.

## 3. Populate Environment

Copy `.env.example` to `.env` and fill in secrets _via Docker secrets when possible_:

```
MQTT_HOST=broker.example.com
MQTT_PORT=8883
MQTT_TLS=true
MQTT_CA=/run/secrets/mqtt_ca.crt
MQTT_CERT=/run/secrets/mqtt_client.crt
MQTT_KEY=/run/secrets/mqtt_client.key
OH_TOKEN=... # openHAB personal access token
```

Never hardcode credentials in images. Use Docker secrets or host-level secret managers.

## 4. Harden Runtime

- Run the container as the non-root `edgeagent` user (default Dockerfile behaviour).
- Mount `/etc/ssl/certs` read-only to provide CA trust.
- Rotate certificates by replacing files in `secrets/` and running `docker compose restart edge-agent`.

## 5. Logging & Monitoring

- All logs are JSON-friendly and include `correlation_id` for traceability.
- Export MQTT broker logs to detect unauthorized access attempts.

## 6. Regular Maintenance

- Enforce certificate expiry ≤ 365 days.
- Run vulnerability scans on the container image (`python:3.11-slim` base).
- Apply openHAB security patches and rotate REST tokens periodically.

