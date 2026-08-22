# RE:Track Upgrade, Migration & Reset Guide

**Document Type**: Operational Maintenance & Upgrade Contract  
**Version**: 0.1.0 (Phase 9B Release Baseline)  

---

## 1. Upgrade Safety Invariants

RE:Track implements strict data protection guarantees during package upgrades:
1. **Zero Silent Overwrites**: Upgrading `retrack-ai` and running `retrack init` preserves all existing user configurations, custom provider settings, registered repositories, and saved context packages.
2. **Automated Pre-Change Backups**: Any state reset or legacy data migration automatically creates an uncompressed snapshot in `~/.retrack/backups/`.
3. **Repository Immutability Guarantee**: Application maintenance commands **never** modify, write to, or delete user source repositories under any circumstances.

---

## 2. Migrating from Legacy Andes (`~/.andes/`)

RE:Track maintains read-only fallback compatibility with legacy `~/.andes/` data. To permanently copy and merge legacy metadata into canonical `~/.retrack/`:

### Step 1: Preview Migration (Dry Run)
```bash
retrack migrate --dry-run
```
Output displays the discovered legacy files, target paths in `~/.retrack/`, and total byte volume without writing any data.

### Step 2: Execute Migration
```bash
retrack migrate
```
- Creates an automated snapshot in `~/.retrack/backups/pre_migration_<timestamp>/`.
- Merges legacy repository records and context packages into `~/.retrack/`.
- Copies cached manifests without overwriting existing canonical manifests.
- **Leaves `~/.andes/` completely intact and unmodified.**

---

## 3. Scoped State Reset (`retrack reset`)

If local metadata or cache becomes corrupted, use `retrack reset` with the appropriate scope:

### 1. Cache Reset (Non-Destructive)
Clears cached AST fingerprints and temporary context chunks. Does not require confirmation.
```bash
retrack reset --cache
```

### 2. Application State Reset
Clears registered repository metadata, saved context packages, and cached manifests. Requires explicit confirmation.
```bash
retrack reset --state --confirm
# or interactive:
retrack reset --state
```
*Creates automatic pre-reset backup before clearing state.*

### 3. Full Environment Reset
Resets all `~/.retrack/` state and restores `settings.json` to factory defaults.
```bash
retrack reset --all --confirm
```
*Creates automatic pre-reset backup before re-initializing defaults.*

---

## 4. Uninstall Safety & Residual Data

When uninstalling `retrack-ai` via `pip uninstall retrack-ai`:
- The Python package binaries and CLI entry points are removed.
- **Your data remains preserved in `~/.retrack/`** unless you explicitly delete the folder.
- To completely remove all RE:Track data after uninstallation:
  ```bash
  rm -rf ~/.retrack
  ```
