from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

import requests
from requests import Response

logger = logging.getLogger(__name__)


class OpenHABProxy:
    """HTTP client for interacting with the local openHAB instance."""

    def __init__(self, base_url: str, token: Optional[str] = None, timeout: int = 10):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()
        if token:
            self._session.headers["Authorization"] = f"Bearer {token}"
        self._session.headers["Content-Type"] = "application/json"
        self._session.headers["Accept"] = "application/json"

    def close(self) -> None:
        self._session.close()

    def request(self, method: str, endpoint: str, data: Any = None, headers: Optional[Dict[str, str]] = None) -> Response:
        url = f"{self._base_url}{endpoint}"
        request_headers = (headers or {}).copy()
        # If data provided as object, convert to JSON string
        payload = data
        if isinstance(data, (dict, list)):
            payload = json.dumps(data)
            request_headers.setdefault("Content-Type", "application/json")

        logger.debug(
            "Dispatching request to openHAB",
            extra={"method": method, "url": url, "headers": list(request_headers.keys())},
        )

        start = time.perf_counter()
        response = self._session.request(
            method=method.upper(),
            url=url,
            data=payload,
            headers=request_headers,
            timeout=self._timeout,
        )
        elapsed = time.perf_counter() - start
        logger.info(
            "openHAB responded",
            extra={"status_code": response.status_code, "url": url, "elapsed_ms": round(elapsed * 1000, 2)},
        )
        return response


__all__ = ["OpenHABProxy"]


