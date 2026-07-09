# Qwen2.5-7B-Instruct GGUF (Q4_K_M)

> Source: `Qwen/Qwen2.5-7B-Instruct-GGUF`
> Mirror used for download: `https://hf-mirror.com/Qwen/Qwen2.5-7B-Instruct-GGUF/`
> Fallback (direct HF, slow outside CN): `https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/`

## Status

- [x] `qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf` downloaded (3.72 GB on 2026-07-09)
- [x] `qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf` downloaded (0.64 GB on 2026-07-09)
- [x] Magic bytes / combined size check passed (passes `is_available()` threshold >= 3500 MB)
- [x] Full-file SHA256 captured in `qwen2.5-7b-instruct-q4_k_m.sha256` (sidecar, for `sha256sum -c` style verification)
- [ ] `llama-cpp-python` not installed (Phase 1.5/2 will add when real inference lands)

## Files

| File | Size | Status |
|---|---|---|
| `qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf` | 3,993,201,344 B (3.72 GB) | downloaded |
| `qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf` |   689,872,288 B (0.64 GB) | downloaded |
| **Total** | **4,683,073,632 B (4.36 GB)** | ready |

## SHA256 (full files)

```
DFCE12E3862A5283CCFB88221B48480E58745165DE856439950D0F22590580DB  qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf
539CF93F78E887EDEA1C04E2D7D8CDACA9D01DAE9C9025BCB8ACCBE29DF3D72A  qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf
```

(also written to `qwen2.5-7b-instruct-q4_k_m.sha256` for `sha256sum -c` style verification)

## Verify

```bash
# 在 apps/api 目录下
cd apps/api
sha256sum -c vendor/llm/qwen2.5-7b-instruct-q4_k_m.sha256

# PowerShell (Windows):
Get-FileHash vendor/llm/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf -Algorithm SHA256
Get-FileHash vendor/llm/qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf -Algorithm SHA256
```

## License

Qwen2.5 is released by Alibaba Cloud under the Apache 2.0 license:
https://huggingface.co/Qwen/Qwen2.5-7B-Instruct/blob/main/LICENSE

## Loader

```python
from app.llm.loader import LocalLLMLoader, LocalLLMProvider, LLMUnavailable

loader = LocalLLMLoader()
print(loader.is_available())         # True after vendor (>= 3.5 GB combined)
h = loader.try_load()
print(h.name, h.size_bytes // 1024 // 1024, "MB")  # qwen2.5-7b-instruct-q4-k-m 4466 MB

provider = LocalLLMProvider()
try:
    text = provider.chat([{"role": "user", "content": "hi"}])
except LLMUnavailable as exc:
    # llama-cpp-python 未安装,或权重缺失
    print("local LLM unavailable:", exc)
```

## Re-download (if needed)

```powershell
# CN mirror (verified 2026-07-09, ~4 MB/s):
# 注意:HF 上 Q4_K_M 现在是分片,两个分片都需要下
# 我们走"分片"路线 — loader 会自动合并大小判定
$ProgressPreference = 'SilentlyContinue'
Invoke-WebRequest -Uri 'https://hf-mirror.com/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf' -OutFile apps/api/vendor/llm/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf
Invoke-WebRequest -Uri 'https://hf-mirror.com/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf' -OutFile apps/api/vendor/llm/qwen2.5-7b-instruct-q4_k_m-00002-of-00002.gguf

# 可选:合并为单文件(让 llama-cpp-python 直接 load,不依赖分片)
# pip install llama-cpp-python
# llama-gguf-split merge vendor/llm/qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf vendor/llm/qwen2.5-7b-instruct-q4_k_m-merged.gguf
```

Expected total size: **4,683,073,632 bytes** (4.36 GB) — well above our 3.5 GB minimum threshold.

## Phase 1.5/2 接入 llama-cpp-python 真实推理

1. 取消 `pyproject.toml` 中 `llm` dependency-group 的注释
2. `uv sync --group llm` 安装(Windows 上首次编译需 10+ 分钟,需要 VS Build Tools)
3. 用 `llama-gguf-split merge` 把两个分片合并为单 GGUF,或保留分片让 loader 多文件 mode 工作
4. `LocalLLMProvider.chat()` 已经按 OpenAI 协议实现,直接可用
5. 前端 onboarding 页的 "local (Ollama / LM Studio)" 选项可以新增一个子项 "local (bundled GGUF)"

## 决策记录

- **N1.6 决策** (2026-07-09):本地 LLM 物理 vendor 落地即算 Task 1.3 完成,不要求 import 跑通
- 8-12GB 打包预算已 OK,玩家不主动点不会下载
- 引导页默认推荐 cloud (DeepSeek / OpenAI 兼容) — 用户原话"你本地模型的效果绝对不行",本地 LLM 是次选
- 推理引擎选 llama.cpp (llama-cpp-python 绑定) 而非 Ollama:零外部进程依赖,打包简单
