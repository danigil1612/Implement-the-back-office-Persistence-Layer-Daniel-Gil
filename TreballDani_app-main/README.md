# TreballDani_app

Aplicació back-office de Fórmula 1 amb capa de persistència implementada amb SQLAlchemy ORM, patró Repository, Unit of Work i migracions amb Alembic.

## Domini

El model representa dades bàsiques d'una temporada de F1:

- conductors;
- cotxes;
- pistes;
- curses;
- pneumàtics;
- resultats de cursa;
- ús de pneumàtics en cada resultat.

## Estructura principal

```text
src/
└── domain/
    ├── config.py
    ├── db.py
    ├── models.py
    └── repositories.py
```

`models.py` conté els models ORM. `repositories.py` conté els repositoris i la unitat de treball. `config.py` centralitza la configuració dels entorns de base de dades.

## Entorns de base de dades

La configuració es fa amb variables d'entorn:

```env
ENVIRONMENT=test
DB_URL_TEST=sqlite:///./f1_test.db
DB_URL_DEVELOPMENT=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME
DB_URL_PRODUCTION=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME
```

Els entorns disponibles són `test`, `development` i `production`. Les URLs de `development` i `production` han de ser de PostgreSQL online i s'han de configurar amb variables d'entorn, sense pujar contrasenyes al repositori.

## Migracions

El projecte inclou dues migracions:

1. `Initial schema creation`
2. `Added last_update attribute`

## Proves

Les proves dels mètodes dels repositoris es troben a:

```text
notebooks/200_repositoris.ipynb
```

El notebook valida les operacions CRUD, les consultes específiques, la paginació i l'operació de domini per afegir pneumàtics a un resultat de cursa.


## Execució ràpida

```bash
python -m pip install -r requirements.txt
cp .env.example .env
ENVIRONMENT=test alembic upgrade head
jupyter nbconvert --to notebook --execute notebooks/200_repositoris.ipynb --output notebooks/200_repositoris_executed.ipynb
```

Per entregar, cal pujar la versió final a la branca `main` amb el commit:

```bash
git add .
git commit -m "Implemented persistence layer"
git push origin main
```
