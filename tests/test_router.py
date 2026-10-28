"""Router dispatch, envelope validation, and error mapping tests."""

import unittest
from unittest.mock import Mock

from domain.schemas import ConflictError, NotFoundError
from server_app.router import Router


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.service = Mock()
        self.router = Router(self.service)

    def test_routes_all_crud_operations(self):
        requests = [
            (
                {"operation": "create", "entity": "driver", "data": {"name": "Alex"}},
                "create",
            ),
            ({"operation": "read", "entity": "driver", "id": 1}, "read"),
            (
                {
                    "operation": "update",
                    "entity": "driver",
                    "id": 1,
                    "data": {"name": "Alex"},
                },
                "update",
            ),
            ({"operation": "delete", "entity": "driver", "id": 1}, "delete"),
            ({"operation": "list", "entity": "driver"}, "list"),
        ]
        for request, method in requests:
            with self.subTest(method=method):
                self.assertTrue(self.router.handle(request)["ok"])
                self.assertTrue(getattr(self.service, method).called)

    def test_rejects_invalid_envelope(self):
        for request in (
            {"operation": "execute", "entity": "driver"},
            {"operation": "read", "entity": "driver"},
            {"operation": "list", "entity": "driver", "unexpected": 1},
            {"operation": "list", "entity": "missing"},
        ):
            with self.subTest(request=request):
                response = self.router.handle(request)
                self.assertEqual(response["error"]["code"], "invalid_request")

    def test_maps_service_errors(self):
        request = {"operation": "read", "entity": "driver", "id": 1}
        self.service.read.side_effect = NotFoundError("Record not found")
        self.assertEqual(self.router.handle(request)["error"]["code"], "not_found")
        self.service.read.side_effect = ConflictError("Conflict")
        self.assertEqual(self.router.handle(request)["error"]["code"], "conflict")


if __name__ == "__main__":
    unittest.main()
