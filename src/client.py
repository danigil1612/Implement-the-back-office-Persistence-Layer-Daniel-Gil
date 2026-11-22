"""Command-line asyncio client with no persistence imports."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from domain.schemas import ENTITY_SCHEMAS
from protocol import (
    MAX_MESSAGE_BYTES,
    ProtocolError,
    close_stream,
    decode_message,
    encode_message,
    read_frame,
)


def _json_value(text: str) -> Any:
    if text == "-":
        text = sys.stdin.read()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError("Expected valid JSON") from exc


def _filter_value(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def build_request(arguments: argparse.Namespace) -> dict[str, Any]:
    request: dict[str, Any] = {
        "operation": arguments.operation,
        "entity": arguments.entity,
    }
    if arguments.operation in {"read", "update", "delete"}:
        request["id"] = arguments.id
    if arguments.operation in {"create", "update"}:
        request["data"] = arguments.data
    if arguments.operation == "list":
        if arguments.filter_field is not None:
            request["filter"] = {
                "field": arguments.filter_field,
                "value": arguments.filter_value,
            }
        if arguments.page is not None:
            request["page"] = arguments.page
        if arguments.page_size is not None:
            request["page_size"] = arguments.page_size
    return request


async def send_request(
    host: str, port: int, request: dict[str, Any]
) -> dict[str, Any]:
    frame = encode_message(request)
    reader, writer = await asyncio.open_connection(
        host, port, limit=MAX_MESSAGE_BYTES
    )
    try:
        writer.write(frame)
        await writer.drain()
        line = await read_frame(reader)
    finally:
        await close_stream(writer)
    if not line:
        raise ProtocolError("invalid_frame", "Server closed without a response")
    return decode_message(line)


def main() -> int:
    parser = argparse.ArgumentParser(description="Formula 1 back-office client")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5050)
    commands = parser.add_subparsers(dest="operation", required=True)
    for operation in ("create", "read", "update", "delete", "list"):
        command = commands.add_parser(operation)
        command.add_argument("entity", choices=sorted(ENTITY_SCHEMAS))
        if operation in {"read", "update", "delete"}:
            command.add_argument(
                "id", type=_json_value, help="JSON id, or '-' to read from stdin"
            )
        if operation in {"create", "update"}:
            command.add_argument(
                "data", type=_json_value, help="JSON object, or '-' to read from stdin"
            )
        if operation == "list":
            command.add_argument("--filter-field")
            command.add_argument("--filter-value", type=_filter_value)
            command.add_argument("--page", type=int)
            command.add_argument("--page-size", type=int)
    arguments = parser.parse_args()
    if arguments.operation == "list" and (
        (arguments.filter_field is None) != (arguments.filter_value is None)
    ):
        parser.error("--filter-field and --filter-value must be used together")
    try:
        response = asyncio.run(
            send_request(arguments.host, arguments.port, build_request(arguments))
        )
    except (OSError, ProtocolError) as exc:
        print(f"Connection error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0 if response.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
