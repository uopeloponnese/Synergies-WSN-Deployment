from __future__ import annotations

import json
from importlib import resources
from typing import Any, Dict

from jsonschema import Draft202012Validator

__all__ = [
    "validate_command",
    "validate_response",
]


def _load_schema(name: str) -> Dict[str, Any]:
    with resources.open_text(__package__, name) as handle:
        return json.load(handle)


_COMMAND_SCHEMA = _load_schema("command.schema.json")
_RESPONSE_SCHEMA = _load_schema("response.schema.json")

_COMMAND_VALIDATOR = Draft202012Validator(_COMMAND_SCHEMA)
_RESPONSE_VALIDATOR = Draft202012Validator(_RESPONSE_SCHEMA)


def validate_command(instance: Dict[str, Any]) -> None:
    _COMMAND_VALIDATOR.validate(instance)


def validate_response(instance: Dict[str, Any]) -> None:
    _RESPONSE_VALIDATOR.validate(instance)


