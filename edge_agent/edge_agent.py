from __future__ import annotations

import json
import logging
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from config import Settings, load_settings
from idempotency_cache import IdempotencyCache
from mqtt_client import MQTTClient
from openhab_proxy import OpenHABProxy
from schemas import validate_command

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)


class EdgeAgent:
    """Coordinates MQTT handling and openHAB proxy interactions."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._topics = settings.resolve_topics()
        self._idempotency_cache: Optional[IdempotencyCache[Dict[str, Any]]] = None

        if settings.cache_size > 0 and settings.cache_ttl_sec > 0:
            self._idempotency_cache = IdempotencyCache(
                ttl_seconds=settings.cache_ttl_sec,
                max_size=settings.cache_size,
            )
        self._proxy = OpenHABProxy(
            base_url=settings.openhab_base_url,
            token=settings.openhab_token,
            timeout=settings.openhab_timeout,
        )
        self._mqtt = MQTTClient(
            client_id=f"{settings.site_id}",
            host=settings.mqtt_host,
            port=settings.mqtt_port,
            keepalive=settings.mqtt_keepalive,
            clean_session=settings.mqtt_clean_session,
            topics=self._topics,
            on_command=self._handle_command,
            tls=settings.mqtt_tls,
            ca_path=str(settings.mqtt_ca) if settings.mqtt_ca else None,
            cert_path=str(settings.mqtt_cert) if settings.mqtt_cert else None,
            key_path=str(settings.mqtt_key) if settings.mqtt_key else None,
            username=settings.mqtt_username,
            password=settings.mqtt_password,
        )
        self._telemetry_thread = threading.Thread(target=self._telemetry_loop, daemon=True)
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._shutdown = threading.Event()

    # Command handling ---------------------------------------------------------
    def _handle_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        validate_command(command)
        correlation_id = command["correlation_id"]
        idempotency_key = command.get("idempotency_key")

        if self._idempotency_cache and idempotency_key:
            cached = self._idempotency_cache.get(idempotency_key)
            if cached:
                cached_response = dict(cached)
                cached_response["from_cache"] = True
                return cached_response

        method = command["method"]
        endpoint = command["endpoint"]
        data = command.get("data")
        headers = command.get("headers")

        start = time.perf_counter()
        response = self._proxy.request(method=method, endpoint=endpoint, data=data, headers=headers)
        elapsed = time.perf_counter() - start

        response_payload: Dict[str, Any] = {
            "correlation_id": correlation_id,
            "status_code": response.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latency_ms": round(elapsed * 1000, 2),
        }

        try:
            content_type = response.headers.get("Content-Type", "")
            if "application/json" in content_type:
                response_payload["data"] = response.json()
            else:
                response_payload["data"] = response.text
        except json.JSONDecodeError:
            response_payload["data"] = response.text

        if response.status_code >= 400:
            response_payload["error"] = response_payload.get("data")

        if self._idempotency_cache and idempotency_key and response.ok:
            self._idempotency_cache.set(idempotency_key, dict(response_payload))

        return response_payload

    # Background loops ---------------------------------------------------------
    def _telemetry_loop(self) -> None:  # pragma: no cover - network dependent
        interval = max(5, self._settings.telemetry_interval_sec)
        logger.info("Telemetry loop active", extra={"interval_sec": interval})
        while not self._shutdown.is_set():
            try:
                telemetry_payload = {
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "status": "sampled",
                }
                self._mqtt.publish_data(telemetry_payload)
            except Exception as exc:
                logger.exception("Telemetry publish failed", exc_info=exc)
            self._shutdown.wait(interval)

    def _heartbeat_loop(self) -> None:  # pragma: no cover - network dependent
        interval = max(5, self._settings.heartbeat_interval_sec)
        logger.info("Heartbeat loop active", extra={"interval_sec": interval})
        while not self._shutdown.is_set():
            try:
                self._mqtt.publish_status("online", retain=False)
            except Exception as exc:
                logger.exception("Heartbeat publish failed", exc_info=exc)
            self._shutdown.wait(interval)

    # Lifecycle ----------------------------------------------------------------
    def start(self) -> None:
        self._mqtt.connect()
        self._telemetry_thread.start()
        self._heartbeat_thread.start()

    def stop(self) -> None:
        logger.info("Shutting down edge agent")
        self._shutdown.set()
        self._mqtt.publish_status("offline", retain=True)
        self._mqtt.disconnect()
        self._proxy.close()


def _install_signal_handlers(agent: EdgeAgent) -> None:
    def _handle_signal(signum, frame):  # pragma: no cover - signal handling
        logger.info("Received signal, stopping agent", extra={"signum": signum})
        agent.stop()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)


def main() -> None:
    configure_logging()
    settings = load_settings()
    agent = EdgeAgent(settings)
    _install_signal_handlers(agent)
    agent.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:  # pragma: no cover - handled via signals
        agent.stop()


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    main()


