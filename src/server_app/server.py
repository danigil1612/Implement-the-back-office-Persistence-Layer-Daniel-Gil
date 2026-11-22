"""Asynchronous TCP server with one request stream per client."""

from __future__ import annotations

import argparse
import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from protocol import (
    MAX_MESSAGE_BYTES,
    ProtocolError,
    close_stream,
    decode_message,
    encode_message,
    failure,
    read_frame,
)

from .router import Router
from .service import EntityService


async def serve_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    router: Router,
) -> None:
    address = writer.get_extra_info("peername")
    logging.info("Client connected: %s", address)
    try:
        while True:
            try:
                line = await read_frame(reader)
            except ProtocolError as exc:
                writer.write(encode_message(failure(exc.code, str(exc))))
                await writer.drain()
                return
            if not line:
                return

            try:
                request = decode_message(line)
                response = await asyncio.to_thread(router.handle, request)
                frame = encode_message(response)
            except ProtocolError as exc:
                frame = encode_message(failure(exc.code, str(exc)))

            writer.write(frame)
            await writer.drain()
            if not line.endswith(b"\n"):
                return
    except OSError as exc:
        logging.debug("Client connection failed: %s: %s", address, exc)
    except Exception:
        logging.exception("Unexpected client failure: %s", address)
    finally:
        await close_stream(writer)
        logging.info("Client disconnected: %s", address)


@asynccontextmanager
async def running_server(
    host: str, port: int, router: Router
) -> AsyncIterator[asyncio.Server]:
    clients: dict[asyncio.Task[None], asyncio.StreamWriter] = {}
    stopping = False

    def connect(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        if stopping:
            writer.close()
            return
        task = asyncio.create_task(serve_client(reader, writer, router))
        clients[task] = writer
        task.add_done_callback(clients.pop)

    listener = await asyncio.start_server(
        connect, host, port, limit=MAX_MESSAGE_BYTES
    )
    try:
        yield listener
    finally:
        stopping = True
        listener.close()
        active_clients = tuple(clients.items())
        for task, writer in active_clients:
            writer.close()
            task.cancel()
        await asyncio.gather(
            *(task for task, _ in active_clients), return_exceptions=True
        )
        await asyncio.gather(
            *(close_stream(writer) for _, writer in active_clients)
        )
        await listener.wait_closed()


async def serve(host: str, port: int, router: Router) -> None:
    async with running_server(host, port, router) as listener:
        addresses = ", ".join(str(sock.getsockname()) for sock in listener.sockets)
        logging.info("Listening on %s", addresses)
        await listener.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Formula 1 back-office server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5050)
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        asyncio.run(serve(arguments.host, arguments.port, Router(EntityService())))
    except KeyboardInterrupt:
        logging.info("Server stopped")


if __name__ == "__main__":
    main()
