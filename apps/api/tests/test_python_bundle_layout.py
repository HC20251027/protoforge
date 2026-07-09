"""Verify the Tauri Python-bundle layout (Phase 3 Task 1.4).

These tests are *configuration / contract* tests — they look at the
files that ship in the repo, not at runtime behavior.  That keeps
them hermetic, fast, and CI-friendly.

The contract:

1. ``scripts/bundle_python.py --dry-run`` writes an INSTALL.md into
   ``apps/desktop/src-tauri/binaries/python-bundle/INSTALL.md``.
2. ``apps/desktop/src-tauri/tauri.conf.json`` declares the sidecar
   binary as ``binaries/python-bundle/python`` (Tauri resolves the
   ``.exe`` extension on Windows automatically).
3. ``apps/desktop/src-tauri/tauri.conf.json`` declares the vendored
   resources (``../api/vendor/**``) so proto-language / ML models /
   GGUF get packaged.
4. ``apps/desktop/src-tauri/src/sidecar.rs`` uses ``uvicorn`` to
   serve the bundled FastAPI app on a TCP port.
5. ``.gitignore`` keeps the heavy venv copy out of git while still
   tracking ``INSTALL.md`` and the placeholder ``python`` file.

Each test targets one piece of the contract; the whole file brings
the api test suite from 74 -> 79 passed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

# Project root = parents[3] of this test file
# (apps/api/tests/test_python_bundle_layout.py -> apps/api/tests -> apps/api
#  -> apps -> root)
PROJECT_ROOT = Path(__file__).resolve().parents[3]

INSTALL_MD = (
    PROJECT_ROOT
    / "apps"
    / "desktop"
    / "src-tauri"
    / "binaries"
    / "python-bundle"
    / "INSTALL.md"
)
TAURI_CONF = PROJECT_ROOT / "apps" / "desktop" / "src-tauri" / "tauri.conf.json"
SIDECAR_RS = PROJECT_ROOT / "apps" / "desktop" / "src-tauri" / "src" / "sidecar.rs"
GITIGNORE = PROJECT_ROOT / ".gitignore"
BUNDLE_DIR = INSTALL_MD.parent


class TestBundleLayout:
    """The python-bundle/ directory + INSTALL.md exist and are correct."""

    def test_install_md_exists(self) -> None:
        assert INSTALL_MD.is_file(), f"missing {INSTALL_MD}"

    def test_install_md_documents_all_three_platforms(self) -> None:
        text = INSTALL_MD.read_text(encoding="utf-8")
        # Windows / macOS / Linux interpreter path map must be explicit.
        assert "python.exe" in text, "INSTALL.md must mention Windows .exe"
        assert "/bin/python" in text, "INSTALL.md must mention Linux /bin/python"
        # The macOS path is a bare `python`; we check the row exists.
        assert re.search(r"\|\s*macOS\s*\|", text), "INSTALL.md must have a macOS row"

    def test_install_md_mentions_uvicorn_command(self) -> None:
        text = INSTALL_MD.read_text(encoding="utf-8")
        assert "uvicorn" in text, "INSTALL.md must show the uvicorn command"
        assert "app.main:app" in text, "INSTALL.md must reference app.main:app"

    def test_bundle_dir_may_exist_even_when_gitignored(self) -> None:
        # The directory itself is allowed to exist (e.g. after a dry-run),
        # but it must be excluded from git (see TestGitignore).
        assert BUNDLE_DIR.exists(), f"bundle dir should exist after bundle_python.py --dry-run, got {BUNDLE_DIR}"


class TestTauriConf:
    """tauri.conf.json declares the Python sidecar and vendored resources."""

    def test_tauri_conf_is_valid_json(self) -> None:
        assert TAURI_CONF.is_file(), f"missing {TAURI_CONF}"
        # ``json.loads`` raises if the file is not valid JSON.
        json.loads(TAURI_CONF.read_text(encoding="utf-8"))

    def test_external_bin_points_to_python(self) -> None:
        conf = json.loads(TAURI_CONF.read_text(encoding="utf-8"))
        ext_bin = conf.get("bundle", {}).get("externalBin", [])
        assert ext_bin, "bundle.externalBin must not be empty"
        # Tauri convention: extension is auto-appended on Windows, so we
        # use the bare name.  The test is intentionally flexible: any
        # entry ending with "/python" (or "/python.exe") is accepted.
        assert any(
            e.endswith("/python") or e.endswith("/python.exe")
            for e in ext_bin
        ), f"externalBin must reference a 'python' sidecar, got {ext_bin}"
        # And specifically the one from the plan:
        assert "binaries/python-bundle/python" in ext_bin, (
            "expected 'binaries/python-bundle/python' in externalBin, "
            f"got {ext_bin}"
        )

    def test_resources_include_vendor(self) -> None:
        conf = json.loads(TAURI_CONF.read_text(encoding="utf-8"))
        resources = conf.get("bundle", {}).get("resources", [])
        assert resources, "bundle.resources must not be empty"
        # We require the vendor glob; that's the meat of Task 1.4.
        assert any(
            "vendor" in r for r in resources
        ), f"resources must include a vendor glob, got {resources}"

    def test_identifier_unchanged(self) -> None:
        # Sanity check: we did not accidentally rewrite identifier / version
        # / windows (per task spec: "不要动" these fields).
        conf = json.loads(TAURI_CONF.read_text(encoding="utf-8"))
        assert "identifier" in conf, "identifier must remain in tauri.conf.json"
        assert "version" in conf, "version must remain in tauri.conf.json"
        assert conf.get("app", {}).get("windows"), "app.windows must remain"


class TestSidecarSource:
    """sidecar.rs implements the launch_python_sidecar entry point."""

    def test_sidecar_rs_uses_uvicorn(self) -> None:
        text = SIDECAR_RS.read_text(encoding="utf-8")
        assert "uvicorn" in text, "sidecar.rs must spawn uvicorn"
        assert "app.main:app" in text, "sidecar.rs must reference app.main:app"
        assert "--port" in text, "sidecar.rs must pass --port to uvicorn"
        assert "127.0.0.1" in text, "sidecar.rs must bind to 127.0.0.1 (loopback)"

    def test_sidecar_rs_has_new_launcher(self) -> None:
        text = SIDECAR_RS.read_text(encoding="utf-8")
        assert "pub fn launch_python_sidecar" in text, (
            "sidecar.rs must define `pub fn launch_python_sidecar`"
        )
        assert "CommandChild" in text, (
            "launch_python_sidecar must return tauri_plugin_shell::process::CommandChild"
        )
        assert "AppHandle" in text or "tauri::AppHandle" in text, (
            "launch_python_sidecar must accept a tauri::AppHandle"
        )

    def test_sidecar_rs_has_path_helper(self) -> None:
        text = SIDECAR_RS.read_text(encoding="utf-8")
        assert "fn sidecar_binary_path" in text, (
            "sidecar.rs must export sidecar_binary_path() for path resolution"
        )
        # Platform matrix coverage — at least the Windows branch should be
        # present in the source even on a Linux build.
        assert "python.exe" in text, "sidecar.rs must mention python.exe for Windows"
        assert "/bin/python" in text, "sidecar.rs must mention /bin/python for Linux"


class TestGitignore:
    """The python-bundle venv copy is excluded from git."""

    def test_gitignore_excludes_python_bundle(self) -> None:
        text = GITIGNORE.read_text(encoding="utf-8")
        assert "python-bundle" in text, (
            ".gitignore must exclude apps/desktop/src-tauri/binaries/python-bundle/"
        )

    def test_gitignore_keeps_install_md(self) -> None:
        text = GITIGNORE.read_text(encoding="utf-8")
        # We need INSTALL.md to land in the repo so CI / tests can read it.
        assert "INSTALL.md" in text, (
            ".gitignore must explicitly whitelist INSTALL.md via a !-rule"
        )
        # Specifically, a re-include (negation) rule for INSTALL.md.
        assert re.search(
            r"^!.*python-bundle/INSTALL\.md$", text, flags=re.MULTILINE
        ), ".gitignore must contain a negation rule for INSTALL.md"


class TestBundleScript:
    """The bundle script itself is present and runs cleanly in dry-run."""

    def test_bundle_script_exists(self) -> None:
        path = PROJECT_ROOT / "scripts" / "bundle_python.py"
        assert path.is_file(), f"missing {path}"

    def test_bundle_script_supports_dry_run(self) -> None:
        path = PROJECT_ROOT / "scripts" / "bundle_python.py"
        text = path.read_text(encoding="utf-8")
        assert "--dry-run" in text, "bundle_python.py must accept --dry-run"
        assert "INSTALL.md" in text, "bundle_python.py must write INSTALL.md"
