#!/usr/bin/env python3
"""
Interactive script to communicate with OpenHAB through the edge-agent via MQTT.

This script allows you to:
- List all OpenHAB items
- Get item state/value
- Set item state/value
- Query any OpenHAB REST API endpoint
- Monitor MQTT topics

Usage examples:

    # List all items
    python utils/openhab_mqtt_client.py list

    # Get item state
    python utils/openhab_mqtt_client.py get MyItemName

    # Set item state (for switches, dimmers, etc.)
    python utils/openhab_mqtt_client.py set MySwitch ON
    python utils/openhab_mqtt_client.py set MyDimmer 50

    # Get item metadata
    python utils/openhab_mqtt_client.py get MyItemName --endpoint /rest/items/MyItemName

    # Custom REST API call
    python utils/openhab_mqtt_client.py call GET /rest/items

    # Monitor MQTT topics (status, data, responses)
    python utils/openhab_mqtt_client.py monitor
"""

from __future__ import annotations

import argparse
import json
import logging
import queue
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

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


def resolve_site_id(override: Optional[str] = None) -> str:
    """Resolve SITE_ID from command line, ID file, or config.env."""
    if override:
        return override
    if ID_FILE.exists():
        text = ID_FILE.read_text(encoding="utf-8").strip()
        if text:
            return text
    cfg = parse_config_env(CONFIG_ENV)
    site_id = cfg.get("SITE_ID", "").strip()
    if site_id:
        return site_id
    raise SystemExit("SITE_ID not found. Use --site-id or ensure ID file/config.env is set.")


