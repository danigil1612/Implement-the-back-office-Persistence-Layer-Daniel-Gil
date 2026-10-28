"""Business operations over the server-side repositories."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

from sqlalchemy.exc import IntegrityError

from domain.schemas import (
    ConflictError,
    NotFoundError,
    ValidationError,
    get_schema,
    validate_data,
    validate_identifier,
    validate_value,
)

from . import models
from .repositories import UnitOfWork


@dataclass(frozen=True)
class PersistenceMapping:
    model: type
    repository: str
    columns: dict[str, str]


PERSISTENCE = {
    "driver": PersistenceMapping(
        models.Conductor,
        "conductors",
        {
            "id": "id_driver",
            "name": "nom",
            "nationality": "nacionalitat",
            "number": "numero",
        },
    ),
    "car": PersistenceMapping(
        models.Cotxe,
        "cotxes",
        {
            "id": "id_cotxe",
            "chassis_code": "codi_xassis",
            "engine_supplier": "proveidor_de_motors",
            "power_hp": "potencia_cv",
            "weight_kg": "pes_kg",
            "driver_id": "id_driver",
        },
    ),
    "track": PersistenceMapping(
        models.Pista,
        "pistes",
        {
            "id": "id_track",
            "name": "nom",
            "country": "pais",
            "length_km": "longitud_km",
        },
    ),
    "race": PersistenceMapping(
        models.Cursa,
        "curses",
        {
            "id": "id_race",
            "grand_prix_name": "nom_del_gran_premi",
            "date": "data",
            "season": "temporada",
            "track_id": "id_track",
        },
    ),
    "tyre": PersistenceMapping(
        models.Pneumatic,
        "pneumatics",
        {
            "id": "id_tyre",
            "compound_name": "nom_compost",
            "description": "descripcio",
        },
    ),
    "race_result": PersistenceMapping(
        models.ResultatCursa,
        "resultats",
        {
            "id": "id_result",
            "final_position": "posicio_final",
            "points": "punts",
            "total_time": "temps_total",
            "driver_id": "id_driver",
            "race_id": "id_race",
        },
    ),
    "tyre_usage": PersistenceMapping(
        models.ResultatPneumatic,
        "tyre_usages",
        {
            "result_id": "id_result",
            "period": "periode",
            "tyre_id": "id_tyre",
            "lap_count": "nombre_de_voltes",
            "use_number": "numero_us",
        },
    ),
}


def to_dto(entity: str, record: Any) -> dict[str, Any]:
    result = {}
    for name, column in PERSISTENCE[entity].columns.items():
        value = getattr(record, column)
        result[name] = value.isoformat() if isinstance(value, date) else value
    updated = getattr(record, "last_update", None)
    result["last_update"] = updated.isoformat() if updated is not None else None
    return result


FILTER_METHODS = {
    "driver": {
        "number": "get_by_numero",
        "name": "get_by_nom",
        "nationality": "get_by_nacionalitat",
    },
    "car": {
        "chassis_code": "get_by_codi_xassis",
        "engine_supplier": "get_by_proveidor_de_motors",
    },
    "track": {"country": "get_by_pais", "name": "get_by_nom"},
    "race": {
        "season": "get_by_temporada",
        "grand_prix_name": "get_by_gran_premi",
    },
    "tyre": {"compound_name": "get_by_nom_compost"},
    "race_result": {
        "driver_id": "get_by_conductor",
        "race_id": "get_by_cursa",
        "podium_race_id": "get_podi",
    },
}


class EntityService:
    """CRUD and existing repository queries for all Formula 1 entities."""

    def __init__(self, unit_of_work_factory: Callable = UnitOfWork) -> None:
        self.unit_of_work_factory = unit_of_work_factory

    def create(self, entity: str, data: dict[str, Any]) -> dict[str, Any]:
        schema = get_schema(entity)
        mapping = PERSISTENCE[entity]
        values = {
            mapping.columns[name]: value
            for name, value in validate_data(schema, data, create=True).items()
        }
        try:
            with self.unit_of_work_factory() as work:
                record = getattr(work, mapping.repository).add(mapping.model(**values))
                work.commit()
                return to_dto(entity, record)
        except IntegrityError as exc:
            raise ConflictError("A unique or foreign-key constraint failed") from exc

    def read(self, entity: str, identifier: Any) -> dict[str, Any]:
        schema = get_schema(entity)
        key = validate_identifier(schema, identifier)
        with self.unit_of_work_factory() as work:
            record = getattr(work, PERSISTENCE[entity].repository).get(key)
            if record is None:
                raise NotFoundError("Record not found")
            return to_dto(entity, record)

    def update(
        self, entity: str, identifier: Any, data: dict[str, Any]
    ) -> dict[str, Any]:
        schema = get_schema(entity)
        key = validate_identifier(schema, identifier)
        mapping = PERSISTENCE[entity]
        values = {
            mapping.columns[name]: value
            for name, value in validate_data(schema, data, create=False).items()
        }
        try:
            with self.unit_of_work_factory() as work:
                repository = getattr(work, mapping.repository)
                record = repository.get(key)
                if record is None:
                    raise NotFoundError("Record not found")
                for column, value in values.items():
                    setattr(record, column, value)
                record = repository.update(record)
                work.commit()
                return to_dto(entity, record)
        except IntegrityError as exc:
            raise ConflictError("A unique or foreign-key constraint failed") from exc

    def delete(self, entity: str, identifier: Any) -> dict[str, Any]:
        schema = get_schema(entity)
        key = validate_identifier(schema, identifier)
        try:
            with self.unit_of_work_factory() as work:
                repository = getattr(work, PERSISTENCE[entity].repository)
                record = repository.get(key)
                if record is None:
                    raise NotFoundError("Record not found")
                repository.delete(record)
                work.commit()
            return {"deleted": True}
        except IntegrityError as exc:
            raise ConflictError("A database constraint prevents deletion") from exc

    def list(
        self,
        entity: str,
        filter_by: dict[str, Any] | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> list[dict[str, Any]]:
        schema = get_schema(entity)
        if filter_by is not None and (page is not None or page_size is not None):
            raise ValidationError("Filters and pagination cannot be combined")
        if page is not None or page_size is not None:
            if (
                entity != "race_result"
                or type(page) is not int
                or type(page_size) is not int
            ):
                raise ValidationError(
                    "Pagination requires race_result, page and page_size"
                )
            if page < 1 or page_size < 1:
                raise ValidationError("page and page_size must be positive")
        with self.unit_of_work_factory() as work:
            repository = getattr(work, PERSISTENCE[entity].repository)
            if filter_by is not None:
                if not isinstance(filter_by, dict) or set(filter_by) != {
                    "field",
                    "value",
                }:
                    raise ValidationError("filter must contain field and value")
                field = filter_by["field"]
                method = FILTER_METHODS.get(entity, {}).get(field)
                if method is None:
                    raise ValidationError("Unsupported filter for this entity")
                source_field = "race_id" if field == "podium_race_id" else field
                value = validate_value(
                    source_field, filter_by["value"], schema.fields[source_field]
                )
                records = getattr(repository, method)(value)
            elif page is not None:
                records = repository.get_paginated(page, page_size)
            else:
                records = repository.get_all()
            if records is None:
                records = []
            elif not isinstance(records, (list, tuple)):
                records = [records]
            return [to_dto(entity, record) for record in records]
