# PortAct — Migration Guide (v1.0.x → v1.1.0)

This guide helps existing users upgrade their PortAct installation to v1.1.0.

## What Changed in v1.1.0

- **Database schema**: Asset types are now stored as VARCHAR with a foreign key to the `asset_types` master table (previously a PostgreSQL native enum)
- **Snapshot system**: EOD snapshots now properly link to source accounts via `snapshot_source`, `bank_account_id`, `demat_account_id`, and `crypto_account_id` columns
- **Enum normalization**: All PostgreSQL enum values are normalized to lowercase
- **Export format**: Bumped to v5.0 (still supports restoring from v1.0–v4.0 backups)
- **New columns**: `allowed_conversions` on asset types, `api_symbol` on assets

These changes require running database migrations. **Your existing data will be preserved and migrated automatically.**

---

## Before You Start

1. **Take a backup** of your database (the migration script does this automatically, but a manual backup is always wise)
2. **Note your current version**: check the `VERSION` file or the health endpoint (`/health`)
3. **Ensure no one is actively using the app** during the upgrade

---

## Option A: Docker All-in-One (Recommended for most users)

If you run PortAct using `docker run debasisdas1976/portact:latest`, the upgrade is automatic:

```bash
# 1. Stop the running container
docker stop portact

# 2. Pull the new image
docker pull debasisdas1976/portact:latest

# 3. Start with your existing data volume
docker run -d \
  --name portact \
  -p 8080:8080 \
  -v portact_data:/var/lib/postgresql/data \
  debasisdas1976/portact:latest

# 4. Verify
curl http://localhost:8080/health
```

The container entrypoint runs `alembic upgrade head` automatically on every start. After the container is up, run the data fix script:

```bash
# 5. Run data fix (fixes Vested/INDMoney demat account market classification)
docker exec portact python /app/backend/scripts/post_migrate_fix.py
```

---

## Option B: Docker Compose

If you use the multi-service Docker Compose setup:

```bash
cd /path/to/PortAct

# 1. Pull latest code
git pull --ff-only

# 2. Rebuild and restart
docker compose -f infrastructure/docker-compose.yml down
docker compose -f infrastructure/docker-compose.yml up -d --build

# 3. Run migrations (if not auto-run by entrypoint)
docker compose -f infrastructure/docker-compose.yml exec backend alembic upgrade head

# 4. Run data fix
docker compose -f infrastructure/docker-compose.yml exec backend python scripts/post_migrate_fix.py

# 5. Verify
curl http://localhost:8000/health
```

---

## Option C: AWS EC2 Production

```bash
cd /opt/portact

# 1. Pull latest code
git pull --ff-only

# 2. Take a manual DB backup first
./infrastructure/aws/backup.sh

# 3. Rebuild and restart
docker compose -f infrastructure/aws/docker-compose.prod.yml down
docker compose -f infrastructure/aws/docker-compose.prod.yml up -d --build

# 4. Run migrations
docker compose -f infrastructure/aws/docker-compose.prod.yml exec backend alembic upgrade head

# 5. Run data fix
docker compose -f infrastructure/aws/docker-compose.prod.yml exec backend python scripts/post_migrate_fix.py

# 6. Verify
curl http://localhost:8000/health
```

---

## Option D: Native Install (macOS / Linux)

The simplest way — use the automated migration script:

```bash
cd /path/to/PortAct

# Run the migration script (handles everything)
./scripts/migrate.sh
```

Or do it manually:

```bash
cd /path/to/PortAct

# 1. Stop the running servers
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "react-scripts start" 2>/dev/null || true

# 2. Pull latest code
git pull --ff-only

# 3. Activate virtual environment
source backend/venv/bin/activate   # or .venv/bin/activate

# 4. Update backend dependencies
cd backend
pip install -r requirements.txt

# 5. Take a database backup
pg_dump -h localhost -U portact_user portact_db | gzip > ../backup_before_v1.1.0_$(date +%Y%m%d_%H%M%S).sql.gz

# 6. Run database migrations
alembic upgrade head

# 7. Run data fix
python scripts/post_migrate_fix.py

# 8. Update frontend dependencies
cd ../frontend
npm install

# 9. Restart the application
cd ..
./update.sh
# or start manually:
#   cd backend && nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
#   cd frontend && BROWSER=none nohup npm start > frontend.log 2>&1 &

# 10. Verify
curl http://localhost:8000/health
```

---

## Post-Migration Verification

After upgrading, verify these items:

| Check | Command / Action | Expected Result |
|-------|-----------------|-----------------|
| Health endpoint | `curl http://localhost:8000/health` | `{"status": "healthy", "database": "ok"}` |
| Version | Check `/health` response | `"version": "1.1.0"` |
| Dashboard loads | Open the app in browser | Dashboard shows all assets and accounts |
| Asset types | Check any asset detail page | Asset type displays correctly |
| Snapshots work | Wait for next EOD snapshot or trigger manually | Performance chart shows data |
| Export works | Portfolio → Export | Downloads JSON file with `export_version: "5.0"` |

---

## Known Data Fix

**Vested / INDMoney demat accounts**: An earlier migration had a case-sensitive comparison that may have failed to set `account_market = 'international'` for these brokers. The `post_migrate_fix.py` script corrects this automatically.

If you want to check manually:

```sql
-- Check if any Vested/INDMoney accounts are incorrectly marked as domestic
SELECT id, broker_name, account_market
FROM demat_accounts
WHERE broker_name IN ('vested', 'indmoney')
  AND account_market = 'domestic';
```

---

## Troubleshooting

### Migration fails with "relation does not exist"

Your database may be in an inconsistent state. Check the current migration:

```bash
cd backend && alembic current
```

If it shows no revision, your database was created with `create_all()` (development mode) instead of Alembic. You need to stamp it at the initial migration first:

```bash
alembic stamp 753a2500fedc
alembic upgrade head
```

### Server won't start after migration

Check the logs for the specific error:

```bash
# Native install
tail -50 backend.log

# Docker
docker logs portact --tail 50
```

Common causes:
- **"Missing asset types"**: Run `alembic upgrade head` again — the seed sync needs all migrations applied first
- **SECRET_KEY error in production**: Generate a proper key: `openssl rand -hex 32` and set it in `.env`

### "type assettype does not exist"

This error means you're running an older version of `main.py` that still references the dropped PostgreSQL enum. Make sure you pulled the latest code (`git pull`) before running migrations.

### Export from old version won't restore

PortAct v1.1.0 supports restoring exports from v1.0 through v5.0. If your export file has `export_version: "1.0"` through `"4.0"`, it will restore correctly. The restore logic automatically handles missing fields and old enum formats.

---

## Rollback (Emergency Only)

If something goes wrong and you need to revert:

1. Stop the application
2. Restore the database from your backup:
   ```bash
   gunzip -c backup_before_v1.1.0_TIMESTAMP.sql.gz | psql -h localhost -U portact_user portact_db
   ```
3. Check out the previous version:
   ```bash
   git checkout v1.0.x   # or the specific tag/commit you were on
   ```
4. Restart the application

> **Warning**: Downgrading Alembic migrations is not recommended for this release due to the enum type changes. Restoring from a backup is the safest rollback path.
