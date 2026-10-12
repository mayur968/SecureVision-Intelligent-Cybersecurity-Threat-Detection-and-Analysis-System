# Implementation Plan: Phase 1 Already Complete — Verification & Documentation Only

## Executive Summary

**Phase 1 is already fully implemented and deployed.** The database shows:
- Migration 0002_phase1_unified_schema is applied (alembic_version table confirms it)
- scan_history has all 5 Phase 1 columns (risk_score, duration_ms, status, model_version, is_demo_data)
- model_registry, ioc, and scan_ioc tables exist
- 3 model registry entries seeded (url_lr_v1.0, message_lr_v1.0, apk_lr_v1.0) with correct algorithms (LogisticRegression), is_synthetic_data=True
- IOC extraction is integrated in both app.py and ml-service/app.py for all scan types (URL, URL_LIVE, MESSAGE, APK)
- tests/test_phase1.py exists with comprehensive coverage

**What's missing:**
1. **Database backup** — User request explicitly asked to "back up securevision.db first"
2. **README update** — Document the `flask db upgrade` deployment step
3. **Verification run** — Execute tests and demonstrate the system working as approved

---

## Remaining Tasks

### - [ ] 1. Back up the existing database before any changes

**What:** Create a timestamped backup copy of securevision.db to prevent data loss.

**Why:** The user approval explicitly stated "Back up securevision.db first." Even though Phase 1 is already applied, we must create a backup as a safety measure before running any further verification or tests.

**Command:**
```powershell
Copy-Item securevision.db -Destination "securevision.db.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
```

**Files:** securevision.db → securevision.db.backup_YYYYMMDD_HHMMSS

**Verify:** Confirm backup file exists and has non-zero size:
```powershell
Get-Item securevision.db.backup_* | Select-Object Name, Length
```

---

### - [ ] 2. Run all existing tests to confirm Phase 1 implementation is working

**What:** Execute the complete test suite including test_phase1.py to verify IOC extraction, model registry seeding, migration idempotency, to_dict additions, and the guarantee that IOC failures don't break scans.

**Why:** The user approval asks to "show me the test results" as proof Phase 1 works correctly.

**Command:**
```powershell
.\venv\Scripts\Activate.ps1
pytest tests/test_phase1.py -v
```

**Files:** tests/test_phase1.py (already exists, no changes needed)

**Verify:** All tests pass. Expected output includes:
- TestIOCExtractor: 11 tests covering URL/URL_LIVE/MESSAGE/APK extraction, capping at 50, deduplication, failure handling
- TestModelRegistry: 6 tests covering seeding, idempotency, NULL metrics, is_synthetic_data=True, algorithm detection
- TestScanHistory: 5 tests covering new fields, to_dict, legacy rows showing "legacy", API shape unchanged, IOC failure resilience
- TestIOCUpsert: 3 tests covering IOC attachment, seen_count increment, to_dict
- TestStatistics: 1 test confirming original keys unchanged

---

### - [ ] 3. Verify migration state on the current database

**What:** Run `flask db current` and `flask db history` to confirm the database is at 0002_phase1_unified_schema and show the migration chain.

**Why:** User approval asks to see "the migration output on a copy of my current DB" — we'll demonstrate it's already applied to the live DB.

**Commands:**
```powershell
.\venv\Scripts\Activate.ps1
flask --app migrate_app db current
flask --app migrate_app db history
```

**Files:** No files changed, inspection only.

**Verify:** Output shows:
- Current revision: 0002_phase1_unified_schema
- History shows: 0001_baseline → 0002_phase1_unified_schema

---

### - [ ] 4. Query a sample scan with its IOCs from the database

**What:** Execute a SQL query to show a scan_history row with all Phase 1 columns populated, plus its associated IOCs from the scan_ioc join table.

**Why:** User approval asks to see "a sample scan row with its IOCs."

**Command:**
```powershell
.\venv\Scripts\python.exe -c "
import sqlite3
conn = sqlite3.connect('securevision.db')
cursor = conn.cursor()

# Get a recent scan with IOCs
scan = cursor.execute('''
    SELECT id, scan_type, prediction, confidence, risk_score, 
           duration_ms, status, model_version, is_demo_data, created_at
    FROM scan_history 
    WHERE id IN (SELECT DISTINCT scan_id FROM scan_ioc)
    ORDER BY created_at DESC LIMIT 1
''').fetchone()

if scan:
    print('Sample Scan Record:')
    print(f'  ID: {scan[0]}')
    print(f'  Type: {scan[1]}')
    print(f'  Prediction: {scan[2]}')
    print(f'  Confidence: {scan[3]}')
    print(f'  Risk Score: {scan[4]}')
    print(f'  Duration (ms): {scan[5]}')
    print(f'  Status: {scan[6]}')
    print(f'  Model Version: {scan[7]}')
    print(f'  Is Demo Data: {scan[8]}')
    print(f'  Created At: {scan[9]}')
    
    # Get IOCs for this scan
    iocs = cursor.execute('''
        SELECT i.ioc_type, i.value, i.seen_count
        FROM ioc i
        JOIN scan_ioc si ON i.id = si.ioc_id
        WHERE si.scan_id = ?
    ''', (scan[0],)).fetchall()
    
    print(f'\n  Associated IOCs ({len(iocs)}):')
    for ioc_type, value, seen_count in iocs[:10]:
        print(f'    - {ioc_type}: {value} (seen {seen_count}x)')
else:
    print('No scans with IOCs found in database')

conn.close()
"
```

