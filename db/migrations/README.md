# Migrations

Plain SQL, applied in order with `psql`:

```bash
for f in db/migrations/*.sql; do psql "$DATABASE_URL" -f "$f"; done
```

`001_init.sql` includes `schema.sql`. Add new numbered files (`002_add_x.sql`)
for incremental changes; every statement should be idempotent (`IF NOT EXISTS`).
For local SQLite development no migration is needed — SQLAlchemy creates the
tables on first start.