def resolve_mqtt_config() -> Tuple[str, int, bool, Optional[str], Optional[str]]:
    """Resolve MQTT configuration from config.env."""
    cfg = parse_config_env(CONFIG_ENV)
    host = cfg.get("MQTT_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port_str = cfg.get("MQTT_PORT", "1883").strip() or "1883"
    try:
        port = int(port_str)
    except ValueError:
        raise SystemExit(f"Invalid MQTT_PORT in config.env: {port_str!r}")
    
    tls_str = cfg.get("MQTT_TLS", "false").strip().lower()
    tls = tls_str in ("true", "1", "yes", "on")
    username = cfg.get("MQTT_USERNAME", "").strip() or None
    password = cfg.get("MQTT_PASSWORD", "").strip() or None
    
    return host, port, tls, username, password


class OpenHABMQTTClient:
    """Client for interacting with OpenHAB through edge-agent via MQTT."""

    def __init__(self, site_id: str, mqtt_host: str, mqtt_port: int, mqtt_tls: bool = False,
                 mqtt_username: Optional[str] = None, mqtt_password: Optional[str] = None):
        self.site_id = site_id
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_tls = mqtt_tls
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password
        
        self.command_topic = f"wsn/{site_id}/openhab/command"
        self.response_topic = f"wsn/{site_id}/openhab/response"
        self.status_topic = f"wsn/{site_id}/openhab/status"
        self.data_topic = f"wsn/{site_id}/openhab/data"
        
        self.response_queue: queue.Queue[dict] = queue.Queue()
        self.client: Optional[mqtt.Client] = None

    def _on_message(self, _client: mqtt.Client, _userdata, message: mqtt.MQTTMessage):
        """Handle incoming MQTT messages."""
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            self.response_queue.put({
                "topic": message.topic,
                "payload": payload,
            })
        except json.JSONDecodeError:
            print(f"⚠️  Received non-JSON on {message.topic}: {message.payload.decode('utf-8', errors='replace')}")

    def _connect(self, subscribe_topics: list[str]) -> None:
        """Connect to MQTT broker and subscribe to topics."""
        client_id = f"openhab-client-{uuid.uuid4().hex[:8]}"
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1,
            client_id=client_id,
            clean_session=True,
        )
        
        if self.mqtt_username:
            self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
        
        if self.mqtt_tls:
            self.client.tls_set()
            self.client.tls_insecure_set(False)
        
        self.client.on_message = self._on_message
        self.client.connect(self.mqtt_host, self.mqtt_port, keepalive=60)
        self.client.loop_start()
        
        # Wait a bit for connection
        time.sleep(0.5)
        
        # Subscribe to topics
        for topic in subscribe_topics:
            self.client.subscribe(topic, qos=1)
            time.sleep(0.1)

    def _disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()

    def send_command(self, method: str, endpoint: str, data: Optional[Any] = None,
                    headers: Optional[Dict[str, str]] = None, timeout: int = 10) -> Dict[str, Any]:
        """Send a command to OpenHAB via edge-agent and wait for response."""
        correlation_id = str(uuid.uuid4())
        
        self._connect([self.response_topic])
        
        command_payload = {
            "method": method,
            "endpoint": endpoint,
            "data": data,
            "headers": headers,
            "correlation_id": correlation_id,
            "idempotency_key": f"{correlation_id}",
        }
        
        print(f"📤 Sending command: {method} {endpoint}")
        if data:
            print(f"   Data: {json.dumps(data)}")
        
        self.client.publish(self.command_topic, json.dumps(command_payload), qos=1, retain=False)
        
        # Wait for response
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                msg = self.response_queue.get(timeout=1)
                if msg["topic"] == self.response_topic:
                    response = msg["payload"]
                    if response.get("correlation_id") == correlation_id:
                        self._disconnect()
                        return response
                    else:
                        # Wrong correlation ID, put it back (shouldn't happen with proper filtering)
                        self.response_queue.put(msg)
            except queue.Empty:
                continue
        
        self._disconnect()
        raise TimeoutError(f"No response received within {timeout} seconds")

    def list_items(self) -> list[Dict[str, Any]]:
        """Get list of all OpenHAB items."""
        response = self.send_command("GET", "/rest/items")
        if response.get("status_code") == 200:
            return response.get("data", [])
        else:
            raise RuntimeError(f"Failed to get items: {response}")

    def get_item_state(self, item_name: str) -> str:
        """Get the state of a specific OpenHAB item."""
        response = self.send_command("GET", f"/rest/items/{item_name}/state")
        if response.get("status_code") == 200:
            return response.get("data", "")
        else:
            error = response.get("error", "Unknown error")
            raise RuntimeError(f"Failed to get item state: {error}")

    def set_item_state(self, item_name: str, state: str) -> None:
        """Set the state of a specific OpenHAB item."""
        response = self.send_command("POST", f"/rest/items/{item_name}", data=state)
        if response.get("status_code") not in (200, 201, 204):
            error = response.get("error", "Unknown error")
            raise RuntimeError(f"Failed to set item state: {error}")

    def get_item(self, item_name: str) -> Dict[str, Any]:
        """Get full metadata of a specific OpenHAB item."""
        response = self.send_command("GET", f"/rest/items/{item_name}")
        if response.get("status_code") == 200:
            return response.get("data", {})
        else:
            error = response.get("error", "Unknown error")
            raise RuntimeError(f"Failed to get item: {error}")

    def monitor(self, duration: Optional[int] = None) -> None:
        """Monitor MQTT topics for status, data, and responses."""
        print(f"👀 Monitoring MQTT topics (Ctrl+C to stop)...")
        print(f"   Status: {self.status_topic}")
        print(f"   Data: {self.data_topic}")
        print(f"   Response: {self.response_topic}")
        print()
        
        self._connect([self.status_topic, self.data_topic, self.response_topic])
        
        start_time = time.time()
        try:
            while True:
                if duration and (time.time() - start_time) > duration:
                    break
                
                try:
                    msg = self.response_queue.get(timeout=1)
                    topic = msg["topic"]
                    payload = msg["payload"]
                    
                    if topic == self.status_topic:
                        status = payload.get("status", "unknown")
                        ts = payload.get("ts", "")
                        print(f"💚 Status: {status} @ {ts}")
                    elif topic == self.data_topic:
                        print(f"📊 Data: {json.dumps(payload, indent=2)}")
                    elif topic == self.response_topic:
                        print(f"📥 Response: {json.dumps(payload, indent=2)}")
                except queue.Empty:
                    continue
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped")
        finally:
            self._disconnect()


