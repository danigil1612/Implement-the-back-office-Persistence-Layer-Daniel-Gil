"""UTF-8 newline-delimited JSON framing shared by client and server."""

from __future__ import annotations

import json
from typing import Any

MAX_MESSAGE_BYTES = 1_048_576


class ProtocolError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def encode_message(message: dict[str, Any]) -> bytes:
    if not isinstance(message, dict):
        raise ProtocolError("invalid_message", "Message must be a JSON object")
    try:
        payload = json.dumps(message, ensure_ascii=False, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError) as exc:
        raise ProtocolError("invalid_message", "Message is not valid JSON") from exc
    if len(payload) > MAX_MESSAGE_BYTES:
        raise ProtocolError("message_too_large", "Message exceeds the size limit")
    return payload + b"\n"


def decode_message(line: bytes) -> dict[str, Any]:
    if len(line) > MAX_MESSAGE_BYTES + 1:
        raise ProtocolError("message_too_large", "Message exceeds the size limit")
    if not line.endswith(b"\n"):
        raise ProtocolError("invalid_frame", "Message must end with a newline")
    try:
        message = json.loads(line.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("invalid_json", "Message is not valid UTF-8 JSON") from exc
    if not isinstance(message, dict):
        raise ProtocolError("invalid_message", "Message must be a JSON object")
    return message


def success(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data}


def failure(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}
