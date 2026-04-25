# Migrations

SupaCRM production migrations are executed with Alembic and the admin database DSN.

Recommended command from `backend/`:

```bash
alembic upgrade head
```

Equivalent repo-root verification commands:

```bash
./backend/.venv313/bin/python -m alembic -c backend/alembic.ini heads
./backend/.venv313/bin/python -m alembic -c backend/alembic.ini current
./backend/.venv313/bin/python -m alembic -c backend/alembic.ini upgrade head
```

For the first production slice, the deploy script runs migrations before the app containers start:

```bash
bash scripts/deploy.sh
```

Important:

- Use the admin sync DSN for migration execution.
- Do not rely on `create_all()` in production startup.
