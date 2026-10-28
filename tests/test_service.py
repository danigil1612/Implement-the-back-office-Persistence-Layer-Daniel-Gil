"""Service logic tests with repositories and transactions replaced by mocks."""

import unittest
from unittest.mock import Mock

from sqlalchemy.exc import IntegrityError

from domain.schemas import ENTITY_SCHEMAS, ConflictError, NotFoundError, ValidationError
from server_app.models import Conductor, ResultatCursa
from server_app.service import PERSISTENCE, EntityService


class FakeWork:
    def __init__(self):
        self.conductors = Mock()
        self.resultats = Mock()
        self.tyre_usages = Mock()
        self.commit = Mock()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception, traceback):
        return False


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.work = FakeWork()
        self.service = EntityService(lambda: self.work)
        self.driver = Conductor(id_driver=5, nom="Alex", nacionalitat="ES", numero=7)

    def test_create_commits_and_returns_dto(self):
        self.work.conductors.add.side_effect = lambda record: record
        result = self.service.create(
            "driver", {"name": "Alex", "nationality": "ES", "number": 7}
        )
        self.assertEqual(result["name"], "Alex")
        self.assertEqual(result["nationality"], "ES")
        self.work.commit.assert_called_once()

    def test_every_public_field_has_a_server_mapping(self):
        self.assertEqual(set(PERSISTENCE), set(ENTITY_SCHEMAS))
        for entity, schema in ENTITY_SCHEMAS.items():
            self.assertEqual(set(PERSISTENCE[entity].columns), set(schema.fields))

    def test_read_and_missing_record(self):
        self.work.conductors.get.return_value = self.driver
        self.assertEqual(self.service.read("driver", 5)["id"], 5)
        self.work.conductors.get.assert_called_with(5)
        self.work.conductors.get.return_value = None
        with self.assertRaises(NotFoundError):
            self.service.read("driver", 5)

    def test_update_and_delete_commit(self):
        self.work.conductors.get.return_value = self.driver
        self.work.conductors.update.side_effect = lambda record: record
        updated = self.service.update("driver", 5, {"name": "Alex Gil"})
        self.assertEqual(updated["name"], "Alex Gil")
        deleted = self.service.delete("driver", 5)
        self.assertEqual(deleted, {"deleted": True})
        self.work.conductors.delete.assert_called_once_with(self.driver)
        self.assertEqual(self.work.commit.call_count, 2)

    def test_list_filter_and_pagination(self):
        self.work.conductors.get_by_nom.return_value = [self.driver]
        result = self.service.list("driver", {"field": "name", "value": "Alex"})
        self.assertEqual(result[0]["id"], 5)
        self.work.conductors.get_by_nom.assert_called_once_with("Alex")
        race_result = ResultatCursa(
            id_result=3, posicio_final=1, punts=25.0, id_driver=5, id_race=2
        )
        self.work.resultats.get_paginated.return_value = [race_result]
        page = self.service.list("race_result", page=1, page_size=10)
        self.assertEqual(page[0]["final_position"], 1)
        self.work.resultats.get_paginated.assert_called_once_with(1, 10)

    def test_rejects_bad_list_options(self):
        with self.assertRaises(ValidationError):
            self.service.list("driver", page=1, page_size=10)
        with self.assertRaises(ValidationError):
            self.service.list("driver", {"field": "unknown", "value": 1})

    def test_constraint_failure_is_a_conflict(self):
        self.work.conductors.add.side_effect = IntegrityError(
            "insert", {}, Exception("duplicate")
        )
        with self.assertRaises(ConflictError):
            self.service.create(
                "driver", {"name": "Alex", "nationality": "ES", "number": 7}
            )


if __name__ == "__main__":
    unittest.main()
