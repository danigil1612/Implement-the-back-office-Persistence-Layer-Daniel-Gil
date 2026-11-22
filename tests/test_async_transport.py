"""Loopback tests for concurrent requests and stream cleanup."""

import asyncio
import threading
import unittest
from unittest.mock import Mock

from client import send_request
from protocol import (
    MAX_MESSAGE_BYTES,
    close_stream,
    decode_message,
    encode_message,
    success,
)
from server_app.server import running_server


HOST = "127.0.0.1"
REQUEST = {"operation": "list", "entity": "driver"}
RESPONSE = success([])
TIMEOUT = 5


class AsyncTransportTests(unittest.IsolatedAsyncioTestCase):
    async def open_connection(self, listener):
        reader, writer = await asyncio.open_connection(
            HOST, listener.sockets[0].getsockname()[1]
        )
        self.addAsyncCleanup(close_stream, writer)
        return reader, writer

    async def test_other_client_is_served_while_router_waits_for_database(self):
        loop = asyncio.get_running_loop()
        entered = asyncio.Event()
        release = threading.Event()

        def handle(request):
            if request["entity"] == "track":
                loop.call_soon_threadsafe(entered.set)
                if not release.wait(TIMEOUT * 2):
                    raise AssertionError("Slow operation was not released")
            return RESPONSE

        async with running_server(HOST, 0, Mock(handle=handle)) as listener:
            reader, writer = await self.open_connection(listener)
            port = listener.sockets[0].getsockname()[1]
            writer.write(encode_message({**REQUEST, "entity": "track"}))
            await writer.drain()
            try:
                await asyncio.wait_for(entered.wait(), TIMEOUT)
                response = await asyncio.wait_for(
                    send_request(HOST, port, REQUEST), TIMEOUT
                )
                self.assertEqual(response, RESPONSE)
            finally:
                release.set()
            line = await asyncio.wait_for(reader.readline(), TIMEOUT)
            self.assertEqual(decode_message(line), RESPONSE)

    async def test_bad_json_recovers_and_oversized_frame_closes_client(self):
        router = Mock()
        router.handle.return_value = RESPONSE
        async with running_server(HOST, 0, router) as listener:
            reader, writer = await self.open_connection(listener)
            writer.write(b"not JSON\n" + encode_message(REQUEST))
            await writer.drain()
            line = await asyncio.wait_for(reader.readline(), TIMEOUT)
            self.assertEqual(decode_message(line)["error"]["code"], "invalid_json")
            line = await asyncio.wait_for(reader.readline(), TIMEOUT)
            self.assertEqual(decode_message(line), RESPONSE)

            writer.write(b"x" * (MAX_MESSAGE_BYTES + 1) + b"\n")
            await writer.drain()
            line = await asyncio.wait_for(reader.readline(), TIMEOUT)
            self.assertEqual(
                decode_message(line)["error"]["code"], "message_too_large"
            )
            self.assertEqual(await asyncio.wait_for(reader.read(), TIMEOUT), b"")
            self.assertEqual(
                await asyncio.wait_for(
                    send_request(HOST, listener.sockets[0].getsockname()[1], REQUEST),
                    TIMEOUT,
                ),
                RESPONSE,
            )
        self.assertEqual(router.handle.call_count, 2)

    async def test_shutdown_closes_idle_client(self):
        router = Mock()
        async with running_server(HOST, 0, router) as listener:
            reader, _ = await self.open_connection(listener)
        self.assertEqual(await asyncio.wait_for(reader.read(), TIMEOUT), b"")
        router.handle.assert_not_called()
