"""Create certificates for a lab CA, a server, and two clients."""

from __future__ import annotations

import argparse
import os
import secrets
import subprocess
import tempfile
from pathlib import Path


def run_openssl(executable: str, *arguments: str | Path) -> None:
    subprocess.run(
        [executable, *(str(argument) for argument in arguments)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


def generate_certificates(output: Path, openssl: str) -> None:
    output.mkdir(mode=0o700, parents=True)
    ca_cert = output / "ca.pem"
    ca_key = output / "ca.key"
    key_arguments = (
        "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-noenc"
    )
    run_openssl(
        openssl, "req", "-x509", *key_arguments, "-sha256", "-days", "365",
        "-subj", "/CN=Back Office Lab CA", "-keyout", ca_key, "-out", ca_cert,
        "-addext", "basicConstraints=critical,CA:TRUE,pathlen:0",
        "-addext", "keyUsage=critical,keyCertSign,cRLSign",
        "-addext", "subjectKeyIdentifier=hash",
    )

    with tempfile.TemporaryDirectory(dir=output) as scratch:
        request_file = Path(scratch) / "leaf.csr"
        extension_file = Path(scratch) / "leaf.ext"
        for name in ("server", "client-one", "client-two"):
            server = name == "server"
            purpose = "serverAuth" if server else "clientAuth"
            extensions = (
                "basicConstraints=critical,CA:FALSE\n"
                "keyUsage=critical,digitalSignature\n"
                "subjectKeyIdentifier=hash\n"
                "authorityKeyIdentifier=keyid:always\n"
                f"extendedKeyUsage={purpose}\n"
            )
            if server:
                extensions += (
                    "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:::1\n"
                )
            extension_file.write_text(extensions, encoding="ascii")
            run_openssl(
                openssl, "req", "-new", *key_arguments, "-sha256",
                "-subj", f"/CN={'localhost' if server else name}",
                "-keyout", output / f"{name}.key", "-out", request_file,
            )
            run_openssl(
                openssl, "x509", "-req", "-in", request_file,
                "-CA", ca_cert, "-CAkey", ca_key,
                "-set_serial", f"0x{secrets.token_hex(16)}",
                "-sha256", "-days", "30", "-extfile", extension_file,
                "-out", output / f"{name}.pem",
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("certs"))
    parser.add_argument(
        "--openssl", default=os.getenv("BACKOFFICE_OPENSSL", "openssl")
    )
    args = parser.parse_args()
    try:
        generate_certificates(args.output, args.openssl)
    except subprocess.CalledProcessError as exc:
        parser.exit(1, f"OpenSSL failed: {exc.stderr.strip()}\n")
    except OSError as exc:
        parser.exit(1, f"Could not generate certificates: {exc}\n")
    print(f"Generated certificates for the CA, server and clients in {args.output}")


if __name__ == "__main__":
    main()
