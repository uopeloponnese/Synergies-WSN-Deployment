# Edge Agent Overview

The edge agent bridges cloud-initiated MQTT commands to the local openHAB REST API, enabling secure, correlated responses without exposing the automation system to the public internet.

## Deployment

```mermaid
graph TD
    Cloud[External Controller]
    Broker[(MQTT Broker 8883)]
    Agent[Edge Agent Docker Container]
    OH[openHAB REST API]

    Cloud -- QoS1 Commands --> Broker
    Broker -- QoS1 Commands --> Agent
    Agent -- REST --> OH
    OH -- Responses --> Agent
    Agent -- QoS1 Responses --> Broker
    Broker -- Responses --> Cloud
    Agent -- Status/Data --> Broker
    Broker -- Monitoring --> Monitor[Telemetry Subscribers]
```

## Command Lifecycle

```mermaid
sequenceDiagram
    participant Controller
    participant Broker
    participant Agent
    participant openHAB
    Controller->>Broker: Publish Command (QoS1, correlation_id)
    Broker->>Agent: Deliver Command
    Agent->>Agent: Validate schema & cache lookup
    alt Cache hit
        Agent->>Broker: Publish Cached Response (QoS1, from_cache=true)
    else Cache miss
        Agent->>openHAB: HTTP request
        openHAB-->>Agent: HTTP response
        Agent->>Broker: Publish Response (QoS1)
    end
    Broker->>Controller: Deliver Response
```

## State Machine

```mermaid
stateDiagram-v2
    [*] --> Connecting
    Connecting --> Online: MQTT Connected
    Online --> Executing: Command Received
    Executing --> Online: Response Sent
    Online --> Reconnecting: MQTT Drop
    Reconnecting --> Connecting: Backoff Retry
    Reconnecting --> Offline: Max Retries Exceeded
    Offline --> Connecting: Manual Restart
```

## Telemetry Flow

```mermaid
sequenceDiagram
    participant Agent
    participant openHAB
    participant Broker
    participant Observer
    loop Every 60s
        Agent->>openHAB: Poll /rest/items
        openHAB-->>Agent: Item snapshot
        Agent->>Broker: Publish telemetry (QoS0)
        Broker->>Observer: Deliver telemetry
    end
```

## Correlation & Idempotency

```mermaid
flowchart LR
    command[Command message] -->|includes| uuid[correlation_id]
    command -->|optional| idem[idempotency_key]
    idem --> cache[Cache lookup]
    cache -->|hit| responseCached[Return cached response]
    cache -->|miss| proxy[Execute HTTP request]
    proxy --> responseFresh[Publish fresh response]
    responseFresh --> cacheStore[Store in cache with TTL]
```


