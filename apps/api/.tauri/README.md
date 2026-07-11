# apps/api/.tauri/

Tauri signing key 目录。

- `protoforge.key` - ed25519 私钥(本地生成,已通过 `apps/api/scripts/set_secret.py` 上传到 GitHub Secrets `TAURI_SIGNING_PRIVATE_KEY`,**不入 git**)
- 重新生成命令:`openssl genpkey -algorithm ed25519 -out protoforge.key` (或 `npx @tauri-apps/cli signer generate`)
- GitHub Actions release.yml 通过 `secrets.TAURI_SIGNING_PRIVATE_KEY` 读取,Windows / macOS / Linux 三平台 Tauri 安装包都自动签名
