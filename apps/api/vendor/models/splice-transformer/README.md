# SpliceTransformer-base Weights (placeholder)

> Source: biomap-research / SpliceTransformer — `https://github.com/biomap-research/SpliceTransformer`

## Status

- [ ] **NOT downloaded** — the project's GitHub repo was unreachable on 2026-07-09
  (multiple network retries on `https://github.com/biomap-research/SpliceTransformer` returned
  "connection closed" / 404 on the README fetch). The model checkpoints are not mirrored on
  HuggingFace under a stable path either; they are typically distributed via the project authors
  on request or via conference proceedings (NeurIPS 2024).

## Why we left this as a placeholder

Per the 2026-07-09 N1.6 decision, vendor directory + loader interface stay in place so Phase 1.5/2
can drop the actual weights in without any code change. Network access to upstream is unreliable
from the current environment, and the model is not strictly required for the Phase 3 gameplay loop
(HeuristicScorer + PWM + future real SpliceAI are sufficient).

## Expected file (when Phase 1.5/2 adds it)

| File | Size | Min threshold |
|---|---|---|
| `model.pt` (or `splice-transformer-base.ckpt`) | ~400 MB | >= 200 MB |

The loader currently accepts any of:

- `model.pt`
- `splice-transformer-base.ckpt`
- `pytorch_model.bin`

## License

SpliceTransformer is academic / non-commercial in its current public release. Check the upstream
repo's LICENSE before commercial redistribution.

## How to obtain the weights later

1. Reach out to the biomap-research team via GitHub issue
2. Or check the paper's supplementary materials (typically NeurIPS proceedings)
3. Once obtained, drop the file at `apps/api/vendor/models/splice-transformer/model.pt`

## Loader still works (returns `None` until weights are placed)

```python
from app.models.loader import SpliceTransformerLoader

loader = SpliceTransformerLoader()
print(loader.is_available())  # False (no weights yet)
print(loader.try_load())      # None
```