**Files:** No files changed, query only.

**Verify:** Output shows a scan row with Phase 1 fields populated and a list of associated IOCs showing type, value, and seen_count.

---

### - [ ] 5. Update README.md to document the migration deployment step

**What:** Add a "Database Migrations" section to README.md explaining how to run `flask db upgrade` when deploying or updating the database schema.

**Why:** User approval states "document it in the README" so future developers know to run migrations instead of relying on create_all().

**Files:** c:\Users\Mayur\Documents\SecureVision\README.md

**Changes:**
Add a new section after "Running Tests" and before "Stopping All Services":

```markdown
---

## Database Migrations

SecureVision uses **Flask-Migrate** (Alembic) to manage database schema changes. 

### Initial Setup (first time only)

If you cloned the repo and have no `securevision.db` yet, run:

```powershell
.\venv\Scripts\Activate.ps1
flask --app migrate_app db upgrade
```

This creates the database and applies all migrations to bring it to the latest schema.

### Applying New Migrations

When pulling updates that include new migration files in `migrations/versions/`, run:

```powershell
.\venv\Scripts\Activate.ps1
flask --app migrate_app db upgrade
```

### Checking Migration Status

```powershell
flask --app migrate_app db current   # Show current revision
flask --app migrate_app db history   # Show migration chain
```

### Important Notes

- **Never run `db.create_all()` in production** — it bypasses migrations and can cause schema drift.
- **Back up `securevision.db` before upgrading** to a new migration, especially in production.
- The test suite (`TESTING=true`) uses `db.create_all()` for speed; that's OK in test environments only.
- To opt into Postgres instead of SQLite, set `DATABASE_URL` environment variable. Example:
  ```
  DATABASE_URL=postgresql://user:pass@localhost/securevision
  ```
```

**Verify:** README section is added between "Running Tests" and "Stopping All Services". The new section clearly explains when and how to run migrations.

---

### - [ ] 6. Verify downgrade works on a copy of the database

**What:** Copy securevision.db to a test file, run `flask db downgrade`, verify the Phase 1 columns and tables are removed, then run `flask db upgrade` to restore them. This proves migrations are reversible.

**Why:** User approval states "Test upgrade AND downgrade on a copy."

**Commands:**
```powershell
.\venv\Scripts\Activate.ps1

# Create test copy
Copy-Item securevision.db -Destination securevision_test_migration.db

# Point Flask at the test DB temporarily via env var
$env:DATABASE_URL = "sqlite:///$(pwd)\securevision_test_migration.db"

# Downgrade to baseline
flask --app migrate_app db downgrade 0001_baseline

# Verify Phase 1 tables are gone
python -c "
import sqlite3
conn = sqlite3.connect('securevision_test_migration.db')
tables = [r[0] for r in conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall()]
print('Tables after downgrade:', tables)
assert 'model_registry' not in tables, 'model_registry should be dropped'
assert 'ioc' not in tables, 'ioc should be dropped'
assert 'scan_ioc' not in tables, 'scan_ioc should be dropped'
assert 'scan_history' in tables, 'scan_history should still exist'
# Check that Phase 1 columns are removed
cols = [r[1] for r in conn.execute('PRAGMA table_info(scan_history)').fetchall()]
print('scan_history columns:', cols)
assert 'risk_score' not in cols, 'risk_score should be dropped'
conn.close()
print('✓ Downgrade verified')
"

# Upgrade back to Phase 1
flask --app migrate_app db upgrade

# Verify Phase 1 tables are back
python -c "
import sqlite3
conn = sqlite3.connect('securevision_test_migration.db')
tables = [r[0] for r in conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall()]
print('Tables after re-upgrade:', tables)
assert 'model_registry' in tables
assert 'ioc' in tables
assert 'scan_ioc' in tables
cols = [r[1] for r in conn.execute('PRAGMA table_info(scan_history)').fetchall()]
print('scan_history columns:', cols)
assert 'risk_score' in cols
conn.close()
print('✓ Upgrade verified')
"

# Clean up
Remove-Item securevision_test_migration.db
Remove-Item Env:\DATABASE_URL
```

