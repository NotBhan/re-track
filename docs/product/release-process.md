# Release Process & Publication Runbook

This runbook guides Release Engineers through the deterministic, gate-protected release process for RE:Track.

---

## 1. Release Invariants & Trust Boundary

1. **Tag-Version Match**: Release tags (`vX.Y.Z`) must match the authoritative `__version__` in `backend/app/__init__.py`.
2. **Artifact Immutability**: The exact wheel and sdist built during the release job are inspected, validated in a clean virtual environment, and attached directly to the GitHub Release.
3. **Automated Verification**: Release publication is blocked if any of the following fail:
   - Version consistency (`test_version_authority.py`)
   - Benchmark regression gate (`test_benchmark_baseline_contract.py`)
   - Package contents allowlist (`test_packaging_validation.py`)
   - Clean-install outside repository (`test_packaging_validation.py`)

---

## 2. Step-by-Step Release Workflow

### Step 1: Prepare Release Branch & Increment Version
1. Update `backend/app/__init__.py`:
   ```python
   __version__ = "0.2.0"
   ```
2. Update `package.json` and `src-tauri/tauri.conf.json` to match:
   ```json
   "version": "0.2.0"
   ```
3. Run local verification:
   ```bash
   cd backend && uv run pytest tests/test_version_authority.py tests/test_packaging_validation.py -v
   npm run build
   ```
4. Commit changes:
   ```bash
   git add backend/app/__init__.py package.json src-tauri/tauri.conf.json
   git commit -m "chore: release version 0.2.0"
   ```

### Step 2: Merge to Main & Tag Release
1. Merge the release PR to `main`.
2. Create and push an annotated git tag:
   ```bash
   git tag -a v0.2.0 -m "Release RE:Track v0.2.0"
   git push origin v0.2.0
   ```

### Step 3: Automated Release Execution
GitHub Actions automatically triggers `.github/workflows/release.yml`:
1. Validates `v0.2.0` matches `app.__version__`.
2. Builds wheel (`retrack_ai-0.2.0-py3-none-any.whl`) and sdist (`retrack_ai-0.2.0.tar.gz`).
3. Installs wheel into an isolated virtual environment and tests CLI and FastMCP entrypoints.
4. Generates `SHA256SUMS.txt`.
5. Creates the GitHub Release with generated release notes and attachments.

---

## 3. Post-Release Verification

After release publication:
1. Verify the release asset checksums:
   ```bash
   sha256sum -c SHA256SUMS.txt
   ```
2. Test installation from PyPI or release wheel in a fresh environment:
   ```bash
   uv venv /tmp/test-retrack-env
   source /tmp/test-retrack-env/bin/activate
   pip install retrack_ai-0.2.0-py3-none-any.whl
   retrack --version
   retrack init
   retrack-mcp
   ```
