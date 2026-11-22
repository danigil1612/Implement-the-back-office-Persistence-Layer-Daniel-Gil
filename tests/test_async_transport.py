"""Loopback tests for authenticated, concurrent connections."""

import asyncio
import os
import shutil
import ssl
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock

from client import send_request
from protocol import (
    MAX_MESSAGE_BYTES,
    ProtocolError,
    close_stream,
    decode_message,
    encode_message,
    success,
)
from server_app.server import running_server
from tls_config import create_context
from tools.generate_certificates import generate_certificates


HOST = "127.0.0.1"
REQUEST = {"operation": "list", "entity": "driver"}
RESPONSE = success([])
TIMEOUT = 5


class SecureTransportTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        openssl = os.getenv("BACKOFFICE_OPENSSL") or shutil.which("openssl")
        if not openssl:
            raise unittest.SkipTest("Install OpenSSL 3 to run the TLS tests")
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.keys = Path(temporary.name) / "trusted"
        cls.untrusted_keys = Path(temporary.name) / "untrusted"
        for directory in (cls.keys, cls.untrusted_keys):
            generate_certificates(directory, openssl)
        cls.server_tls = cls.tls(cls.keys, "server", server_side=True)
        cls.client_one = cls.tls(cls.keys, "client-one")
        cls.client_two = cls.tls(cls.keys, "client-two")

    @staticmethod
    def tls(directory, name, *, server_side=False):
        return create_context(
            directory / "ca.pem",
            directory / f"{name}.pem",
            directory / f"{name}.key",
            server_side=server_side,
        )

    async def open_connection(self, listener):
        reader, writer = await asyncio.open_connection(
            HOST, listener.sockets[0].getsockname()[1], ssl=self.client_one
        )
        self.addAsyncCleanup(close_stream, writer)
        return reader, writer

    async def test_other_client_can_proceed_during_database_wait(self):
        loop = asyncio.get_running_loop()
        entered = asyncio.Event()
        release = threading.Event()

        def handle(request):
            if request["entity"] == "track":
                loop.call_soon_threadsafe(entered.set)
                if not release.wait(TIMEOUT * 2):
                    raise AssertionError("Slow operation was not released")
            return RESPONSE

        router = Mock(handle=handle)
        async with running_server(HOST, 0, router, self.server_tls) as listener:
            reader, writer = await self.open_connection(listener)
            session = writer.get_extra_info("ssl_object")
            self.assertEqual(session.version(), "TLSv1.3")
            self.assertEqual(session.cipher()[1], "TLSv1.3")
            port = listener.sockets[0].getsockname()[1]
            writer.write(encode_message({**REQUEST, "entity": "track"}))
            await writer.drain()
            try:
                await asyncio.wait_for(entered.wait(), TIMEOUT)
                response = await asyncio.wait_for(
                    send_request(HOST, port, REQUEST, self.client_two), TIMEOUT
                )
                self.assertEqual(response, RESPONSE)
            finally:
                release.set()
            line = await asyncio.wait_for(reader.readline(), TIMEOUT)
            self.assertEqual(decode_message(line), RESPONSE)

    async def test_bad_json_recovers_and_oversized_frame_closes_client(self):
        router = Mock()
        router.handle.return_value = RESPONSE
        async with running_server(HOST, 0, router, self.server_tls) as listener:
            reader, writer = await self.open_connection(listener)
            writer.write(b"not JSON\n" + encode_message(REQUEST))
            await writer.drain()
            line = await asyncio.wait_for(reader.readline(), TIMEOUT)
            malformed = decode_message(line)
            self.assertEqual(malformed["error"]["code"], "invalid_json")
            line = await asyncio.wait_for(reader.readline(), TIMEOUT)
            self.assertEqual(decode_message(line), RESPONSE)

            writer.write(b"x" * (MAX_MESSAGE_BYTES + 1) + b"\n")
            await writer.drain()
            line = await asyncio.wait_for(reader.readline(), TIMEOUT)
            self.assertEqual(
                decode_message(line)["error"]["code"], "message_too_large"
            )
            eof = await asyncio.wait_for(reader.read(), TIMEOUT)
            self.assertEqual(eof, b"")
            self.assertEqual(
                await asyncio.wait_for(
                    send_request(
                        HOST, listener.sockets[0].getsockname()[1], REQUEST,
                        self.client_one,
                    ),
                    TIMEOUT,
                ),
                RESPONSE,
            )
        self.assertEqual(router.handle.call_count, 2)

    async def test_shutdown_closes_idle_client(self):
        router = Mock()
        async with running_server(HOST, 0, router, self.server_tls) as listener:
            reader, _ = await self.open_connection(listener)
        self.assertEqual(await asyncio.wait_for(reader.read(), TIMEOUT), b"")
        router.handle.assert_not_called()

    async def test_rejects_missing_and_untrusted_client_certificates(self):
        ca = self.keys / "ca.pem"
        no_certificate = ssl.create_default_context(cafile=str(ca))
        untrusted = create_context(
            ca,
            self.untrusted_keys / "client-one.pem",
            self.untrusted_keys / "client-one.key",
            server_side=False,
        )
        router = Mock()
        router.handle.return_value = RESPONSE
        async with running_server(HOST, 0, router, self.server_tls) as listener:
            port = listener.sockets[0].getsockname()[1]
            for candidate in (no_certificate, untrusted):
                with self.assertRaises(
                    (ssl.SSLError, ConnectionError, ProtocolError)
                ):
                    await asyncio.wait_for(
                        send_request(HOST, port, REQUEST, candidate), TIMEOUT
                    )
            router.handle.assert_not_called()
            reply = await send_request(HOST, port, REQUEST, self.client_one)
            self.assertEqual(reply, RESPONSE)
        router.handle.assert_called_once_with(REQUEST)

    async def test_client_rejects_wrong_server_identity(self):
        router = Mock()
        async with running_server(HOST, 0, router, self.server_tls) as listener:
            port = listener.sockets[0].getsockname()[1]
            with self.assertRaises(ssl.SSLCertVerificationError):
                await asyncio.wait_for(
                    asyncio.open_connection(
                        HOST, port, ssl=self.client_one,
                        server_hostname="other.example",
                    ),
                    TIMEOUT,
                )
        router.handle.assert_not_called()