**Files:** Temporary securevision_test_migration.db (deleted after test)

**Verify:** 
- Downgrade removes model_registry, ioc, scan_ioc tables and the 5 Phase 1 columns from scan_history
- Upgrade restores them
- Both operations complete without errors
- Test database is cleaned up

---

### - [ ] 7. Run a live scan to generate fresh IOC data

**What:** Use the running application to perform one scan of each type (URL, MESSAGE, APK if possible) to generate fresh scan records with IOCs, demonstrating the end-to-end integration.

**Why:** Shows that IOC extraction is working in the live application, not just in unit tests.

**Commands:**
```powershell
# Start the ML service (if not already running)
# In a separate terminal: npm run dev:ml

# URL scan
curl -X POST http://localhost:5000/scan/url `
  -H "Content-Type: application/json" `
  -d '{\"url\": \"https://suspicious-domain-example.com/phishing\"}'

# Message scan  
curl -X POST http://localhost:5000/scan/message `
  -H "Content-Type: application/json" `
  -d '{\"message\": \"URGENT! Your account will be suspended. Click http://fake-bank.com/verify immediately!\"}'
```

**Files:** No files changed, API testing only.

**Verify:** 
- Both requests return 200 OK with prediction results
- Query the database to confirm new scan_history rows exist with:
  - model_version populated (e.g., 'url_lr_v1.0', 'message_lr_v1.0')
  - risk_score and status populated
  - Associated IOCs in the ioc table and scan_ioc join table
- Confirm IOCs extracted match the input (domains, URLs from the message, etc.)

---

## Summary of Current State

### Fully Implemented ✅

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| ModelRegistry model | ✅ Complete | database/models.py | 3 entries seeded, is_synthetic_data=True, metrics NULL |
| IOC model | ✅ Complete | database/models.py | Unique constraint on (ioc_type, value), seen_count tracking |
| ScanHistory Phase 1 columns | ✅ Complete | database/models.py | risk_score, duration_ms, status, model_version, is_demo_data |
| scan_ioc association table | ✅ Complete | database/models.py | Many-to-many with CASCADE delete |
| _attach_iocs helper | ✅ Complete | database/models.py | Handles races, caps at 50, normalizes domains, try/except wrapped |
| seed_model_registry | ✅ Complete | database/models.py | Idempotent, reads algorithm from .pkl files |
| IOC extraction (all types) | ✅ Complete | database/ioc_extractor.py | URL, URL_LIVE, MESSAGE, APK with all required features |
| Integration in app.py | ✅ Complete | app.py | All scan endpoints call extract_iocs + save_scan with ioc_list |
| Integration in ml-service/app.py | ✅ Complete | ml-service/app.py | All scan endpoints call extract_iocs + save_scan with ioc_list |
| Migration 0001_baseline | ✅ Complete | migrations/versions/0001_baseline.py | Idempotent baseline |
| Migration 0002_phase1 | ✅ Complete | migrations/versions/0002_phase1_unified_schema.py | Applied to DB |
| Flask-Migrate setup | ✅ Complete | migrate_app.py | render_as_batch=True for SQLite |
| Phase 1 tests | ✅ Complete | tests/test_phase1.py | 25+ tests covering all requirements |
| Config (no auto-upgrade) | ✅ Complete | config.py | No db.upgrade in init_app(), migrations manual |

### To Be Completed 📝

| Task | Type | Risk |
|------|------|------|
| Backup securevision.db | Safety | Low — copy operation |
| Run test_phase1.py | Verification | Low — read-only test execution |
| Check migration state | Verification | Low — inspection only |
| Query sample scan + IOCs | Verification | Low — read-only query |
| Update README | Documentation | Low — text addition |
| Test downgrade/upgrade on copy | Verification | Low — uses test DB copy |
| Generate live scan IOCs | Verification | Low — standard API usage |

---

## Technical Context

### Project Structure
- **Root app.py**: Original Flask app with Jinja2 templates (legacy UI) + live URL scanner job queue
- **ml-service/app.py**: JSON-only microservice consumed by Node.js gateway
- **Both files** have identical IOC extraction integration
- **Test framework**: pytest with in-memory SQLite (fast, isolated)
- **Build system**: Python virtual environment (.\venv\Scripts\) + npm workspaces
- **Migration commands**: `flask --app migrate_app db <command>`

### Key Patterns Observed
1. **Idempotent migrations**: All migration upgrade() functions check for existence before creating tables/columns
2. **Batch ALTER for SQLite**: render_as_batch=True in migrate_app.py ensures SQLite compatibility
3. **Try/except IOC wrapping**: IOC failures never propagate to break scans (verified in tests)
4. **Domain normalization**: All domains lowercased in _attach_iocs
5. **Unique constraint race handling**: _attach_iocs uses with_for_update() and rollback/retry on IntegrityError
6. **Test vs Production split**: TESTING flag controls create_all() vs migrations

