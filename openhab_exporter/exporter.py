#!/usr/bin/env python3
"""
openHAB Exporter

Periodically collects the latest state for all items grouped by thing/channel
and forwards the payload to a remote HTTP endpoint.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests
from requests import Response, Session


LOGGER = logging.getLogger("openhab-exporter")


class GracefulExit(SystemExit):
    """Raised when a termination signal is received."""


def _setup_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )


def _current_ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_site_id(site_id_env: Optional[str], site_id_file: Optional[str]) -> Optional[str]:
    if site_id_env:
        return site_id_env.strip() or None

    if site_id_file:
        path = Path(site_id_file)
        if path.exists():
            try:
                return path.read_text(encoding="utf-8").strip() or None
            except OSError as exc:
                LOGGER.error("Failed to read site_id file %s: %s", path, exc)
    return None


def _default_site_id_path() -> str:
    return "/data/site/ID"


def _merge_dict(base: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    merged.update(extra)
    return merged


class OpenHABClient:
    def __init__(
        self,
        base_url: str,
        session: Session,
        timeout: float,
        persistence_service: Optional[str],
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session
        self.timeout = timeout
        self.persistence_service = persistence_service

    def _request(self, method: str, path: str, **kwargs: Any) -> Response:
        url = f"{self.base_url}{path}"
        headers = kwargs.pop("headers", {})
        headers.setdefault("Accept", "application/json")
        return self.session.request(method, url, headers=headers, timeout=self.timeout, **kwargs)

    def fetch_things(self) -> List[Dict[str, Any]]:
        resp = self._request("GET", "/rest/things")
        resp.raise_for_status()
        return resp.json()

    def fetch_item(self, name: str) -> Dict[str, Any]:
        resp = self._request("GET", f"/rest/items/{name}")
        resp.raise_for_status()
        return resp.json()

    def fetch_persistence_snapshot(self, name: str) -> Optional[Dict[str, Any]]:
        if not self.persistence_service:
            return None

        params = {
            "pageSize": 1,
        }
        if self.persistence_service:
            params["serviceId"] = self.persistence_service

        resp = self._request("GET", f"/rest/persistence/items/{name}", params=params)
        if resp.status_code == 200:
            body = resp.json()
            data_points: Iterable[Dict[str, Any]] = body.get("data", [])
            # The API returns a list with the earliest entry first; the last entry is the latest snapshot.
            last_point = None
            for entry in data_points:
                last_point = entry
            if last_point:
                return {
                    "time": last_point.get("time"),
                    "state": last_point.get("state"),
                }
            # Some persistence services provide last value fields
            if "lastUpdate" in body and "lastValue" in body:
                return {
                    "time": body.get("lastUpdate"),
                    "state": body.get("lastValue"),
                }
        return None


class Exporter:
    def __init__(
        self,
        site_id: Optional[str],
        client: OpenHABClient,
        remote_url: str,
        interval: float,
        timeout: float,
        api_key: Optional[str],
        max_retries: int,
    ) -> None:
        self.site_id = site_id
        self.client = client
        self.remote_url = remote_url
        self.interval = interval
        self.timeout = timeout
        self.api_key = api_key
        self.max_retries = max_retries
        self.session = requests.Session()

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def build_payload(self) -> Dict[str, Any]:
        things = self.client.fetch_things()
        item_cache: Dict[str, Dict[str, Any]] = {}
        hierarchy: List[Dict[str, Any]] = []

        for thing in things:
            channels_output: List[Dict[str, Any]] = []
            for channel in thing.get("channels", []):
                linked_items = []
                for item_name in channel.get("linkedItems", []):
                    item_payload = item_cache.get(item_name)
                    if not item_payload:
                        item_payload = self._format_item(item_name)
                        item_cache[item_name] = item_payload
                    linked_items.append(dict(item_payload))

                channels_output.append(
                    {
                        "uid": channel.get("uid"),
                        "id": channel.get("id"),
                        "label": channel.get("label"),
                        "item_type": channel.get("itemType"),
                        "kind": channel.get("kind"),
                        "linked_items": linked_items,
                    }
                )

            hierarchy.append(
                {
                    "uid": thing.get("UID"),
                    "thing_type_uid": thing.get("thingTypeUID"),
                    "label": thing.get("label"),
                    "location": thing.get("location"),
                    "bridge_uid": thing.get("bridgeUID"),
                    "status": thing.get("statusInfo", {}).get("status"),
                    "status_detail": thing.get("statusInfo", {}).get("statusDetail"),
                    "channels": channels_output,
                }
            )

        payload = {
            "site_id": self.site_id,
            "generated_at": _current_ts(),
            "things": hierarchy,
        }
        return payload

    def _format_item(self, item_name: str) -> Dict[str, Any]:
        try:
            item = self.client.fetch_item(item_name)
        except requests.HTTPError as exc:
            LOGGER.error("Failed to fetch item %s: %s", item_name, exc)
            raise

        item_payload: Dict[str, Any] = {
            "name": item.get("name"),
            "label": item.get("label"),
            "category": item.get("category"),
            "state": item.get("state"),
            "type": item.get("type"),
            "group_names": item.get("groupNames", []),
            "tags": item.get("tags", []),
        }

        state_description = item.get("stateDescription")
        if isinstance(state_description, dict):
            item_payload["state_description"] = {
                "pattern": state_description.get("pattern"),
                "read_only": state_description.get("readOnly"),
                "options": state_description.get("options"),
                "minimum": state_description.get("minimum"),
                "maximum": state_description.get("maximum"),
                "step": state_description.get("step"),
            }

        persistence_snapshot = None
        try:
            persistence_snapshot = self.client.fetch_persistence_snapshot(item_name)
        except requests.HTTPError as exc:
            LOGGER.warning("Failed to fetch persistence data for %s: %s", item_name, exc)

        if persistence_snapshot:
            item_payload["persistence"] = persistence_snapshot

        return item_payload

    def send_payload(self, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = self._build_headers()

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.post(
                    self.remote_url,
                    headers=headers,
                    data=data,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                LOGGER.info(
                    "Exporter delivered payload (%d things, response %s)",
                    len(payload.get("things", [])),
                    response.status_code,
                )
                return
            except requests.RequestException as exc:
                LOGGER.error(
                    "Attempt %d/%d failed posting exporter payload: %s",
                    attempt,
                    self.max_retries,
                    exc,
                )
                sleep_time = min(2 ** attempt, 60)
                time.sleep(sleep_time)
        LOGGER.error("Exporter unable to deliver payload after %d attempts", self.max_retries)

    def run_forever(self, run_once: bool = False) -> None:
        while True:
            payload = self.build_payload()
            self.send_payload(payload)

            if run_once:
                return

            LOGGER.debug("Sleeping for %s seconds", self.interval)
            time.sleep(self.interval)


def build_session(username: Optional[str], password: Optional[str], verify_tls: bool) -> Session:
    session = requests.Session()
    if username:
        session.auth = (username, password or "")
    session.verify = verify_tls
    return session


def _handle_signals():
    def _raise_graceful_exit(signum, _frame):
        raise GracefulExit(f"Received signal {signum}")

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _raise_graceful_exit)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="openHAB measurements exporter")
    parser.add_argument("--once", action="store_true", help="Run a single collection/post cycle and exit")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase logging verbosity")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    _setup_logging(args.verbose)
    _handle_signals()

    openhab_url = os.getenv("OPENHAB_BASE_URL", "http://oh:8080")
    remote_url = os.getenv("EXPORTER_TARGET_URL")
    if not remote_url:
        LOGGER.error("EXPORTER_TARGET_URL environment variable is required")
        return 1

    site_id = _load_site_id(
        os.getenv("SITE_ID"),
        os.getenv("SITE_ID_FILE", _default_site_id_path()),
    )
    if not site_id:
        LOGGER.warning("No site_id resolved; payloads will include null site_id")

    interval = float(os.getenv("EXPORTER_INTERVAL_SECONDS", "300"))
    timeout = float(os.getenv("EXPORTER_HTTP_TIMEOUT_SECONDS", "15"))
    api_key = os.getenv("EXPORTER_API_KEY") or None
    max_retries = int(os.getenv("EXPORTER_MAX_RETRIES", "3"))
    openhab_timeout = float(os.getenv("OPENHAB_HTTP_TIMEOUT_SECONDS", "10"))
    persistence_service = os.getenv("OPENHAB_PERSISTENCE_SERVICE", "influxdb") or None
    verify_tls_env = os.getenv("OPENHAB_TLS_VERIFY", "true").lower()
    verify_tls = verify_tls_env not in ("0", "false", "no")

    username = os.getenv("OPENHAB_USERNAME")
    password = os.getenv("OPENHAB_PASSWORD")

    session = build_session(username, password, verify_tls)
    client = OpenHABClient(openhab_url, session, openhab_timeout, persistence_service)
    exporter = Exporter(site_id, client, remote_url, interval, timeout, api_key, max_retries)

    try:
        exporter.run_forever(run_once=args.once)
    except GracefulExit as exc:
        LOGGER.info("Exporter exiting gracefully: %s", exc)
    except requests.RequestException as exc:
        LOGGER.error("Exporter encountered an HTTP error: %s", exc)
        return 2
    except Exception:  # noqa: BLE001
        LOGGER.exception("Unexpected exporter failure")
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())

