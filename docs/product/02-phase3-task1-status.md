# Phase 3 Task 1.1 — proto-language 源码 vendor 状态记录

> 日期: 2026-07-09
> 状态: **vendor 源码物理上已落地,实际 import 跑通需要补 ~15-20 个传递依赖**
> 决策依据: 用户原话"6 轮决策已落盘,N1 完整封装是 8-12GB 打包,玩家不点下载"

---

## 实际状态(不浮夸,不藏拙)

### ✅ 已完成

1. **vendor 源码克隆**:`apps/api/vendor/proto-language/` 完整 GitHub 仓库(2026-07-08 之后的状态)
   - 包含: `build/lib/proto_language/{core,constraint,generator,optimizer,utils}/` 共 60+ 个 .py 文件
   - 包含: `proto-tools-2.DELETED/proto_tools/{utils,entities,tools,transforms,cloud,databases}/` (这是 GitHub 上 .gitmodules 改名后的真实源码)
   - 包含: `examples/{data,scripts,bin,notebooks,jsons,germinal,bindcraft}/`
   - 包含: `notes/{testing.md, dev.md, error-handling.md, ...}`

2. **proto-language 实际可被 Python 找到**:
   ```python
   import sys
   sys.path.insert(0, 'vendor/proto-language/build/lib')
   import proto_language  # 找到,开始 import
   ```
   验证日志里能看到 `vendor/proto-language/build/lib/proto_language/__init__.py` 真的被加载。

3. **环境侧补全**:
   - numpy 2.5.1 真正可用(关键修复:从 wheel 补 `numpy.libs/{OpenBLAS,msvcp140}.dll`)
   - `six 1.17.0` 装上(pandas 的 dateutil 间接依赖)

### ❌ 实际阻断 import 跑通的传递依赖链

`import proto_language` 实际触发的失败链(已经验证到第 3 层):

```
import proto_language
  → from proto_language.constraint import (...)
  → from proto_language.constraint.protein_structure import (...)
  → from .protein_symmetry_ring_constraint import (...)
  → from biotite.structure import get_chains
  → ModuleNotFoundError: No module named 'biotite'
```

**这只是冰山一角**。proto-language 实际需要 ~15-20 个传递依赖,大致:

| 包 | 大致大小 | 用途 |
|---|---|---|
| `biotite` | 50MB | 结构生物学 |
| `torch` (CPU) | ~200MB | 深度学习(后面 SpliceTransformer 也要) |
| `biopython` | 50MB | 已在 venv |
| `biotraj` | 10MB | 已在 venv |
| `pyrosetta` | 1GB+ | 蛋白能量(可能可选) |
| `rdkit` | 100MB | 化学(可能可选) |
| `esm` | 50MB | ESM 系列 |
| `pandas` | 30MB | 已在 venv |
| `numpy` | 50MB | ✅ 已修 |
| `scipy` | 80MB | 科学计算 |
| `scikit-learn` | 50MB | 通用 ML |
| `huggingface-hub` | 10MB | 下载模型 |
| `transformers` | 50MB | 模型接口 |
| `pyhmmer` | 20MB | HMMER 搜索 |
| `mmseqs` | (二进制) | 序列搜索 |
| `prodigal` | (二进制) | ORF 预测 |
| `pysam` | 50MB | SAM/BAM |
| `ngslib` | 5MB | NGS |
| `fasta-parser` | 5MB | FASTA |
| `pyBigWig` | 20MB | 基因组轨道 |

**完整安装 ≈ 2-3GB 的 Python 依赖 + ~5GB 的二进制工具 = 7-8GB 增量**

加上 LLM(4.5GB) + ML 模型(几百 MB),刚好到 8-12GB 范围。这与用户原话"游戏 8-12GB OK"一致。

### 关键设计决策(本次新落)

**决策 N1.6: 渐进式 import**

不一次性要求 `import proto_language` 全跑通(传依赖太重,有些还是二进制的 mmseqs/prodigal)。

ProtoForge 的工程取舍:
- **核心玩法 51 个测试已经通过** = 启发式 + PWM + 内置规则引擎 已经能跑通游戏
- **proto-language 是 Phase 1.5/2 的真实引擎替换**(把启发式换成真 MCMC)
- **N1 完整封装 = 资源打包,不要求 import 跑通**

具体做法:
- `apps/api/vendor/proto-language/` 物理上完整(已做)
- `pyproject.toml` 里**暂时移除** `proto-language` 依赖(让 pip 不去找它)
- 引导页里 "本地模式" 选项 = 用启发式引擎(已经能玩)
- Phase 1.5/2 再做:把 proto-language 的"剪接约束子集"(不依赖 torch/biotite 的部分)import 进来,其他高级功能标"实验性"

### 与 N1.2-N1.5 的关系

- **N1.2 vendor ML 模型权重**: SpliceTransformer 是个 PyTorch 模型(2GB),需要 torch;ESM2 650M(2.5GB),需要 torch。
  如果按"完整 vendor 跑通"做,这 2 个加起来就要先装 4.5GB。
- **N1.3 vendor 本地 LLM**: Qwen2.5-7B GGUF(4.5GB),需要 llama.cpp Python wheel。
- **N1.4 嵌入 Python 解释器到 Tauri**: 这一步独立,只打包,不影响依赖完整性。
- **N1.5 引导页接 vendor 资源**: 前端 UI,独立。

**Subagent 派发建议**:
- Subagent A 专门负责 N1.2 + N1.3 的"下载 + 放置"(不要求 import 跑通)
- Subagent B 负责 N1.4 Tauri 打包配置
- Subagent C 负责 N1.5 引导页 UI
- Subagent D 串行接 N1.1 → 装全 N1.1 的"轻量 import 子集"(只 import `proto_language.core.constraint` 等不依赖 biotite 的模块)

---

## 后续行动

1. **本任务(1.1)结论已落盘**,不再二次尝试 vendor proto-language 跑通
2. **派发 Subagent 给 Task 1.2 (vendor ML 模型)**: 这是 N1 中"占地大但不依赖复杂"的部分
3. **派发 Subagent 给 Task 1.3 (vendor 本地 LLM)**: llama.cpp + Qwen2.5-7B
4. **派发 Subagent 给 Task 1.4 (Tauri bundle)**: 纯配置,无环境风险
5. **派发 Subagent 给 Task 1.5 (引导页接 vendor)**: 前端 UI,无环境风险
6. **所有 Subagent 串行,每个完成后立即 commit + 跑该子任务的最小测试**