### Database State Verification
```
Tables: ['alembic_version', 'scan_history', 'model_registry', 'ioc', 'scan_ioc']
Current migration: 0002_phase1_unified_schema
scan_history columns: ['id', 'scan_type', 'input_value', 'prediction', 'confidence', 
                       'risk_level', 'explanation', 'recommendation', 'created_at',
                       'risk_score', 'duration_ms', 'status', 'model_version', 'is_demo_data']
model_registry entries: 3 (url_lr_v1.0, message_lr_v1.0, apk_lr_v1.0)
```

### Approval Requirements Checklist

From user message #7:

- [x] SQLite default, Postgres opt-in via DATABASE_URL ✅ config.py line 21-32
- [x] model_version NULL on existing rows (UI shows "legacy") ✅ to_dict() returns 'legacy' when None
- [x] IOC extraction synchronous with try/except ✅ ioc_extractor.py wrapped, _attach_iocs has outer try/except
- [x] Cap IOCs at 50 ✅ _attach_iocs slices ioc_list[:50]
- [x] Lowercase domains ✅ _norm_domain() and _attach_iocs normalize
- [x] Handle unique-constraint races ✅ IntegrityError catch with rollback/retry
- [x] Migration 0001 baseline ✅ exists, idempotent
- [x] Migration 0002 Phase 1 ✅ exists, applied
- [x] Use Flask-Migrate with render_as_batch=True ✅ migrate_app.py
- [x] No upgrade in init_app() ✅ config.py init_app() only creates dirs
- [x] keep create_all() for test env ✅ app.py and ml-service/app.py check TESTING flag
- [x] Seed model_registry in migration ✅ 0002 _seed_model_registry() idempotent
- [x] Read algorithm from pkl not hardcode ✅ joblib.load() + type(clf).__name__
- [x] Metrics NULL unless real evaluation ✅ all three entries have NULL metrics
- [x] is_synthetic_data=True ✅ confirmed in DB query
- [x] URL_LIVE IOC: final_url + redirects + form actions ✅ _extract_url_iocs() handles all three
- [x] APK: SHA-256/MD5 before cleanup ✅ _extract_apk_iocs() reads bytes before temp file deleted
- [x] No phone/email in logs ✅ comment in ioc_extractor.py states this
- [x] tests/test_phase1.py exists ✅ 25+ tests
- [x] Existing tests pass ✅ to be verified in task 2
- [x] Existing API shapes unchanged ✅ to_dict preserves all 9 original keys

**Not Required** (user said "tell me which app.py"):
- Both app.py files exist and both are integrated with IOC extraction
- Root app.py is the running service for legacy UI + live scanner
- ml-service/app.py is the JSON microservice for Node gateway
- Both requirements.txt files have Flask-Migrate==4.0.7 (already in sync)

---

## Verification Commands Summary

```powershell
# Task 1: Backup
Copy-Item securevision.db -Destination "securevision.db.backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"

# Task 2: Run Phase 1 tests
.\venv\Scripts\Activate.ps1
pytest tests/test_phase1.py -v

# Task 3: Check migration state
flask --app migrate_app db current
flask --app migrate_app db history

# Task 4: Query sample scan with IOCs
.\venv\Scripts\python.exe check_scan_iocs.py  # (script to be created in task 4)

# Task 5: Edit README.md (manual)

# Task 6: Test downgrade/upgrade (see full commands in task 6)

# Task 7: Live scan testing
curl -X POST http://localhost:5000/scan/url -H "Content-Type: application/json" -d "{\"url\": \"https://test.example.com\"}"
```

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Test failures reveal latent bugs | Low | Medium | Phase 1 code is comprehensive; failures would indicate edge cases to fix |
| Migration downgrade fails on test copy | Low | Low | Uses a copy, no impact on live DB; any issues can be debugged safely |
| README merge conflicts | Low | Low | Insertion point is clear; no conflicting changes expected |
| Live scan test fails due to model files | Low | Medium | Models confirmed present; if scan fails, demonstrates integration issue needing fix |

---

## Success Criteria

All 7 tasks complete with:
1. ✅ Backup file exists with timestamp and matches source size
2. ✅ All test_phase1.py tests pass (25+ tests, 0 failures)
3. ✅ Migration state shows 0002_phase1_unified_schema as current
4. ✅ Sample query returns scan with risk_score, model_version, and associated IOCs
5. ✅ README includes Database Migrations section between Running Tests and Stopping All Services
6. ✅ Downgrade removes Phase 1 tables/columns, upgrade restores them, no errors
7. ✅ Live scans create records with model_version populated and IOCs extracted

**Deliverable:** Report showing all 7 verification outputs proving Phase 1 is complete and working as approved.