def format_items(items: list[Dict[str, Any]]) -> None:
    """Pretty print a list of OpenHAB items."""
    if not items:
        print("No items found.")
        return
    
    print(f"\n📋 Found {len(items)} items:\n")
    for item in items:
        name = item.get("name", "?")
        item_type = item.get("type", "?")
        state = item.get("state", "?")
        label = item.get("label", "")
        print(f"  • {name:30} [{item_type:15}] State: {state:15} {label}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interact with OpenHAB through edge-agent via MQTT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--site-id",
        help="Site ID (overrides ID file and config.env)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout for MQTT responses in seconds (default: 10)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all OpenHAB items")
    
    # Get command
    get_parser = subparsers.add_parser("get", help="Get item state or metadata")
    get_parser.add_argument("item", help="Item name")
    get_parser.add_argument(
        "--endpoint",
        help="Custom endpoint (default: /rest/items/{item}/state)",
    )
    get_parser.add_argument(
        "--full",
        action="store_true",
        help="Get full item metadata instead of just state",
    )
    
    # Set command
    set_parser = subparsers.add_parser("set", help="Set item state")
    set_parser.add_argument("item", help="Item name")
    set_parser.add_argument("value", help="Value to set (e.g., ON, OFF, 50, etc.)")
    
    # Call command
    call_parser = subparsers.add_parser("call", help="Make custom REST API call")
    call_parser.add_argument("method", choices=["GET", "POST", "PUT", "DELETE"], help="HTTP method")
    call_parser.add_argument("endpoint", help="REST API endpoint (e.g., /rest/items)")
    call_parser.add_argument(
        "--data",
        help="JSON data for POST/PUT requests",
    )
    
    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Monitor MQTT topics")
    monitor_parser.add_argument(
        "--duration",
        type=int,
        help="Duration in seconds (default: infinite)",
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Configure logging
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")
    
    # Resolve configuration
    site_id = resolve_site_id(args.site_id)
    mqtt_host, mqtt_port, mqtt_tls, mqtt_username, mqtt_password = resolve_mqtt_config()
    
    print(f"🔗 Connecting to MQTT broker: {mqtt_host}:{mqtt_port}")
    print(f"📍 Site ID: {site_id}\n")
    
    client = OpenHABMQTTClient(
        site_id=site_id,
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        mqtt_tls=mqtt_tls,
        mqtt_username=mqtt_username,
        mqtt_password=mqtt_password,
    )
    
    try:
        if args.command == "list":
            items = client.list_items()
            format_items(items)
            
        elif args.command == "get":
            if args.full:
                item_data = client.get_item(args.item)
                print(f"\n📦 Item: {args.item}\n")
                print(json.dumps(item_data, indent=2))
            elif args.endpoint:
                response = client.send_command("GET", args.endpoint, timeout=args.timeout)
                print(f"\n✅ Response:\n")
                print(json.dumps(response, indent=2))
            else:
                state = client.get_item_state(args.item)
                print(f"\n✅ {args.item} = {state}\n")
                
        elif args.command == "set":
            client.set_item_state(args.item, args.value)
            print(f"\n✅ Set {args.item} = {args.value}\n")
            # Get updated state
            try:
                state = client.get_item_state(args.item)
                print(f"   Current state: {state}\n")
            except Exception as e:
                print(f"   ⚠️  Could not verify state: {e}\n")
                
        elif args.command == "call":
            data = None
            if args.data:
                try:
                    data = json.loads(args.data)
                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON data: {args.data}")
                    sys.exit(1)
            
            response = client.send_command(args.method, args.endpoint, data=data, timeout=args.timeout)
            print(f"\n✅ Response:\n")
            print(json.dumps(response, indent=2))
            
        elif args.command == "monitor":
            client.monitor(duration=args.duration)
            
    except TimeoutError as e:
        print(f"\n❌ {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

