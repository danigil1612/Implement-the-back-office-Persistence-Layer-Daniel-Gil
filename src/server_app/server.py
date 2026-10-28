"""Blocking, single-client-at-a-time TCP server."""

from __future__ import annotations

import argparse
import logging
import socket

from protocol import (
    MAX_MESSAGE_BYTES,
    ProtocolError,
    decode_message,
    encode_message,
    failure,
)

from .router import Router
from .service import EntityService


def serve_client(connection: socket.socket, router: Router) -> None:
    """Process one client's newline-delimited requests until it disconnects."""
    with connection.makefile("rb") as incoming:
        while True:
            line = incoming.readline(MAX_MESSAGE_BYTES + 2)
            if not line:
                return
            try:
                request = decode_message(line)
                response = router.handle(request)
            except ProtocolError as exc:
                response = failure(exc.code, str(exc))
            try:
                encoded_response = encode_message(response)
            except ProtocolError as exc:
                encoded_response = encode_message(failure(exc.code, str(exc)))
            connection.sendall(encoded_response)
            if len(line) > MAX_MESSAGE_BYTES + 1 or not line.endswith(b"\n"):
                return


def serve(host: str, port: int, router: Router) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((host, port))
        listener.listen(1)
        logging.info("Listening on %s:%s", host, port)
        while True:
            connection, address = listener.accept()
            logging.info("Client connected: %s", address)
            with connection:
                try:
                    serve_client(connection, router)
                except OSError:
                    logging.exception("Client connection failed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Formula 1 back-office server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5050)
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        serve(arguments.host, arguments.port, Router(EntityService()))
    except KeyboardInterrupt:
        logging.info("Server stopped")


if __name__ == "__main__":
    main()
