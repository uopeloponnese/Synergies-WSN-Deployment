from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


CommandHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


def _iso_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class MQTTClient:
    """Encapsulates MQTT connectivity and request/response handling."""

    def __init__(
        self,
        client_id: str,
        host: str,
        port: int,
        keepalive: int,
        clean_session: bool,
        topics: Dict[str, str],
        on_command: CommandHandler,
        tls: bool = True,
        ca_path: Optional[str] = None,
        cert_path: Optional[str] = None,
        key_path: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self._topics = topics
        self._on_command = on_command
        self._client = mqtt.Client(client_id=client_id, clean_session=clean_session)
        self._client.enable_logger(logger)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect
        self._client.on_subscribe = self._on_subscribe
        # Bridge Paho's internal logs into our logger for easier debugging.
        self._client.on_log = self._on_log
        if username:
            self._client.username_pw_set(username=username, password=password)
        self._host = host
        self._port = port
        self._keepalive = keepalive

        self._client.will_set(
            topic=topics["status"],
            payload=json.dumps({"status": "offline", "ts": _iso_timestamp()}),
            qos=1,
            retain=True,
        )

        if tls:
            self._client.tls_set(ca_certs=ca_path, certfile=cert_path, keyfile=key_path)
            self._client.tls_insecure_set(False)

        self._loop_running = threading.Event()

    # Callbacks -----------------------------------------------------------------
    def _on_log(self, client: mqtt.Client, userdata, level, buf):
        """Bridge Paho's internal logging into our logger."""
        try:
            # Include buf in the log message itself so we can see what Paho is doing.
            if level >= mqtt.MQTT_LOG_INFO:
                logger.info("MQTT client log: %s", buf)
            else:
                logger.debug("MQTT client log: %s", buf)
        except Exception:
            # Never let logging issues interfere with MQTT processing.
            logger.debug("Failed to log MQTT client message", exc_info=True)

    # def _on_connect(self, client: mqtt.Client, userdata, flags, rc):
    #     if rc != 0:
    #         logger.error("MQTT connection failed", extra={"rc": rc})
    #         return
    #     logger.info(
    #         "MQTT connected",
    #         extra={
    #             "host": self._host,
    #             "port": self._port,
    #             "command_topic": self._topics.get("command"),
    #             "response_topic": self._topics.get("response"),
    #             "status_topic": self._topics.get("status"),
    #             "data_topic": self._topics.get("data"),
    #         },
    #     )
    #     # Subscribe to the command topic and log the broker's acknowledgement.
    #     result, mid = client.subscribe(self._topics["command"], qos=1)
    #     logger.info(
    #         "Subscribe requested for command topic",
    #         extra={"topic": self._topics.get("command"), "result": result, "mid": mid},
    #     )
    #     status_payload = json.dumps({"status": "online", "ts": _iso_timestamp()})
    #     self.publish(self._topics["status"], status_payload, qos=1, retain=True)
    #     result, mid = client.subscribe("#", qos=0)
    #     logger.info("Subscribe requested for #", extra={"result": result, "mid": mid})

    def _on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            logger.error("MQTT connection failed", extra={"rc": rc})
            return

        logger.info("MQTT connected", extra={...})

        # DEBUG: subscribe to everything
        result, mid = client.subscribe("#", qos=0)
        logger.info(
            "Subscribe requested for #",
            extra={"result": result, "mid": mid},
        )

        status_payload = json.dumps({"status": "online", "ts": _iso_timestamp()})
        self.publish(self._topics["status"], status_payload, qos=1, retain=True)


    def _on_disconnect(self, client: mqtt.Client, userdata, rc):
        if rc != 0:
            logger.warning("Unexpected MQTT disconnection", extra={"rc": rc})
        else:
            logger.info("MQTT disconnected cleanly")

    # def _on_subscribe(self, client: mqtt.Client, userdata, mid, granted_qos):
    #     logger.info(
    #         "SUBACK received",
    #         extra={"mid": mid, "granted_qos": granted_qos},
    #     )
    #     if granted_qos and granted_qos[0] == 128:
    #         logger.error(
    #             "Broker rejected subscription to command topic",
    #             extra={"mid": mid},
    #         )

    def _on_subscribe(self, client: mqtt.Client, userdata, mid, granted_qos):
        logger.info(
            "SUBACK received",
            extra={"mid": mid, "granted_qos": granted_qos},
        )
        if granted_qos and granted_qos[0] == 128:
            logger.error(
                "Broker rejected subscription to command topic",
                extra={"mid": mid},
            )


    def _on_message(self, client: mqtt.Client, userdata, message: mqtt.MQTTMessage):
        # Log that the callback fired before doing any parsing so we can
        # distinguish missing callbacks from JSON/handler errors.
        raw_payload = message.payload.decode("utf-8", errors="replace")
        logger.info(
            "MQTT on_message callback invoked",
            extra={"topic": message.topic, "payload": raw_payload},
        )

        command: Optional[Dict[str, Any]] = None
        try:
            command = json.loads(raw_payload)
            response = self._on_command(command)
            self.publish(self._topics["response"], json.dumps(response), qos=1, retain=False)
        except Exception as exc:  # pragma: no cover - defensive path
            logger.exception("Error handling MQTT command", exc_info=exc)
            error_response = {
                "correlation_id": command.get("correlation_id") if isinstance(command, dict) else None,
                "status_code": 500,
                "error": "Edge agent encountered an unexpected error",
                "timestamp": _iso_timestamp(),
            }
            self.publish(self._topics["response"], json.dumps(error_response), qos=1, retain=False)

    # Public API -----------------------------------------------------------------
    def connect(self) -> None:
        logger.info("Connecting to MQTT broker", extra={"host": self._host, "port": self._port})
        self._client.connect(self._host, self._port, self._keepalive)
        self._client.loop_start()
        self._loop_running.set()

    def disconnect(self) -> None:
        if not self._loop_running.is_set():
            return
        logger.info("Disconnecting MQTT client")
        self._client.loop_stop()
        self._client.disconnect()
        self._loop_running.clear()

    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False) -> None:
        logger.debug("Publishing MQTT message", extra={"topic": topic, "qos": qos, "retain": retain})
        result = self._client.publish(topic, payload=payload, qos=qos, retain=retain)
        result.wait_for_publish()
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error("MQTT publish failed", extra={"topic": topic, "rc": result.rc})

    def publish_status(self, status: str, retain: bool = False) -> None:
        payload = json.dumps({"status": status, "ts": _iso_timestamp()})
        self.publish(self._topics["status"], payload, qos=1, retain=retain)

    def publish_data(self, data: Dict[str, Any]) -> None:
        payload = json.dumps(data)
        self.publish(self._topics["data"], payload, qos=0, retain=False)


