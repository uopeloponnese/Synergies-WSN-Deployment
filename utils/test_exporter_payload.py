#!/usr/bin/env python3
"""
Manual test utility for the openHAB exporter.

Fetches the latest openHAB hierarchy payload and optionally posts it to the
configured remote endpoint.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Optional

from openhab_exporter.exporter import (
    Exporter,
    OpenHABClient,
    _load_site_id,
    build_session,
)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test the openHAB exporter payload generation.")
    parser.add_argument(
        "--openhab-url",
        default=os.getenv("OPENHAB_BASE_URL", "http://oh:8080"),
        help="Base URL for the openHAB REST API.",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("OPENHAB_USERNAME"),
        help="Optional basic-auth username for openHAB.",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("OPENHAB_PASSWORD"),
        help="Optional basic-auth password for openHAB.",
    )
    parser.add_argument(
        "--verify-tls",
        default=os.getenv("OPENHAB_TLS_VERIFY", "true"),
        help="Whether to verify TLS certificates when connecting to openHAB.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.getenv("OPENHAB_HTTP_TIMEOUT_SECONDS", "10")),
        help="HTTP timeout for openHAB requests.",
    )
    parser.add_argument(
        "--persistence-service",
        default=os.getenv("OPENHAB_PERSISTENCE_SERVICE", "influxdb"),
        help="Persistence service ID to query for last values (set empty to skip).",
    )
    parser.add_argument(
        "--site-id",
        default=os.getenv("SITE_ID"),
        help="Explicit site_id value (overrides file lookup).",
    )
    parser.add_argument(
        "--site-id-file",
        default=os.getenv("SITE_ID_FILE"),
        help="Path to the site_id file (default: /data/site/ID).",
    )
    parser.add_argument(
        "--target-url",
        default=os.getenv("EXPORTER_TARGET_URL"),
        help="Optional remote endpoint to POST the payload.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("EXPORTER_API_KEY"),
        help="API key for the remote endpoint (sent as X-API-Key).",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send the payload to the remote endpoint instead of only printing it.",
    )
    parser.add_argument(
        "--verbose",
        action="count",
        default=0,
        help="Increase logging verbosity.",
    )
    return parser.parse_args(argv)


def configure_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(level=level, format="%(asctime)s | %(levelname)s | %(message)s")


def to_bool(value: str) -> bool:
    return value.lower() not in {"0", "false", "no"}


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)

    verify_tls = to_bool(str(args.verify_tls))
    session = build_session(args.username, args.password, verify_tls)
    client = OpenHABClient(
        base_url=args.openhab_url,
        session=session,
        timeout=args.timeout,
        persistence_service=(args.persistence_service or None),
    )

    site_id = _load_site_id(args.site_id, args.site_id_file)
    exporter = Exporter(
        site_id=site_id,
        client=client,
        remote_url=args.target_url or "http://localhost",
        interval=0,
        timeout=float(os.getenv("EXPORTER_HTTP_TIMEOUT_SECONDS", "15")),
        api_key=args.api_key,
        max_retries=int(os.getenv("EXPORTER_MAX_RETRIES", "3")),
    )

    payload = exporter.build_payload()
    print(json.dumps(payload, indent=2))

    if args.send:
        if not args.target_url:
            logging.error("--send requires --target-url to be provided")
            return 1
        logging.info("Sending payload to %s", args.target_url)
        exporter.send_payload(payload)

    return 0


if __name__ == "__main__":
    sys.exit(main())

