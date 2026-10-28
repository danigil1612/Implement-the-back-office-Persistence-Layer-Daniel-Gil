"""Protocol serialization and framing tests."""

import unittest

from protocol import ProtocolError, decode_message, encode_message


class ProtocolTests(unittest.TestCase):
    def test_utf8_round_trip(self):
        message = {"operation": "create", "data": {"name": "Àlex"}}
        self.assertEqual(decode_message(encode_message(message)), message)

    def test_rejects_invalid_json(self):
        with self.assertRaises(ProtocolError) as error:
            decode_message(b"{bad}\n")
        self.assertEqual(error.exception.code, "invalid_json")

    def test_rejects_non_object_message(self):
        with self.assertRaises(ProtocolError) as error:
            decode_message(b"[]\n")
        self.assertEqual(error.exception.code, "invalid_message")

    def test_rejects_missing_newline(self):
        with self.assertRaises(ProtocolError) as error:
            decode_message(b"{}")
        self.assertEqual(error.exception.code, "invalid_frame")

    def test_rejects_non_serializable_value(self):
        with self.assertRaises(ProtocolError):
            encode_message({"value": object()})


if __name__ == "__main__":
    unittest.main()
