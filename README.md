# Formula 1 back-office

This project provides an asyncio client and a concurrent server for the
Formula 1 back office. Both peers authenticate with certificates and exchange
JSON over TLS. The server owns the business service, repositories, SQLAlchemy
models, and database. The [architecture diagram](ARCHITECTURE.md) shows the
TLS boundary and database access. [SECURITY.md](SECURITY.md) describes the
handshake, certificate roles, and demonstration steps.

## Structure

- `src/client.py`: command-line TCP client.
- `src/protocol.py`: JSON framing and response helpers shared by both programs.
- `src/tls_config.py`: certificate and trust settings for both programs.
- `tools/generate_certificates.py`: lab CA, server and two client identities.
- `src/domain/`: persistence-independent field schemas and validation.
- `src/server_app/router.py`: request dispatch and error formatting.
- `src/server_app/service.py`: CRUD and existing repository queries.
- `src/server_app/models.py`, `repositories.py`, `db.py`, `config.py`:
  server-only SQLAlchemy persistence.
- `alembic/`: unchanged database schema migrations.
- `tests/`: unit tests and loopback tests for concurrent connections.
- `PROTOCOL.md`: complete wire format, operations, fields, and errors.

## Database setup

Python 3.10 or newer is required. Install dependencies from `requirements.txt`.
The default `test` environment uses SQLite at `./f1_test.db`. The existing
`development` and `production` environments use PostgreSQL URLs from
`DB_URL_DEVELOPMENT` and `DB_URL_PRODUCTION` respectively. Configuration can
be placed in `.env` (see `.env.example`). Keep credentials out of Git.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:ENVIRONMENT = "test"
python -m alembic upgrade head
$env:PYTHONPATH = "src"
```

## Generate certificates and run the programs

Use Python with TLS 1.3 support and OpenSSL 3 for certificate generation.
Run this once from the repository root. The script creates a new `certs/`
directory and refuses to overwrite an existing directory. Use `--openssl`
with the full executable path if OpenSSL is outside your `PATH`.

```powershell
python tools/generate_certificates.py
```

In one terminal:

```powershell
python -m server_app.server --ca certs/ca.pem --cert certs/server.pem --key certs/server.key
```

In another terminal, with the same virtual environment and `PYTHONPATH=src`:

```powershell
$clientOne = @('--ca', 'certs/ca.pem', '--cert', 'certs/client-one.pem', '--key', 'certs/client-one.key')
$clientTwo = @('--ca', 'certs/ca.pem', '--cert', 'certs/client-two.pem', '--key', 'certs/client-two.key')
python -m client @clientOne list driver
'{"name":"Alex","nationality":"ES","number":7}' | python -m client @clientOne create driver -
python -m client @clientTwo read driver 1
'{"name":"Alex Gil"}' | python -m client @clientTwo update driver 1 -
python -m client @clientOne delete driver 1
```

The `-` argument reads JSON from standard input. This form works in Windows
PowerShell 5.1, which can strip quotes from JSON passed directly as a native
command argument. For a composite tyre-usage ID, pipe a JSON object such as
`'{"result_id":1,"period":1}'` into `read tyre_usage -`. The client prints
the full JSON response and exits with status 1 on an error. Use `--host` and
`--port` before the operation to connect to a different server. See
`PROTOCOL.md` for filters, pagination, all entity fields, and error codes.

## Tests

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

The TLS loopback tests generate temporary certificates using `openssl`.
Set `BACKOFFICE_OPENSSL` to its executable path if necessary. The tests
exercise both valid identities concurrently and reject missing or untrusted
client certificates and an incorrect server identity.

The earlier repository notebook remains at `notebooks/200_repositoris.ipynb`
and imports the server-side persistence package.
