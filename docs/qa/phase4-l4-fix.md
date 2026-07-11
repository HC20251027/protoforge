# Phase 4 L4 修复:测试不再写满 C 盘

> 日期: 2026-07-11
> commit: 400ade72 `test(llm): 注入 min_size_mb 阈值,跑一次 pytest 写盘从 15GB 降到 0.6GB`

## 问题

Phase 4 C 段跑 pytest 时,C 盘突然从 600GB 可用掉到 2.06GB,触发 `OSError: [Errno 28] No space left on device`。

定位后根因:

1. **pytest 测试 fixture 写真大文件**: 每个 case 调 `_make_fake_gguf(path, size_mb=3600)` 在 `tmp_path` 写出 3.6GB 假 GGUF 文件,为了触发产品 `LocalLLMLoader` 的 `min_size_mb=3500` 硬阈值。
2. **单次跑 pytest 写 15GB+**: 8 个 case × 3.6GB 单文件 + 多个分片场景 = 15GB 假文件落到 `C:\Users\32893\AppData\Local\Temp\pytest-of-32893\`。
3. **多次跑累加**: Phase 4 C 段跑过 3 次完整 pytest,3 × 15GB = 45GB 假文件残留。
4. **pytest 异常退出时残留不清理**: C 段最后一次 pytest 写满 C 盘后 OOM 退出,pytest 的 tmp_path 清理机制没机会跑,留下 19GB 假文件。

## 根因分析

- **产品代码本身没问题**: `LocalLLMLoader.min_size_mb = 3500` 是合理的硬阈值,真模型 Qwen2.5-7B 4.36GB 必须 >= 3500MB 才算"装好"。
- **测试设计有问题**: 测试代码在产品阈值下必须写真 4GB 假文件,不能 mock loader 阈值(原本 loader 阈值是类属性硬编码,无法注入)。
- **结果**: 测试与产品耦合在"必须写真大文件"上,每次跑都消耗玩家电脑 GB 级空间。

## 修法 (L4)

**`LocalLLMLoader.__init__` 接受可选参数 `min_size_mb`**,默认仍为 3500(产品行为零变化);测试代码显式构造 `LocalLLMLoader(min_size_mb=1)`,case 写 1-2MB 占位文件即可触发 `is_available()=True`。

### 关键变更

1. **`apps/api/app/llm/loader.py`** (+5 行)
   - `__init__` 加 `min_size_mb: int | None = None` 可选参数
   - 不传时仍用类属性默认 3500,产品代码 0 行为变化

2. **`apps/api/tests/test_local_llm.py`** (8 个 case 改)
   - `_make_fake_gguf` 默认 size_mb=1(1MB 占位)
   - 7 个 case 改用 `LocalLLMLoader(min_size_mb=1)` 注入低阈值
   - 1 个 case 用 `LocalLLMLoader.min_size_mb = 1` 临时改(走单例路径)

3. **`apps/api/tests/test_models_loader.py`** (3 个 case 改)
   - `_make_fake_safetensors/h5/pt` 默认 1-2MB
   - 3 个 case 用 `monkeypatch.setattr(ESM2Loader, "min_size_mb", 1)` 注入

4. **`apps/api/tests/conftest.py`** (新增 fixture)
   - `shared_fake_gguf` session-scope fixture 脚手架(本 commit 暂未使用,后续 case 改写时备用)

## 效果

| 指标 | L4 前 | L4 后 | 缩减 |
|---|---|---|---|
| 单次 pytest 写盘 | ~15 GB | **0.6 GB** | **25x** |
| 单次 pytest 用时 | 360s | 189s | 1.9x |
| pytest-of-32893 残留 | 47.6GB | **614 MB** | **77x** |
| 220 测试结果 | 220 pass | **220 pass** | 0 回归 |

## 验证

```
$ cd apps/api && uv run pytest -q
220 passed, 5 warnings in 188.78s (0:03:08)

$ du -sh /c/Users/32893/AppData/Local/Temp/pytest-of-32893
614 MB  (vs L4 前 47.6 GB)
```

## 历史背景

C 段前每个 case 写真 3600MB 假文件触发 3500MB 阈值,单次 pytest 写 15GB+ 假文件,反复跑把 C 盘顶到 2GB 触发 OSError。L4 改造后该根问题彻底消除,**玩家电脑再也不会被测试跑满**。

## 后续

- (低优) `apps/api/tests/conftest.py` 里的 `shared_fake_gguf` 脚手架暂未启用,如果未来还有 3600MB 占位 case 可以用
- (低优) `apps/api/tests/test_local_llm.py` 里 `test_real_vendor_dir_or_empty` 这种"测产品行为"的 case 仍用 `LocalLLMLoader()` 默认 3500,合理保留
