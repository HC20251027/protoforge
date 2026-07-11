---
'@protoforge/api': patch
'@protoforge/web': patch
'@protoforge/shared': patch
---

# Phase 4: P1 fixes + quality debt cleanup

## Security
- **API key encryption upgraded to cryptography Fernet** (was base64 fallback). Production API keys now encrypted at rest, key persisted to `.protoforge/.protoforge_key`. base64 fallback retained with explicit `UserWarning` when `cryptography` is missing.

## Bug fixes
- **GGUF v3 magic byte fix**: `loader.py` now reads correct `b"\x03GGUF"` header (was `b"GGUF"`). Players with real Qwen2.5-7B models will no longer see silent load failure; magic mismatch now raises `LLMUnavailable` with explicit message.
- **detect_hardware() removed**: 4 difficulty tiers are now decoupled from hardware detection per Phase 3 decision N2. `app.proto.profile` module deleted; `from app.proto import *` no longer exports hardware-related symbols.

## Quality
- **21 historical F401 unused imports cleaned** (17 auto-fixed by `ruff --fix`, 4 manual). CI ruff now fails on lint errors (was `|| true`).
- **CI/CD infrastructure**: 4-job GitHub Actions workflow (web/api/shared/security), release workflow with tauri-action for 3-platform builds, dependabot weekly, CODEOWNERS, PR/issue templates, pre-commit hooks (ruff + gitleaks + yamllint + actionlint).
- **Vendor SHA256 verification script** (`scripts/verify_vendor.py`) added; all vendor resources now have `.sha256` checksum files.
- **Subdirectory READMEs** added for `apps/api`, `apps/web`, `apps/desktop`, `packages/shared` to onboard new developers faster.

## Testing infrastructure
- **L4 fixture optimization**: pytest fixtures switched to `min_size_mb=1` injection on `LocalLLMLoader`, reducing single-run pytest disk write from **15 GB → 0.6 GB** (25x reduction). Running the full 220-test suite no longer risks filling the C drive.
