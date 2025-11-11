from __future__ import annotations

import functools
import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseSettings, Field, validator

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Runtime configuration for the edge agent."""

    site_id: str = Field(..., env="SITE_ID", description="Logical site identifier.")

    mqtt_host: str = Field(..., env="MQTT_HOST")
    mqtt_port: int = Field(8883, env="MQTT_PORT")
    mqtt_tls: bool = Field(True, env="MQTT_TLS")
    mqtt_username: Optional[str] = Field(None, env="MQTT_USERNAME")
    mqtt_password: Optional[str] = Field(None, env="MQTT_PASSWORD")
    mqtt_ca: Optional[Path] = Field(None, env="MQTT_CA")
    mqtt_cert: Optional[Path] = Field(None, env="MQTT_CERT")
    mqtt_key: Optional[Path] = Field(None, env="MQTT_KEY")
    mqtt_keepalive: int = Field(60, env="MQTT_KEEPALIVE")
    mqtt_clean_session: bool = Field(False, env="MQTT_CLEAN_SESSION")
    mqtt_command_topic: Optional[str] = Field(None, env="MQTT_COMMAND_TOPIC")
    mqtt_response_topic: Optional[str] = Field(None, env="MQTT_RESPONSE_TOPIC")
    mqtt_status_topic: Optional[str] = Field(None, env="MQTT_STATUS_TOPIC")
    mqtt_data_topic: Optional[str] = Field(None, env="MQTT_DATA_TOPIC")

    openhab_base_url: str = Field("http://localhost:8080", env="OH_BASE_URL")
    openhab_token: Optional[str] = Field(None, env="OH_TOKEN")
    openhab_timeout: int = Field(10, env="OH_TIMEOUT_SEC")

    telemetry_interval_sec: int = Field(60, env="TELEMETRY_INTERVAL_SEC")
    heartbeat_interval_sec: int = Field(30, env="HEARTBEAT_INTERVAL_SEC")

    cache_ttl_sec: int = Field(300, env="CACHE_TTL_SEC")
    cache_size: int = Field(1000, env="CACHE_SIZE")

    class Config:
        env_file = ".env"
        case_sensitive = False

    @validator("mqtt_command_topic", "mqtt_response_topic", "mqtt_status_topic", "mqtt_data_topic", pre=True)
    def strip_empty(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        return value or None

    @validator("mqtt_clean_session", pre=True)
    def parse_bool(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in {"1", "true", "yes", "on"}
        return bool(value)

    @property
    def topic_prefix(self) -> str:
        return f"wsn/{self.site_id}/openhab"

    def resolve_topics(self) -> dict[str, str]:
        """Return computed MQTT topics for command, response, status, and data."""
        command = self.mqtt_command_topic or f"{self.topic_prefix}/command"
        response = self.mqtt_response_topic or f"{self.topic_prefix}/response"
        status = self.mqtt_status_topic or f"{self.topic_prefix}/status"
        data = self.mqtt_data_topic or f"{self.topic_prefix}/data"
        return {
            "command": command,
            "response": response,
            "status": status,
            "data": data,
        }


@functools.lru_cache(maxsize=1)
def load_settings(env_file: Optional[Path] = None) -> Settings:
    """Load configuration, optionally specifying a non-default env file."""
    settings_kwargs = {}
    if env_file:
        if not env_file.exists():
            raise FileNotFoundError(f"Env file {env_file} does not exist")
        settings_kwargs["env_file"] = env_file
    settings = Settings(**settings_kwargs)
    logger.debug("Configuration loaded", extra={"config": settings.dict()})
    return settings


__all__ = ["Settings", "load_settings"]


