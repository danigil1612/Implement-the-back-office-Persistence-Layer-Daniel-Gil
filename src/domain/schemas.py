"""Public entity fields and validation, independent of SQLAlchemy."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Any


class ValidationError(ValueError):
    """A request contains an invalid entity, identifier, or field value."""


class NotFoundError(LookupError):
    """The requested record does not exist."""


class ConflictError(ValueError):
    """A database constraint rejected the change."""


@dataclass(frozen=True)
class FieldSpec:
    kind: str
    required: bool = True
    nullable: bool = False
    max_length: int | None = None


@dataclass(frozen=True)
class EntitySchema:
    identifiers: tuple[str, ...]
    generated_id: bool
    fields: dict[str, FieldSpec]


def _field(
    kind: str,
    required: bool = True,
    nullable: bool = False,
    max_length: int | None = None,
) -> FieldSpec:
    return FieldSpec(kind, required, nullable, max_length)


ENTITY_SCHEMAS = {
    "driver": EntitySchema(
        ("id",),
        True,
        {
            "id": _field("int"),
            "name": _field("str", max_length=100),
            "nationality": _field("str", max_length=60),
            "number": _field("int"),
        },
    ),
    "car": EntitySchema(
        ("id",),
        True,
        {
            "id": _field("int"),
            "chassis_code": _field("str", max_length=50),
            "engine_supplier": _field("str", max_length=80),
            "power_hp": _field("int"),
            "weight_kg": _field("float"),
            "driver_id": _field("int"),
        },
    ),
    "track": EntitySchema(
        ("id",),
        True,
        {
            "id": _field("int"),
            "name": _field("str", max_length=100),
            "country": _field("str", max_length=80),
            "length_km": _field("float"),
        },
    ),
    "race": EntitySchema(
        ("id",),
        True,
        {
            "id": _field("int"),
            "grand_prix_name": _field("str", max_length=120),
            "date": _field("date"),
            "season": _field("int"),
            "track_id": _field("int"),
        },
    ),
    "tyre": EntitySchema(
        ("id",),
        True,
        {
            "id": _field("int"),
            "compound_name": _field("str", max_length=50),
            "description": _field("str", False, True),
        },
    ),
    "race_result": EntitySchema(
        ("id",),
        True,
        {
            "id": _field("int"),
            "final_position": _field("int"),
            "points": _field("float", False),
            "total_time": _field("str", False, True, 40),
            "driver_id": _field("int"),
            "race_id": _field("int"),
        },
    ),
    "tyre_usage": EntitySchema(
        ("result_id", "period"),
        False,
        {
            "result_id": _field("int"),
            "period": _field("int"),
            "tyre_id": _field("int"),
            "lap_count": _field("int"),
            "use_number": _field("int"),
        },
    ),
}


def get_schema(entity: Any) -> EntitySchema:
    if not isinstance(entity, str) or entity not in ENTITY_SCHEMAS:
        raise ValidationError("Unknown entity")
    return ENTITY_SCHEMAS[entity]


def validate_value(name: str, value: Any, spec: FieldSpec) -> Any:
    if value is None:
        if spec.nullable:
            return None
        raise ValidationError(f"{name} cannot be null")
    if spec.kind == "int":
        if type(value) is not int or value < 0:
            raise ValidationError(f"{name} must be a non-negative integer")
    elif spec.kind == "float":
        if type(value) not in (int, float) or not isfinite(value):
            raise ValidationError(f"{name} must be a finite number")
        value = float(value)
    elif spec.kind == "str":
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"{name} must be a non-empty string")
        if spec.max_length is not None and len(value) > spec.max_length:
            raise ValidationError(f"{name} exceeds {spec.max_length} characters")
    elif spec.kind == "date":
        if not isinstance(value, str):
            raise ValidationError(f"{name} must be an ISO date")
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise ValidationError(f"{name} must be an ISO date") from exc
        if parsed.isoformat() != value:
            raise ValidationError(f"{name} must use YYYY-MM-DD")
        value = parsed
    return value


def validate_data(schema: EntitySchema, data: Any, *, create: bool) -> dict[str, Any]:
    if not isinstance(data, dict) or not data:
        raise ValidationError("data must be a non-empty object")
    forbidden = set(schema.identifiers) if not create or schema.generated_id else set()
    if set(data) - set(schema.fields) or forbidden.intersection(data):
        raise ValidationError("data contains unknown or read-only fields")
    if create:
        required = {
            name
            for name, spec in schema.fields.items()
            if spec.required
            and (name not in schema.identifiers or not schema.generated_id)
        }
        missing = required - set(data)
        if missing:
            raise ValidationError(
                f"Missing required fields: {', '.join(sorted(missing))}"
            )
    return {
        name: validate_value(name, value, schema.fields[name])
        for name, value in data.items()
    }


def validate_identifier(schema: EntitySchema, value: Any) -> int | tuple[int, ...]:
    if len(schema.identifiers) == 1:
        if type(value) is not int or value < 1:
            raise ValidationError("id must be a positive integer")
        return value
    if not isinstance(value, dict) or set(value) != set(schema.identifiers):
        raise ValidationError("id must contain the composite key fields")
    result = tuple(value[name] for name in schema.identifiers)
    if any(type(item) is not int or item < 1 for item in result):
        raise ValidationError("composite id fields must be positive integers")
    return result
