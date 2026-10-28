# Formula 1 back-office

This project provides a command-line client and a blocking TCP server for the
Formula 1 back-office persistence layer. The server owns the business service,
repositories, SQLAlchemy models, and database. The client exchanges only JSON
data through the shared protocol and never imports SQLAlchemy.

## Structure

- `src/client.py`: command-line TCP client.
- `src/protocol.py`: JSON framing and response helpers shared by both programs.
- `src/domain/`: persistence-independent field schemas and validation.
- `src/server_app/router.py`: request dispatch and error formatting.
- `src/server_app/service.py`: CRUD and existing repository queries.
- `src/server_app/models.py`, `repositories.py`, `db.py`, `config.py`:
  server-only SQLAlchemy persistence.
- `alembic/`: unchanged database schema migrations.
- `tests/`: unit tests for validation, protocol, routing, and services.
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

## Run the programs

In one terminal:

```powershell
python -m server_app.server --host 127.0.0.1 --port 5050
```

In another terminal, with the same virtual environment and `PYTHONPATH=src`:

```powershell
python -m client list driver
python -m client create driver '{"name":"Alex","nationality":"ES","number":7}'
python -m client read driver 1
python -m client update driver 1 '{"name":"Alex Gil"}'
python -m client delete driver 1
```

For a composite tyre-usage ID, pass a JSON object, for example
`'{"result_id":1,"period":1}'`. The client prints the full JSON response and
exits with status 1 on an error. Use `--host` and `--port` before the operation
to connect to a different server. See `PROTOCOL.md` for filters, pagination,
all entity fields, and error codes.

## Tests

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

The earlier repository notebook remains at `notebooks/200_repositoris.ipynb`
and imports the server-side persistence package.
