#!/usr/bin/env python3
"""
Quick MQTT test script for the edge agent / openHAB integration.

Usage examples (from the repo root):

    # Fetch a specific item's state
    python utils/test_mqtt_openhab.py --item YourItemName

    # Fetch the full /rest/items list
    python utils/test_mqtt_openhab.py --list-items

The script will:
  - Read SITE_ID from the ID file (or SITE_ID in config.env as a fallback)
  - Read MQTT_HOST / MQTT_PORT from config.env
  - Publish a GET command for /rest/items/<item>/state
  - Wait for the edge agent's response and print it
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import queue
import uuid
from pathlib import Path
from typing import Dict, Optional, Tuple

import paho.mqtt.client as mqtt


REPO_ROOT = Path(__file__).resolve().parents[1]
ID_FILE = REPO_ROOT / "ID"
CONFIG_ENV = REPO_ROOT / "config.env"


def parse_config_env(path: Path) -> Dict[str, str]:
    """Very small parser for key=value lines in config.env."""
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        values[key] = value
    return values


def resolve_site_id() -> str:
    if ID_FILE.exists():
        text = ID_FILE.read_text(encoding="utf-8").strip()
        if text:
            return text
    cfg = parse_config_env(CONFIG_ENV)
    site_id = cfg.get("SITE_ID", "").strip()
    if site_id:
        return site_id
    raise SystemExit("SITE_ID not found in ID file or config.env. Please set it before running this test.")


def resolve_mqtt_config() -> Tuple[str, int]:
    cfg = parse_config_env(CONFIG_ENV)
    host = cfg.get("MQTT_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port_str = cfg.get("MQTT_PORT", "1883").strip() or "1883"
    try:
        port = int(port_str)
    except ValueError:
        raise SystemExit(f"Invalid MQTT_PORT in config.env: {port_str!r}")
    return host, port


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Test edge-agent MQTT command to openHAB.")
    parser.add_argument(
        "--item",
        help="openHAB item name to query (e.g. MySwitch). Mutually exclusive with --list-items.",
    )
    parser.add_argument(
        "--list-items",
        action="store_true",
        help="Fetch the full /rest/items list from openHAB via the edge agent.",
    )
    parser.add_argument(
        "--method",
        default="GET",
        choices=["GET", "POST", "PUT", "DELETE"],
        help="HTTP method for the openHAB REST call (default: GET).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Seconds to wait for MQTT response (default: 10).",
    )
    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = build_parser().parse_args()

    if not args.list_items and not args.item:
        raise SystemExit("You must provide either --item <name> or --list-items.")

    site_id = resolve_site_id()
    mqtt_host, mqtt_port = resolve_mqtt_config()
    command_topic = f"wsn/{site_id}/openhab/command"
    response_topic = f"wsn/{site_id}/openhab/response"

    logging.info("SITE_ID=%s", site_id)
    logging.info("MQTT broker: %s:%s", mqtt_host, mqtt_port)
    logging.info("Command topic: %s", command_topic)
    logging.info("Response topic: %s", response_topic)

    response_queue: "queue.Queue[dict]" = queue.Queue()
    correlation_id = str(uuid.uuid4())

    client = mqtt.Client(client_id=f"mqtt-test-{correlation_id}", clean_session=True)

    def on_message(_client, _userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except json.JSONDecodeError:
            logging.warning("Received non-JSON response: %s", message.payload)
            return
        if payload.get("correlation_id") == correlation_id:
            response_queue.put(payload)

    client.on_message = on_message
    client.connect(mqtt_host, mqtt_port, keepalive=60)
    client.subscribe(response_topic, qos=1)
    client.loop_start()

    if args.list_items:
        endpoint = "/rest/items"
    else:
        endpoint = f"/rest/items/{args.item}/state"
    command_payload = {
        "method": args.method,
        "endpoint": endpoint,
        "data": None,
        "correlation_id": correlation_id,
        "idempotency_key": f"{correlation_id}",
    }

    logging.info("Publishing command: %s", json.dumps(command_payload))
    client.publish(command_topic, json.dumps(command_payload), qos=1, retain=False)

    try:
        response = response_queue.get(timeout=args.timeout)
        logging.info("Received response:\n%s", json.dumps(response, indent=2))
    except queue.Empty:
        logging.error("Timed out waiting for response with correlation_id %s", correlation_id)
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()


