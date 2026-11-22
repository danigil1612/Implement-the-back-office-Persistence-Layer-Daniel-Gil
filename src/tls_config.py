"""Build verified TLS contexts for the back-office client and server."""

from __future__ import annotations

import argparse
import ssl
from pathlib import Path

HANDSHAKE_TIMEOUT = 10.0


def add_tls_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ca", type=Path, required=True, help="CA PEM")
    parser.add_argument("--cert", type=Path, required=True, help="Cert PEM")
    parser.add_argument("--key", type=Path, required=True, help="Key PEM")


def create_context(
    ca_file: Path, cert_file: Path, key_file: Path, *, server_side: bool
) -> ssl.SSLContext:
    protocol = (
        ssl.PROTOCOL_TLS_SERVER if server_side else ssl.PROTOCOL_TLS_CLIENT
    )
    context = ssl.SSLContext(protocol)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(cafile=str(ca_file))
    context.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))
    if server_side:
        context.num_tickets = 0
    else:
        context.hostname_checks_common_name = False
    return context
