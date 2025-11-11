# MQTT Topics & QoS Matrix

All MQTT resources are scoped per site using the prefix:

```
wsn/<site_id>/openhab/
```

## Topics

| Topic Suffix | Direction | QoS | Retained | Purpose |
| --- | --- | --- | --- | --- |
| `command` | Cloud → Edge | 1 | No | Execute REST calls against openHAB. Persistent session ensures delivery once online. |
| `response` | Edge → Cloud | 1 | No | Results correlated via `correlation_id`. |
| `status` | Edge → Cloud | 1 | Yes | Online/offline heartbeat. LWT publishes `{"status":"offline"}`. |
| `data` | Edge → Cloud | 0 | No | Periodic telemetry snapshots or events. |

## ACL Recommendations

| Principal | Allowed Publish | Allowed Subscribe |
| --- | --- | --- |
| Edge Agent | `response`, `status`, `data` | `command` |
| Controller | `command` | `response` |
| Observers / Monitoring | _None_ | `status`, `data` |

## Session Settings

- `Clean Session`: `false` to resume QoS1 deliveries after reconnect.
- `Persistent Store`: Configure broker to buffer up to 100 QoS1 messages per client to avoid message loss during brief outages.

## Message Size & Rate Guidance

- Commands should be ≤ 32 KB to ensure prompt delivery.
- Telemetry default interval is 60 seconds; adjust via `TELEMETRY_INTERVAL_SEC`.
- Use idempotency keys for retrying commands without duplicate execution.


