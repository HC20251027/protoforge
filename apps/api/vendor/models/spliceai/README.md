# SpliceAI Model Weights (placeholder)

> Source: Illumina SpliceAI — `https://github.com/Illumina/SpliceAI`
> Upstream distribution: academic pre-computed scores, NOT raw model checkpoints

## Status

- [ ] **NOT downloaded** — upstream SpliceAI does **not** ship model weights in the public GitHub repo.
  The trained `.h5` files are bundled inside the `spliceai` pip package (`spliceai/models/spliceai{1..5}.h5`),
  but the package's pre-computed scores are free for academic / non-commercial use, and the
  trained models for **commercial** redistribution require a license from Illumina.

## Why we left this as a placeholder

Per the 2026-07-09 N1.6 decision ("vendor 资源物理落地即完成任务"), we keep the directory and the
loader interface stable so Phase 1.5/2 can drop the actual weights in without code changes.
Installing the upstream `spliceai` package and copying the bundled `.h5` files is the only practical
path; we did **not** install `tensorflow` (~600 MB wheel) for this Phase 3 sub-task to keep the
sidecar's startup time below 3 seconds.

## Expected file (when Phase 1.5/2 adds it)

| File | Size | Min threshold |
|---|---|---|
| `SpliceAI_hg38_model.h5` (or `spliceai1.h5` ... `spliceai5.h5` if individual 5 sub-models) | ~50 MB (combined 250 MB) | >= 20 MB |

> If the 5 sub-models are kept separate, the loader's `min_size_mb` for `SpliceAI` must be lowered
> to ~10 MB per file (or we relax the heuristic to "at least one file >= 20 MB and total >= 50 MB").
> For now we keep the current single-file assumption to avoid over-engineering.

## License

Trained models are CC BY-NC 4.0 (academic / non-commercial). Commercial use requires a license from
Illumina (AI_licensing@illumina.com). ProtoForge ships the model only; users opt in during onboarding.

## How to obtain the weights later

```bash
# Option A: install upstream (requires tensorflow)
uv pip install spliceai
# Then locate the bundled .h5 files (typically inside the installed package directory)
python -c "import spliceai, os; d=os.path.dirname(spliceai.__file__); print(os.path.join(d, 'models'))"
# Copy them into apps/api/vendor/models/spliceai/ as SpliceAI_hg38_model.h5

# Option B: download pre-computed scores (academic license, NOT real-time inference)
#   from https://basespace.illumina.com/s/otSPW8hnhaZR  (registration required)
```

## Loader still works (returns `None` until weights are placed)

```python
from app.models.loader import SpliceAILoader

loader = SpliceAILoader()
print(loader.is_available())  # False (no weights yet)
print(loader.try_load())      # None
```

This is the intended graceful-degradation behavior — game uses `HeuristicScorer` until SpliceAI is
wired in.
