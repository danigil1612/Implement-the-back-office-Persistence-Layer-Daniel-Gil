"""Validate request envelopes and dispatch them to the service layer."""

from __future__ import annotations

import logging
from typing import Any

from domain.schemas import ConflictError, NotFoundError, ValidationError, get_schema
from protocol import failure, success


REQUEST_KEYS = {
    "create": {"operation", "entity", "data"},
    "read": {"operation", "entity", "id"},
    "update": {"operation", "entity", "id", "data"},
    "delete": {"operation", "entity", "id"},
    "list": {"operation", "entity"},
}
LIST_OPTIONS = {"filter", "page", "page_size"}


def validate_request(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ValidationError("Request must be a JSON object")
    operation = request.get("operation")
    if not isinstance(operation, str) or operation not in REQUEST_KEYS:
        raise ValidationError("Unsupported operation")
    get_schema(request.get("entity"))
    required = REQUEST_KEYS[operation]
    allowed = required | (LIST_OPTIONS if operation == "list" else set())
    if not required.issubset(request) or set(request) - allowed:
        raise ValidationError("Missing or unexpected request fields")
    return request


class Router:
    def __init__(self, service: Any) -> None:
        self.service = service

    def handle(self, request: Any) -> dict[str, Any]:
        try:
            request = validate_request(request)
            operation = request["operation"]
            entity = request["entity"]
            if operation == "create":
                data = self.service.create(entity, request["data"])
            elif operation == "read":
                data = self.service.read(entity, request["id"])
            elif operation == "update":
                data = self.service.update(entity, request["id"], request["data"])
            elif operation == "delete":
                data = self.service.delete(entity, request["id"])
            else:
                data = self.service.list(
                    entity,
                    request.get("filter"),
                    request.get("page"),
                    request.get("page_size"),
                )
            return success(data)
        except ValidationError as exc:
            return failure("invalid_request", str(exc))
        except NotFoundError as exc:
            return failure("not_found", str(exc))
        except ConflictError as exc:
            return failure("conflict", str(exc))
        except Exception:
            logging.exception("Unhandled request failure")
            return failure("server_error", "Internal server error")
