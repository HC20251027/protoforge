---
'@protoforge/api': patch
---

# Phase 4 B1: Tauri 签名密钥 + GitHub Secret 工具链

## DevOps

- **`apps/api/scripts/set_secret.py`** - 用 libsodium (PyNaCl) SealedBox 加密 + GitHub REST API 设仓库 Secret。本地开发者配 `TAURI_SIGNING_PRIVATE_KEY` / `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` 一次的工具。CI release.yml 不依赖此脚本(用 `${{ secrets.* }}` 直接读)。
- **`apps/api/.tauri/README.md`** - Tauri 签名密钥目录说明。私钥 `*.key` / `*.key.pub` 通过新增的 `.gitignore` 规则不入 git,只能通过 `set_secret.py` 推到 GitHub Secrets。
- **pre-commit gitleaks 改 local hook** - 用本机或项目 `apps/api/.cache/bin/gitleaks.exe` 二进制跑(8.30.1,约 30 MB),不再拉 1GB+ docker 镜像。Windows + macOS + Linux 一致行为。
- **`pynacl>=1.6.2`** 加进 `apps/api/pyproject.toml` 的 `dev-dependencies`(只本地脚本需要,产品 bundle 不带)。
