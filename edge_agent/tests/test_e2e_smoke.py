from __future__ import annotations

import json
import os
import time
import uuid

import pytest

try:
    import paho.mqtt.client as mqtt
except ModuleNotFoundError:  # pragma: no cover - optional dependency for test env
    mqtt = None


@pytest.mark.skipif(
    mqtt is None or os.getenv("EDGE_AGENT_E2E_ENABLED") != "1",
    reason="Set EDGE_AGENT_E2E_ENABLED=1 and ensure MQTT/openHAB endpoints are reachable.",
)
def test_command_roundtrip():
    broker_host = os.environ["MQTT_HOST"]
    broker_port = int(os.getenv("MQTT_PORT", "8883"))
    command_topic = os.environ["MQTT_COMMAND_TOPIC"]
    response_topic = os.environ["MQTT_RESPONSE_TOPIC"]

    correlation_id = str(uuid.uuid4())
    response_payload = {}

    def on_message(_client, _userdata, message):
        nonlocal response_payload
        payload = json.loads(message.payload.decode("utf-8"))
        if payload.get("correlation_id") == correlation_id:
            response_payload = payload

    client = mqtt.Client(client_id=f"test-{correlation_id}", clean_session=True)
    client.tls_set()
    client.on_message = on_message
    client.connect(broker_host, broker_port, keepalive=30)
    client.subscribe(response_topic, qos=1)
    client.loop_start()

    client.publish(
        command_topic,
        json.dumps(
            {
                "method": "GET",
                "endpoint": "/rest",
                "correlation_id": correlation_id,
            }
        ),
        qos=1,
    )

    timeout = time.time() + 10
    while not response_payload and time.time() < timeout:
        time.sleep(0.1)

    client.loop_stop()
    client.disconnect()

    assert response_payload["correlation_id"] == correlation_id
    assert isinstance(response_payload["status_code"], int)

