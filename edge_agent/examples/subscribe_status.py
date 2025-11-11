#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging

import paho.mqtt.client as mqtt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Subscribe to edge agent status updates.")
    parser.add_argument("--host", required=True, help="MQTT broker host")
    parser.add_argument("--port", type=int, default=8883, help="MQTT broker TLS port (default: 8883)")
    parser.add_argument("--username", help="MQTT username")
    parser.add_argument("--password", help="MQTT password")
    parser.add_argument("--status-topic", required=True, help="MQTT status topic")
    parser.add_argument("--tls", action="store_true", default=True, help="Use TLS (default: enabled)")
    parser.add_argument("--ca-cert", help="CA certificate path for TLS validation")
    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args()

    client = mqtt.Client(client_id="status-monitor", clean_session=True)

    if args.username:
        client.username_pw_set(args.username, args.password)

    if args.tls:
        client.tls_set(ca_certs=args.ca_cert)

    def on_message(_client, _userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except json.JSONDecodeError:
            logging.warning("Non-JSON status payload: %s", message.payload)
            return
        logging.info("Status update (%s): %s", message.topic, json.dumps(payload))

    client.on_message = on_message
    client.connect(args.host, args.port, keepalive=60)
    client.subscribe(args.status_topic, qos=1)
    client.loop_forever()


if __name__ == "__main__":
    main()


