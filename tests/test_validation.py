"""Persistence-independent request data validation tests."""

import unittest
from datetime import date

from domain.schemas import (
    ValidationError,
    get_schema,
    validate_data,
    validate_identifier,
)


class ValidationTests(unittest.TestCase):
    def test_create_validates_public_fields(self):
        values = validate_data(
            get_schema("driver"),
            {"name": "Alex", "nationality": "ES", "number": 7},
            create=True,
        )
        self.assertEqual(values, {"name": "Alex", "nationality": "ES", "number": 7})

    def test_create_requires_fields_and_rejects_generated_id(self):
        with self.assertRaises(ValidationError):
            validate_data(get_schema("driver"), {"name": "Alex"}, create=True)
        with self.assertRaises(ValidationError):
            validate_data(
                get_schema("driver"),
                {"id": 1, "name": "Alex", "nationality": "ES", "number": 7},
                create=True,
            )

    def test_update_rejects_unknown_and_key_fields(self):
        with self.assertRaises(ValidationError):
            validate_data(get_schema("driver"), {"unknown": 1}, create=False)
        with self.assertRaises(ValidationError):
            validate_data(get_schema("tyre_usage"), {"period": 2}, create=False)

    def test_validates_types_and_iso_date(self):
        with self.assertRaises(ValidationError):
            validate_data(get_schema("driver"), {"number": True}, create=False)
        with self.assertRaises(ValidationError):
            validate_data(
                get_schema("track"), {"length_km": float("nan")}, create=False
            )
        values = validate_data(get_schema("race"), {"date": "2026-10-28"}, create=False)
        self.assertEqual(values["date"], date(2026, 10, 28))

    def test_validates_composite_identifier(self):
        schema = get_schema("tyre_usage")
        self.assertEqual(
            validate_identifier(schema, {"result_id": 4, "period": 2}), (4, 2)
        )
        with self.assertRaises(ValidationError):
            validate_identifier(schema, {"result_id": 4})

    def test_rejects_unknown_entity(self):
        with self.assertRaises(ValidationError):
            get_schema("unknown")


if __name__ == "__main__":
    unittest.main()
