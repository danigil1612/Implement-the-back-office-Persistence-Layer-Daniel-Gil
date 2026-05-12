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
DB_URL_DEVELOPMENT=postgresql+psycopg://admin:admin123@localhost:5432/dam
DB_URL_PRODUCTION=postgresql+psycopg://admin:admin123@localhost:5432/dam
```

Els entorns disponibles són `test`, `development` i `production`.

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
