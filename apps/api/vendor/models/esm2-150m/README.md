# ESM2-150M Model Weights

> Source: `facebook/esm2_t30_150M_UR50D`
> Mirrors used for download: `https://hf-mirror.com/facebook/esm2_t30_150M_UR50D/`

## Status

- [x] `model.safetensors` downloaded (567.7 MB on 2026-07-09)
- [x] Magic bytes / size check passed (passes `is_available()` threshold >= 500 MB)
- [ ] `config.json` and tokenizer files not vendored (Phase 1.5/2 will add when real `transformers.AutoModel` integration lands)

## Files

| File | Size | Status |
|---|---|---|
| `model.safetensors` | 567.7 MB | downloaded |

## SHA256 (full file)

`C3F1DA8AEA53BDDD32C246C86168C23B9FD72341FB9DB9A94436F855F5053566  model.safetensors`

(also written to `model.safetensors.sha256` for `sha256sum -c` style verification)

## License

ESM2 is released by Meta under the [ESM2 model license](https://huggingface.co/facebook/esm2_t30_150M_UR50D) — academic / non-commercial use.

## Loader

```python
from app.models.loader import ESM2Loader

loader = ESM2Loader()
print(loader.is_available())  # True after vendor
print(loader.try_load().size_bytes)  # ~595 MB
```

## Re-download (if needed)

```bash
# Direct HF (slow outside CN):
Invoke-WebRequest -Uri "https://huggingface.co/facebook/esm2_t30_150M_UR50D/resolve/main/model.safetensors" -OutFile apps/api/vendor/models/esm2-150m/model.safetensors

# CN mirror (verified 2026-07-09):
Invoke-WebRequest -Uri "https://hf-mirror.com/facebook/esm2_t30_150M_UR50D/resolve/main/model.safetensors" -OutFile apps/api/vendor/models/esm2-150m/model.safetensors
```

Expected size: **595,257,706 bytes** (567.7 MB) — under our 500 MB minimum threshold.
