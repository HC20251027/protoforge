//! Unit tests for ProtoForge Phase 3 Task 1.4 — Tauri sidecar layout.
//!
//! These tests are **placeholders** that verify the platform-aware
//! interpreter path returned by ``sidecar::sidecar_binary_path()``.
//!
//! They are intentionally *pure*: no Tauri AppHandle, no filesystem,
//! no network — they must run in any environment.
//!
//! NOTE: We do NOT run ``cargo test`` here on Windows (Rust toolchain
//! install + first build takes ~30 minutes, see Phase 3 plan).  The
//! tests exist as a hand-off contract for whoever picks up
//! ``cargo test`` next; CI / Linux can exercise them directly.

use protoforge_desktop_lib::sidecar;

#[test]
fn sidecar_path_is_non_empty() {
    let p = sidecar::sidecar_binary_path();
    assert!(!p.is_empty(), "sidecar path must not be empty");
    assert!(
        p.starts_with("binaries/python-bundle/"),
        "sidecar path must live under binaries/python-bundle/, got: {p}"
    );
}

#[test]
fn sidecar_path_matches_platform_convention() {
    let p = sidecar::sidecar_binary_path();
    if cfg!(target_os = "windows") {
        assert!(
            p.ends_with("python.exe"),
            "Windows sidecar must be .exe, got: {p}"
        );
    } else if cfg!(target_os = "macos") {
        assert!(
            p.ends_with("python"),
            "macOS sidecar must be a bare 'python' (no extension), got: {p}"
        );
        assert!(
            !p.contains("/bin/python"),
            "macOS layout is <root>/python, not <root>/bin/python"
        );
    } else {
        // Linux / other unix (PEP 394)
        assert!(
            p.ends_with("/bin/python"),
            "Linux sidecar must end with /bin/python (PEP 394), got: {p}"
        );
    }
}

#[test]
fn sidecar_runtime_path_includes_binary() {
    let runtime = sidecar::sidecar_runtime_path();
    let bin = sidecar::sidecar_binary_path();
    assert!(
        runtime.ends_with(bin),
        "runtime path must end with the binary path ({bin}), got: {runtime}"
    );
    assert!(
        runtime.starts_with("<game-dir>/"),
        "runtime path must be presented relative to <game-dir>, got: {runtime}"
    );
}

#[test]
fn sidecar_port_default_is_sane() {
    // Default port must be a non-zero ephemeral-range value.
    let port = sidecar::sidecar_port();
    assert!(port > 0, "sidecar port must be non-zero, got {port}");
    assert!(port < 65_536, "sidecar port must fit u16, got {port}");
    // And must equal the documented default.
    assert_eq!(
        port, sidecar::SIDECAR_API_PORT_DEFAULT,
        "default port should match SIDECAR_API_PORT_DEFAULT"
    );
}
