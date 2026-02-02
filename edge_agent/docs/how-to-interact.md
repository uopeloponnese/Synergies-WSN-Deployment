# How to Interact with OpenHAB via Edge Agent

This guide explains how to interact with your OpenHAB instance through the edge-agent using MQTT.

## Prerequisites

1. **Edge-agent is running** - The edge-agent container should be deployed and running
2. **MQTT broker is accessible** - You need access to the MQTT broker configured in the edge-agent
3. **Configuration is set** - The edge-agent should have:
   - Valid `SITE_ID` (from `ID` file or `config.env`)
   - MQTT broker connection details (`MQTT_HOST`, `MQTT_PORT`)
   - OpenHAB connection details (`OH_BASE_URL`, `OH_TOKEN`)

## Understanding the Architecture

```
Your Client/Controller  →  MQTT Broker  →  Edge Agent  →  OpenHAB REST API
```

The edge-agent acts as a **bridge**:
- **Receives** MQTT commands on `wsn/<SITE_ID>/openhab/command`
- **Translates** them to HTTP REST API calls to OpenHAB
- **Returns** responses on `wsn/<SITE_ID>/openhab/response`

## Quick Start: Using the Test Script

The easiest way to interact with OpenHAB is using the provided test script.

### 1. List All OpenHAB Items

```bash
# From the repository root
python3 utils/openhab_mqtt_client.py list
```

This will show all items available in your OpenHAB instance.

### 2. Get an Item's State

```bash
python3 utils/openhab_mqtt_client.py get MyItemName
```

Replace `MyItemName` with an actual item name from your OpenHAB setup.

**Example:**
```bash
python3 utils/openhab_mqtt_client.py get GRC00001MS009_Sensor_temperature
```

### 3. Get Full Item Metadata

```bash
python3 utils/openhab_mqtt_client.py get MyItemName --full
```

This returns complete item information including type, label, state, etc.

### 4. Set an Item's State

```bash
python3 utils/openhab_mqtt_client.py set MySwitch ON
python3 utils/openhab_mqtt_client.py set MyDimmer 50
```

**Examples:**
```bash
# Turn on a switch
python3 utils/openhab_mqtt_client.py set LivingRoom_Light ON

# Set dimmer to 50%
python3 utils/openhab_mqtt_client.py set Bedroom_Dimmer 50

# Turn off
python3 utils/openhab_mqtt_client.py set LivingRoom_Light OFF
```

### 5. Make Custom REST API Calls

```bash
python3 utils/openhab_mqtt_client.py call GET /rest/items
python3 utils/openhab_mqtt_client.py call POST /rest/items/MyItem --data '"ON"'
```

### 6. Monitor MQTT Topics

Watch status updates, telemetry, and responses in real-time:

```bash
python3 utils/openhab_mqtt_client.py monitor
```

Press `Ctrl+C` to stop monitoring.

## MQTT Topics

The edge-agent uses the following topics (where `<SITE_ID>` is your site identifier):

| Topic | Direction | Purpose |
|-------|-----------|---------|
| `wsn/<SITE_ID>/openhab/command` | Client → Agent | Send commands to OpenHAB |
| `wsn/<SITE_ID>/openhab/response` | Agent → Client | Receive responses from OpenHAB |
| `wsn/<SITE_ID>/openhab/status` | Agent → Client | Heartbeat/status messages |
| `wsn/<SITE_ID>/openhab/data` | Agent → Client | Telemetry data |

## Command Format

When sending commands directly via MQTT, use this JSON format:

```json
{
  "method": "GET",
  "endpoint": "/rest/items/MyItem/state",
  "data": null,
  "correlation_id": "unique-uuid-here",
  "idempotency_key": "optional-key-for-caching"
}
```

### Field Descriptions

- **`method`**: HTTP method (`GET`, `POST`, `PUT`, `DELETE`)
- **`endpoint`**: OpenHAB REST API endpoint (e.g., `/rest/items`, `/rest/items/MyItem/state`)
- **`data`**: Request body (for POST/PUT) - can be a string, number, or JSON object
- **`correlation_id`**: Unique identifier to match request with response
- **`idempotency_key`**: (Optional) Key for response caching - same key returns cached response

### Response Format

```json
{
  "correlation_id": "unique-uuid-here",
  "status_code": 200,
  "timestamp": "2025-01-15T10:30:00Z",
  "latency_ms": 45.2,
  "data": "ON"
}
```

## Common Use Cases

### Get All Items

**Using script:**
```bash
python3 utils/openhab_mqtt_client.py list
```

**Direct MQTT:**
```json
{
  "method": "GET",
  "endpoint": "/rest/items",
  "correlation_id": "abc-123"
}
```

### Get Item State

**Using script:**
```bash
python3 utils/openhab_mqtt_client.py get MyItem
```

**Direct MQTT:**
```json
{
  "method": "GET",
  "endpoint": "/rest/items/MyItem/state",
  "correlation_id": "abc-123"
}
```

### Set Item State

**Using script:**
```bash
python3 utils/openhab_mqtt_client.py set MySwitch ON
```

**Direct MQTT:**
```json
{
  "method": "POST",
  "endpoint": "/rest/items/MySwitch",
  "data": "ON",
  "correlation_id": "abc-123"
}
```

### Get Item Metadata

**Using script:**
```bash
python3 utils/openhab_mqtt_client.py get MyItem --full
```

**Direct MQTT:**
```json
{
  "method": "GET",
  "endpoint": "/rest/items/MyItem",
  "correlation_id": "abc-123"
}
```

## Important Notes

### Measurements Don't Flow Automatically

⚠️ **The edge-agent does NOT automatically push measurements.** It's a **request/response bridge**, not a push service.

- You must **actively request** data by sending MQTT commands
- The edge-agent only sends status/heartbeat messages automatically
- To get measurements, you need to query specific items

### Response Caching

The edge-agent supports response caching using `idempotency_key`:
- Same `idempotency_key` returns cached response (if within TTL)
- Useful for retrying commands without duplicate execution
- Cache TTL and size are configurable via environment variables

### Error Handling

If a command fails, the response will include:
```json
{
  "correlation_id": "abc-123",
  "status_code": 404,
  "error": "Item not found",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

Common error codes:
- `404`: Item not found
- `400`: Bad request (invalid data/format)
- `500`: OpenHAB server error

## Troubleshooting

### Edge-agent not responding

1. Check if the container is running:
   ```bash
   docker ps | grep edge-agent
   ```

2. Check edge-agent logs:
   ```bash
   docker logs edge-agent
   ```

3. Verify MQTT connection:
   - Check `MQTT_HOST` and `MQTT_PORT` in `edge_agent/.env`
   - Ensure MQTT broker is accessible

### Can't find items

1. Verify OpenHAB is running:
   ```bash
   docker ps | grep openhab
   ```

2. Check OpenHAB connection:
   - Verify `OH_BASE_URL` in `edge_agent/.env`
   - Test OpenHAB API directly: `curl http://openhab:8080/rest/items`

3. Verify API token:
   - Check `OH_TOKEN` in `edge_agent/.env`
   - Ensure token has proper permissions in OpenHAB

### Timeout errors

- Increase timeout: `python3 utils/openhab_mqtt_client.py get MyItem --timeout 30`
- Check network connectivity between edge-agent and OpenHAB
- Verify OpenHAB is responding (may be overloaded)

## Next Steps

- See [MQTT Topics](mqtt-topics.md) for detailed topic specifications
- See [Overview](overview.md) for architecture details
- See [Security Quickstart](security-quickstart.md) for secure deployment
- See [Runbook](runbook.md) for operational procedures

