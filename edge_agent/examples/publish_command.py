#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import queue
import uuid
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish a command to the edge agent and await the response.")
    parser.add_argument("--host", required=True, help="MQTT broker host")
    parser.add_argument("--port", type=int, default=8883, help="MQTT broker TLS port (default: 8883)")
    parser.add_argument("--username", help="MQTT username")
    parser.add_argument("--password", help="MQTT password")
    parser.add_argument("--command-topic", required=True, help="MQTT command topic")
    parser.add_argument("--response-topic", required=True, help="MQTT response topic")
    parser.add_argument("--endpoint", required=True, help="openHAB REST endpoint (e.g. /rest/items/Example/state)")
    parser.add_argument("--method", default="GET", choices=["GET", "POST", "PUT", "DELETE"], help="HTTP method")
    parser.add_argument("--data", help="Stringified payload to send")
    parser.add_argument("--timeout", type=int, default=10, help="Seconds to wait for response")
    parser.add_argument("--tls", action="store_true", default=True, help="Use TLS (default: enabled)")
    parser.add_argument("--ca-cert", help="CA certificate path for TLS validation")
    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args()
    response_queue: "queue.Queue[dict]" = queue.Queue()
    correlation_id = str(uuid.uuid4())

    client = mqtt.Client(client_id=f"controller-{correlation_id}", clean_session=True)

    if args.username:
        client.username_pw_set(args.username, args.password)

    if args.tls:
        client.tls_set(ca_certs=args.ca_cert)

    def on_message(_client, _userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except json.JSONDecodeError:
            logging.warning("Received non-JSON response: %s", message.payload)
            return
        if payload.get("correlation_id") == correlation_id:
            response_queue.put(payload)

    client.on_message = on_message
    client.connect(args.host, args.port, keepalive=60)
    client.subscribe(args.response_topic, qos=1)
    client.loop_start()

    command_payload = {
        "method": args.method,
        "endpoint": args.endpoint,
        "data": args.data,
        "correlation_id": correlation_id,
        "idempotency_key": f"{correlation_id}:{int(datetime.now(timezone.utc).timestamp())}",
    }
    logging.info("Publishing command: %s", json.dumps(command_payload))
    client.publish(args.command_topic, json.dumps(command_payload), qos=1, retain=False)

    try:
        response = response_queue.get(timeout=args.timeout)
        logging.info("Received response: %s", json.dumps(response, indent=2))
    except queue.Empty:
        logging.error("Timed out waiting for response with correlation_id %s", correlation_id)
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()


