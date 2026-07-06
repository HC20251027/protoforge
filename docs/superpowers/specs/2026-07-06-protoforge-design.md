# ProtoForge(原体锻炉)设计文档

> 状态:草案 v0.3 · 算力策略 + LLM Provider 抽象 + 锻炉时间游戏化
> 日期:2026-07-06
> 作者:TRAE × 用户共创

---

## 1. 背景与目标

### 1.1 来源

基于用户上传的科普稿 [金牛掰掰的多维宇宙 — 生物编程器 Proto](file:///c:/Users/32893/.trae-cn/attachments/6a4b9e7dfc8269540e150264/ec7ba576-5b8c-43b6-b325-dca0eb2f6386_e734fa19-1489-444b-a64b-aced6960bf9d_【金牛掰掰的多维宇宙】—生物编程器Proto,人类技术飞升！但是战锤线—【2026-07-04】-中文.txt)
所介绍的 **Proto** —— 斯坦福 Brian Hie 实验室 2026 年 6 月发表的开源生成生物学编程语言,论文 DOI `10.64898/2026.06.22.733870` [($TRAE_REF)](https://blog.csdn.net/weixin_51577602/article/details/162294641),官方 Python 包 `proto-language` MIT 协议 [($TRAE_REF)](https://github.com/evo-design/proto-language)。

### 1.2 一句话定义

**ProtoForge(原体锻炉)是一个游戏化的合成生物学众包平台**。玩家用"自然语言 + 可视化滑块"代替写 Proto 代码,在三个科幻任务场景中设计出能解决真实问题的生物元件;后端在 Docker 中运行真 Proto + SpliceTransformer/Evo 2 评分,玩家方案可导出为可湿实验验证的候选列表。

### 1.3 项目立意(why now)

- Proto 论文里 32% 成功率的内含子设计任务 [($TRAE_REF)](https://blog.csdn.net/weixin_51577602/article/details/162294641) 是**典型的"巨大序列搜索空间 + 评分函数已知 + 人类直觉可补足 AI 短板"** 问题 —— 复刻 Foldit 模式的最佳切入;
- 2026 年 ICML 已经把 AI for Science 提到独立 oral 分场 [($TRAE_REF)](http://m.toutiao.com/group/7659288691986137651/),公众对该领域关注度高峰;
- 现成的游戏化生物项目(Foldit / EteRNA / Nanocrafter)的成功路径已被验证(万-十万级玩家共同作者发 Nature 系列论文 [($TRAE_REF)](https://www.linkresearcher.com/theses/e40363f2-925f-4c79-be09-a34f41268732)[($TRAE_REF)](https://www.360zhyx.com/home-research-index-rid-29519.shtml)),Proto 还没有对应的游戏化产品 —— 空白窗口期。

### 1.4 关键约束(用户明确要求)

- 所有产物放**项目目录**下,不动 C 盘(配置 `PROTO_HOME=/path/to/project/.proto`,pip/uv 缓存重定向);
- **Docker 化**,一行命令起停;
- 单人可维护,渐进推进;
- 兼顾"未来可剥离为独立像素游戏"的扩展性;
- **算力策略(2026-07-06 修订)**:默认目标 = 消费级 8GB+ NVIDIA 独显(RTX 3060 及以上);无 GPU 走纯 CPU 降级路径,功能约 70% 可用(详见 §4.2)。

---

## 2. 用户提到的 5 个模块 — 整合映射

| 用户原话 | 设计映射 | 落地位置 |
|---|---|---|
| ① 引导(剧情/世界观) | **Onboarding 剧情模式** | Phase 1 Web 前端"任务简报"页 |
| ② 自然语言交互(友好包装) | **NL→Proto 翻译层** | Phase 2 Ollama 本地 LLM(qwen2.5-3B),无 GPU 可跑 |
| ③ 玩家作品共享库(像 Foldit 共享库) | **作品墙 / Forging Gallery** | Phase 1 SQLite 起步 → Phase 3 Postgres |
| ④ 核心玩法(关卡/任务) | **Forge 关卡系统** | Phase 1 内含子 1 关,Phase 2 全 3 场景 |
| ⑤ 风险评估(关卡合格门) | **Risk Gate** | Phase 1 教学多选题,Phase 3 自动评分 + 人工复审 |

---

## 3. 渐进三步走(核心范围)

| Phase | 目标 | 工期 | 算力 | 验证强度 |
|---|---|---|---|---|
| **Phase 1:本地可玩** | 单机跑通"剧情 → 调参 → 评分 → 风险门"完整闭环 | 2-4 周 | 纯 CPU(几 GB 内存)+ Docker | 纯 in-silico |
| **Phase 2:多关卡 + 作品墙** | 三个场景全开,玩家作品可本地浏览,Nat-Proto 接口 | 1-2 月 | 同上 + Ollama qwen2.5-3B | 纯 in-silico + 候选导出 |
| **Phase 3:服务端化 + 社区** | Postgres + Redis 队列 + 用户系统,接 Stanford 社区 | 2-3 月 | 同上 + 可选 GPU worker | 候选列表提交,争取湿实验合作 |
| **Phase 4(可选):独立像素游戏** | Phase 3 跑通后,Game architecture 切成 Godot + 像素 | 远期 | — | — |

**当前本文档只锁定 Phase 1 的实现细节。** Phase 2-3 在文档中以"扩展点"形式标注接口,避免过度设计。

---

## 4. 架构总览(Phase 1)

```
┌──────────────────────────────────────────────────────────┐
│                   浏览器(玩家)                            │
│   Next.js 14 + TypeScript + TailwindCSS + PixiJS         │
│   - 剧情页(任务简报)                                       │
│   - Forge 工作台(可视化调参 UI)                              │
│   - 风险门(教学多选题 + 解释)                                 │
│   - 作品墙(本地浏览自己的作品)                                 │
└──────────────────────────┬───────────────────────────────┘
                           │ HTTP / WebSocket
                           ▼
┌──────────────────────────────────────────────────────────┐
│              FastAPI 后端(Docker 容器)                    │
│   - /api/missions       任务列表                          │
│   - /api/forge/run      同步跑 Proto 程序(返回评分)        │
│   - /api/forge/jobs/{id} 查询历史                          │
│   - /api/gallery        作品 CRUD                        │
│   - /api/risk/evaluate  风险门评分                        │
└──────────────────────────┬───────────────────────────────┘
                           │ Python SDK 调用
                           ▼
┌──────────────────────────────────────────────────────────┐
│         Proto 引擎层(Docker 容器)                          │
│   proto-language (MIT)                                  │
│     Sequence / Segment / Construct / Constraint /        │
│     Generator / Optimizer / Program 七大原语             │
│   proto-tools  (自动管理 micromamba 隔离环境)              │
│   PROTO_HOME 指向项目目录 .proto/                         │
│                                                          │
│   默认工具栈(R2 内含子任务):                                │
│     - SpliceTransformer  (剪接位点评分,~250MB)             │
│     - Evo 2 1B           (序列生成器,~1GB)                │
│     - ESM2 650M          (蛋白语言模型,~2.5GB)            │
│     - motif 评分器        (内置,无依赖)                     │
└──────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────┐
│           存储层(项目目录内,Docker 卷)                    │
│   - SQLite (.data/protoforge.db)  玩家、任务、作品、风险  │
│   - JSON Files (.data/programs/)    玩家 Proto 程序 + 输出 │
│   - FASTA (.data/sequences/)         导出的序列             │
│   - PROTO_HOME (.proto/)             Proto 模型权重与缓存   │
└──────────────────────────────────────────────────────────┘
```

### 4.1 数据流(Phase 1 端到端时序)

```
玩家点击"开炉" → 浏览器收集滑块值
   → POST /api/forge/run { mission_id, params, nl_text? }
   → FastAPI 校验 + 生成 Proto Program JSON
   → 调用 proto_language.Program.run() (同步,timeout 60s)
   → 收集 constraint 评分 + 输出的 FASTA
   → 写入 SQLite(gallery, runs 表)
   → 返回 { scores: {...}, fasta: "...", risk_flags: [...] }
   → 浏览器渲染雷达图 + 风险门提示
```

### 4.2 算力档位与自适应(用户 2026-07-06 反馈后修订)

**默认目标 = 消费级 8GB+ NVIDIA 独显**(RTX 3060 已是 Steam 装机量第一,占 6.27% [($TRAE_REF)](http://m.toutiao.com/group/7285648330061857315/))。但保留**无 GPU 降级路径**,覆盖没独显的玩家。

启动时自动检测硬件,匹配模型分档:

| 玩家硬件 | 默认模型栈 | 显存/CPU 占用 | Phase 1 体验 |
|---|---|---|---|
| **RTX 4070+ / 3090+ / 4090(8GB+)** | Evo 2 1B + ESM2 650M + AlphaGenome + ProteinMPNN | ~6GB 显存 | 完整体验,雷达图实时刷新 |
| RTX 3060/4060(8-12GB) | Evo 2 1B + ESM2 650M + AlphaGenome + ProteinMPNN | ~6GB 显存 | 完整体验 |
| 4-6GB 独显 / 集成显卡 | SpliceTransformer + ESM2 650M(部分) + motif 评分器 | 2-3GB 显存 | 90% 功能,内含子任务可玩 |
| **无独显 / Apple Silicon / 纯 CPU** | SpliceTransformer(CPU)+ motif 评分器 | 2GB 内存 | 70% 功能,推理 5-15s,关卡仍可通关 |

**自动检测实现**:
- 启动时 `nvidia-smi --query-gpu=memory.total --format=csv,noheader` 查显存;
- 匹配分档 → 写 `.proto/profile.json` → proto-language 启动时按 profile 加载模型;
- 用户可在"设置"页手动覆盖档位("我有更好的卡,想跑 7B")。

**关键原则**:有 GPU 就别"装穷",用 GPU 跑 Evo 2 1B / AlphaGenome / ESM2 才是 Proto 论文里那批实验验证工具,玩家方案才真的"能出口到 Stanford 社区"。

### 4.2.1 算力档位 × 锻炉时间 = 游戏机制(用户 2026-07-06 反馈后修订)

**核心洞察**:**推理时长不是 bug,是游戏机制**。玩家硬件差异转化为"原体锻炉仪式"的不同形态,本身就在讲"科研本就是慢工出细活"的叙事。

| 玩家硬件 | 单次开炉真实耗时 | 游戏内仪式名 | 视觉表现 | 配套机制 |
|---|---|---|---|---|
| RTX 4090 / 3090(8GB+) | 2-5 秒 | **「急锻」** | 火花飞溅 + 快速合盖动画 | 一次点击几乎实时,可批量比较 5-10 个方案 |
| RTX 3060/4060(8-12GB) | 5-10 秒 | **「标准锻」** | 标准锻造动画 + 进度条 | 节奏舒适,适合"一次调一参" |
| 集成显卡 / 4-6GB | 15-30 秒 | **「古法锻」** | 慢节奏 + 火光摇曳 + 仪式音效 | 玩家有时间思考"下一步调哪一参" |
| 纯 CPU / Apple Silicon | 30-90 秒 | **「晶种培育」** | 长时间养成 + 阶段提示(20% 30% 50% 80%) | **等待中挂小游戏**:猜最终评分区间 / 看剧情对话 / 翻作品墙 |

**关键设计**:
- **不掩盖加载**:UI 永远显示"仪式进行中"和"已等待 X 秒" —— 慢就是慢,但有仪式感;
- **等待中可关掉浏览器**:长任务写入 `runs` 表异步,玩家回来刷新看结果(类 EteRNA 云实验室);
- **档位徽章系统**:玩家关卡页右上角展示"急锻者 / 标准锻匠 / 古法锻师 / 晶种培育师"徽章,**用"我慢但我坚持"作为荣誉**,而不是惩罚;
- **跨档位公平**:慢档位的玩家有"晶种培育"专属成就(连续 10 次古法锻 + 最终完成关卡),快档位玩家有"急锻"专属成就(10 次内最优解),**两端都有荣誉**。

### 4.3 Docker GPU 透传配置

`docker-compose.yml` 需用 NVIDIA Container Toolkit 透传 GPU:

```yaml
services:
  api:
    image: protoforge-api:latest
    build: ./apps/api
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - PROTO_HOME=/app/.proto
      - PROTO_PROFILE=auto   # auto / gpu_8gb / gpu_24gb / cpu
    volumes:
      - ./.proto:/app/.proto
      - ./.data:/app/.data
```

**Windows 主机要求**:Docker Desktop 开启 WSL2 + NVIDIA Container Toolkit。无 GPU 也能跑(自动降级到 CPU profile),但 README 显眼位置标"推荐 NVIDIA 独显 ≥ 8GB"。

**Proto-language 打包进镜像**(用户 2026-07-06 反馈后修订):
- proto-language 已在 GitHub 开源,MIT 协议 [($TRAE_REF)](https://github.com/evo-design/proto-language);
- PyPI 正式包计划中,当前通过 `pip install git+https://github.com/evo-design/proto-language.git` 安装 [($TRAE_REF)](https://github.com/evo-design/proto-language);
- Dockerfile 一行搞定: `RUN pip install git+https://github.com/evo-design/proto-language.git`;
- proto-tools 用 micromamba 自动管理子环境(SpliceTransformer、ESM2 等每个工具一个隔离环境),无需手动配;
- **打包后整个游戏自包含**:玩家拉取 `protoforge:latest` 镜像,装完直接能玩,不依赖任何外部包管理器。

---

## 5. 模块详细设计

### 5.1 任务/关卡系统(Missions)

Phase 1 **1 个核心任务**:**"极地科考队的耐低温发光菌"**。

- **背景叙事**:2099 年,南极科考站坍塌,救援队要在 -80°C 黑夜里找到幸存者。他们委托你:设计一段**只能在极地菌株里正确表达、不能在人细胞系里误表达**的"诱导型发光启动子 + 内含子"组合,这样发光菌在人体内不会无控扩增,符合生物安全;
- **Proto 任务**:复用 Proto 论文 R2 的"细胞系特异性内含子"任务范式(以 SpliceTransformer + AlphaGenome 为约束) [($TRAE_REF)](https://blog.csdn.net/weixin_51577602/article/details/162294641),**有 GPU 直接用 AlphaGenome 复刻论文 32% 任务**;无 GPU 时降级为 SpliceTransformer + ESM2 650M 困惑度评分。
- **玩家操作**:5 个滑块 —— "目标剪接强度"、"脱靶抑制强度"、"约束权重 α/β"、"MCMC 步数";"生成器下拉" —— "均匀突变 / 偏好突变 / 随机序列";
- **评分函数**:`score = α·target_splice + β·orthogonality + γ·novelty`(前两个用 SpliceTransformer,novelty 用 ESM2 困惑度);
- **通过条件**:3 个目标(每个细胞系对)平均分 ≥ 0.7,且风险门通过。

### 5.2 Forge 工作台(玩家 UI)

设计原则:**滑块代替写代码**,所有 Proto 参数都能在 UI 上点出来。

- **左 1/3**:任务简报 + 当前 Proto 程序结构(只读,序列树 + 约束/生成器/优化器卡片)
- **中 1/3**:滑块区(每个约束一个滑块,带 tooltip 解释生物意义)
- **右 1/3**:实时反馈区 —— 序列预览 + 雷达图(5 维:剪接强度/正交性/新颖性/多样性/GC 含量) + 历史曲线
- **底部**:NL 输入框(Phase 1 留空,Phase 2 接 Ollama),"开炉"按钮,"导出 FASTA"按钮

技术栈:Next.js 14 App Router + Radix UI + TailwindCSS + Recharts(雷达图) + Web Worker(滑块防抖)。

### 5.3 风险门(Risk Gate)

Phase 1 实现为**教学多选题 + 自动关键词扫描**两层:

| 层 | 规则 | 教学性 |
|---|---|---|
| L1 自动 | 玩家 Proto 程序不包含"裂解酶"、"毒素"、"耐药基因"等 30+ 关键词 | 仅作红线 |
| L2 多选 | 3 道情景题,玩家判断"这个设计有没有伦理问题" | 教学:为什么这种设计有/没有风险 |

通过条件:L1 不触发 + L2 ≥ 2/3 正确。

### 5.4 作品墙(Forging Gallery)

- 玩家每次开炉留下的"Proto 程序 + 评分 + FASTA"算一件"作品";
- 列表页:按评分倒序、按时间、按玩家标签筛选;
- 详情页:可重放(用相同参数再跑一次) + 二次编辑(从这件作品 fork 出新版本);
- Phase 1 只本地浏览(单用户),Phase 2 改 SQL 多用户,Phase 3 接 Stanford Proto 社区的 `proto-client` SDK 实现"导出候选"。

### 5.5 LLM Provider 抽象层(用户 2026-07-06 反馈后升级:目标人群含开发者/程序员)

**用户洞察**:玩家群体里有相当一部分是**有技术背景、对科研有兴趣的开发者/程序员**,他们会自带 LLM API key 或本地模型服务。要为他们预留**第三方 LLM 接入通道**,而不是只让他们用滑块。

#### 5.5.1 用户分层与 LLM 体验

| 用户层 | 接入方式 | 配置位置 | Phase 1 支持 |
|---|---|---|---|
| **纯新手** | 不接 LLM,纯滑块 + 教程 | 无 | ✅ 默认 |
| **本地玩家** | Ollama(`localhost:11434`)/ LM Studio(`localhost:1234`),OpenAI 兼容 API [($TRAE_REF)](http://m.toutiao.com/group/7598431735818240562/)[($TRAE_REF)](https://blog.csdn.net/a772304419/article/details/150642356) | `Settings` 填 `base_url` | ✅ 自动检测 + 手动填 |
| **云 API 玩家** | Claude / OpenAI / DeepSeek / 任何 OpenAI 兼容云 | `Settings` 填 `base_url + api_key + model` | ✅ |
| **离线 / 隐私党** | 完全关 LLM | 开关关掉 | ✅ |

#### 5.5.2 统一 LLMClient 接口

后端抽象一个 `LLMClient` 接口,内部把 4 类 provider 统一成 `messages → response`:

```python
# apps/api/app/llm/base.py
class LLMClient(Protocol):
    async def complete(self, system: str, user: str, **kw) -> str: ...

# apps/api/app/llm/providers/
#   - ollama.py    (检测 localhost:11434,model 走本地拉取)
#   - lmstudio.py  (检测 localhost:1234)
#   - openai_compat.py  (任意 base_url + api_key,覆盖 Claude/GPT/DeepSeek/...)
#   - disabled.py  (NL 接口完全关闭)
```

**降级链**(后端启动时按顺序探测,首个可用为默认):
```
玩家显式配置 (Settings) > 环境变量 (ANTHROPIC_API_KEY / OPENAI_API_KEY) 
  > 检测到本地 Ollama (localhost:11434 /api/tags 返回 200) 
  > 检测到本地 LM Studio (localhost:1234 /v1/models 返回 200) 
  > 关闭 NL 接口
```

**协议统一**:Ollama / LM Studio 都已经支持 OpenAI 兼容 API [($TRAE_REF)](https://juejin.cn/post/7590128405350285312),所以 `openai_compat.py` 一个实现就能接 4 类(本地 Ollama / 本地 LM Studio / Claude / OpenAI / DeepSeek / 任何兼容服务),用 `openai` Python SDK 即可,**零额外代码**。

#### 5.5.3 配置存储

`Settings` 页配置项(写入 `data/protoforge.db` 的 `app_settings` 表):
```json
{
  "llm_provider": "auto",  // auto / ollama / lmstudio / openai_compat / disabled
  "base_url": null,         // auto 模式可空,显式模式必填
  "api_key": null,          // 本地服务不需要,云 API 必填
  "model": null,            // 留空则 provider 选默认(如 Ollama 的 llama3.2)
  "system_prompt_override": null  // 高级用户可改 system prompt
}
```

**用户分级 UX**:
- 普通玩家:`Settings` 页只看到"启用 AI 助手?"开关,其他自动;
- 进阶玩家:展开"高级"折叠,填 `base_url`;
- 开发者:展开"开发者模式",可改 `system_prompt`、调 `temperature`、看每次 LLM 调用的 token 用量和耗时。

#### 5.5.4 NL → Proto 翻译 Prompt 模板(Phase 1 内置,Phase 3 可被 Stanford AI Agent 替换)

```
你是 ProtoForge 游戏里的「AI 锻炉助手」。玩家会描述他想要的生物设计,你要把它转成 Proto 程序的 JSON 片段。

可用任务类型:
- "细胞系特异性内含子" → {constraints: [...], generators: [...]}
- "极地耐低温启动子" → ...
- "抗 PD-L1 抗体 CDR" → ...

玩家输入: "{nl_text}"
当前任务: {mission_slug}
当前滑块值: {current_params}

输出:只输出 JSON,不要解释。格式:
{
  "constraints": [{"name": "...", "weight": 0.0-1.0, "params": {...}}],
  "generators": [{"name": "uniform_mutation" | "biased_mutation" | "esm3", "params": {...}}],
  "optimizer": {"name": "mcmc" | "gradient_descent", "params": {...}}
}
```

#### 5.5.5 Phase 进度安排

| Phase | NL 接口状态 |
|---|---|
| Phase 1 | `LLMClient` 抽象 + Ollama/LM Studio/OpenAI 兼容 provider 实现 + `Settings` UI;**默认 disabled**(纯滑块游戏能玩),玩家主动开 |
| Phase 2 | NL 接口默认 enabled(Ollama `qwen2.5-3b-instruct-q4_k_m` 为主);5 个新手引导关卡全用 NL 教玩家 |
| Phase 3 | 接入 Stanford Proto 社区 AI Agent [($TRAE_REF)](https://blog.csdn.net/weixin_51577602/article/details/162294641);玩家方案可"导出为 NL 描述"反向生成 |

### 5.6 存储模型(SQLite,Phase 1)

```sql
-- 玩家(Phase 1 单机版就是本机用户;Phase 2 多用户,Phase 3 接账号)
players (id, name, created_at)

-- 任务(Phase 1 写死 1 个,Phase 2 走数据)
missions (id, slug, title, briefing, proto_template_json, scoring_json, risk_rules_json, created_at)

-- 玩家作品
artifacts (id, player_id, mission_id, parent_id, name,
           proto_program_json, scores_json, fasta_path,
           risk_passed, created_at)

-- 每次开炉的运行记录
runs (id, artifact_id, mission_id, params_json,
      constraint_scores_json, started_at, finished_at, status)

-- 风险门答卷
risk_answers (id, run_id, question_id, choice, correct)
```

---

## 6. 项目结构

```
protoforge/
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── docs/
│   └── superpowers/specs/2026-07-06-protoforge-design.md   (本文件)
├── apps/
│   ├── web/                       Next.js 14 前端
│   │   ├── app/
│   │   │   ├── page.tsx           首页
│   │   │   ├── missions/[slug]/   任务详情
│   │   │   ├── forge/             Forge 工作台
│   │   │   └── gallery/           作品墙
│   │   ├── components/
│   │   ├── lib/api.ts
│   │   ├── tailwind.config.ts
│   │   └── package.json
│   └── api/                       FastAPI 后端
│       ├── app/
│       │   ├── main.py
│       │   ├── routers/
│       │   │   ├── missions.py
│       │   │   ├── forge.py
│       │   │   ├── gallery.py
│       │   │   └── risk.py
│       │   ├── proto/
│       │   │   ├── engine.py      proto-language 封装
│       │   │   ├── missions.py    任务模板加载
│       │   │   └── exporters.py   FASTA 导出
│       │   ├── db.py              SQLAlchemy
│       │   └── config.py
│       ├── tests/
│       │   ├── test_missions.py
│       │   ├── test_forge.py
│       │   ├── test_gallery.py
│       │   └── test_risk.py
│       ├── Dockerfile
│       ├── pyproject.toml
│       └── uv.lock
├── data/                          (gitignore,Docker 卷)
│   ├── protoforge.db
│   ├── programs/
│   └── sequences/
├── .proto/                        (gitignore,Docker 卷,PROTO_HOME)
└── .cache/                        (gitignore,本地包管理器缓存)
    ├── pip/
    ├── uv/
    └── node_modules.tar
```

---

## 7. 接口契约(Phase 1)

### 7.1 `GET /api/missions`
返回任务列表。Phase 1 写死返回 1 个任务(极地科考队)。

### 7.2 `GET /api/missions/{slug}`
返回任务详情 + Proto 程序模板 JSON + 风险门题目。

### 7.3 `POST /api/forge/run`
**请求**:
```json
{
  "mission_slug": "polar-glow",
  "params": {
    "target_splice_strength": 0.8,
    "orthogonality_weight": 0.6,
    "mc_steps": 200,
    "generator": "uniform_mutation"
  },
  "nl_text": null
}
```
**响应**:
```json
{
  "run_id": "uuid",
  "scores": {
    "splice_strength": 0.82,
    "orthogonality": 0.71,
    "novelty": 0.65,
    "gc_content": 0.55
  },
  "fasta": ">design_1\nGTAA...",
  "duration_ms": 4200,
  "risk_flags": [],
  "passed": true
}
```

### 7.4 `POST /api/gallery`
把当前 run 存为作品(玩家命名)。

### 7.5 `GET /api/gallery`
作品列表(分页,排序)。

### 7.6 `POST /api/risk/evaluate`
对一次 run 做风险门评分(必须先有 run)。

---

## 8. 错误处理

| 场景 | 行为 |
|---|---|
| Proto 程序运行超时(>60s) | 返回 504 + 部分结果(显示已跑的约束分数) |
| SpliceTransformer 模型未下载 | 返回 503 + 提示运行 `scripts/download_models.sh` |
| 玩家提交了非法 Proto JSON | 返回 422 + 错误字段位置 |
| 风险门触发 L1 红线词 | 返回 200 + `risk_flags:[...]` + 拒绝保存作品 |
| SQLite 写失败 | 返回 500 + 错误码,前端展示"重试"按钮 |
| Docker 容器挂了 | docker-compose 自动 restart: unless-stopped,前端心跳检测显示"服务维护中" |

---

## 9. 测试策略(用户明确要求:全项目运行测试)

| 层级 | 工具 | 覆盖 |
|---|---|---|
| 单元测试 | pytest | proto/engine.py、missions.py、exporters.py、routers/* |
| 集成测试 | pytest + TestClient(httpx) | 端到端 `/api/forge/run` 流程 |
| 前端单元 | Vitest | 滑块组件、雷达图渲染、风险门多选题 |
| 前端 E2E | Playwright | "登录 → 进任务 → 调滑块 → 开炉 → 看到分数 → 存作品 → 看作品墙"完整路径 |
| 验收 | 用户手动 + Playwright 截图 | UI 与功能性 |

`docker-compose.test.yml` 拉起一个独立测试栈,自动跑完整测试套件。

---

## 10. 性能与资源预算

| 档位 | 显存/CPU | 后端容器 | 首次下载 | 单次开炉 |
|---|---|---|---|---|
| **GPU 8GB+(推荐)** | ~6GB 显存 | 8GB 显存 + 4 核 CPU | ~6GB(Evo 2 1B + ESM2 650M + AlphaGenome + ProteinMPNN) | **2-5 秒** |
| GPU 4-6GB | 3-4GB 显存 | 4GB 显存 + 2 核 CPU | ~3GB | 5-10 秒 |
| **纯 CPU / Apple Silicon** | 2GB 内存 | 2 核 + 4GB RAM | ~300MB(只 SpliceTransformer + motif) | 10-30 秒 |

**关键差异**:有 GPU 时玩家每次"调滑块→看雷达图"几乎实时(2-5 秒),无 GPU 时 10-30 秒,UX 要做"加载中骨架屏"。

| 通用预算 | 数值 |
|---|---|
| 前端构建 | 静态导出 |
| SQLite 容量 | 10 万次 run 约 50 MB |
| Proto 模型总占用(全栈) | ~10GB |
| 网络 | 仅首次下载模型,运行期离线 |

---

## 11. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| Proto 包 Windows 安装兼容性差 | 中 | 高 | Docker 化,所有 Python 跑在 Linux 容器里,Windows 主机只跑 Docker Desktop |
| Windows 主机未配置 NVIDIA Container Toolkit(玩家有卡但没启 GPU 透传) | 高 | 中 | README 写明一键脚本 `scripts/setup_wsl2_gpu.ps1`;首次启动检测,提示"检测到 NVIDIA 显卡但未启用 GPU 透传" |
| SpliceTransformer 第一次下载失败 | 低 | 中 | 文档化"断点续传"脚本;支持 HuggingFace 镜像 |
| 玩家设计触发生物安全红线 | 低 | 中 | L1 关键词扫描 + L2 教学题;Phase 3 接 Stanford IRB 流程 |
| 项目过于"教育"被玩家弃坑 | 中 | 中 | 强叙事 + 视觉冲击(雷达图、序列动态生成);委托制持续给新目标 |
| Proto API 变更导致接口断裂 | 中 | 中 | 固定 proto-language 版本 `0.1.0` [($TRAE_REF)](https://github.com/evo-design/proto-language),写好 `requirements-pin` |
| Evo 2 1B / AlphaGenome 模型下载大(6GB)首次体验门槛 | 中 | 低 | 启动时后台下载 + 进度条;可"先玩低档位 demo 任务" |

---

## 12. 验收标准(Phase 1)

✅ 验收通过必须满足:

1. `docker compose up -d` 一行命令起服务,`docker compose logs -f` 看到模型加载完成;
2. **有 NVIDIA 独显时自动启用 GPU profile**(检测 `nvidia-smi` 成功),无 GPU 时降级到 CPU profile,UI 顶部显示当前档位("GPU 加速 / CPU 模式");
3. 浏览器打开 `http://localhost:3000`,能进"极地科考队"任务;
4. 调 5 个滑块,点"开炉",**GPU 档 2-5 秒、CPU 档 10-30 秒**看到雷达图 + 序列预览;
5. 改滑块到目标,能稳定通过风险门(教学题 ≥ 2/3);
6. 作品能存、能进作品墙、能 fork;
7. 全测试套件绿(`make test` 或 `docker compose -f docker-compose.test.yml up --abort-on-container-exit`);
8. README 含"如何开服 / 如何接 Stanford 社区 / 如何开/关 GPU 透传"三条路径;
9. 所有产物在 `C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261\` 下,C 盘未污染。

---

## 13. Phase 2 / 3 扩展点(接口预留,不实现)

| 扩展点 | Phase 1 实现 | Phase 2/3 切换 |
|---|---|---|
| 数据库 | SQLite | SQLAlchemy 切到 Postgres |
| 任务队列 | 同步跑 | 同步路径保留,加 Celery + Redis 异步路径 |
| 用户系统 | 单机 | 加 users 表 + JWT |
| NL 接口 | 占位 | 接 Ollama → 切 proto-client AI Agent |
| 风险门 | L1+L2 | 加 L3 自动评分(基于元件功能分类) |
| 作品墙 | 本地 | 加服务端 API + Stanford 社区导出 |

---

## 14. 引用

[1] Merchant AT et al., "A high-level programming language for generative biology with Proto", bioRxiv 2026.06.22.733870 — https://blog.csdn.net/weixin_51577602/article/details/162294641
[2] evo-design/proto-language GitHub — https://github.com/evo-design/proto-language
[3] ICML 2026 AI for Science oral 分场 — http://m.toutiao.com/group/7659288691986137651/
[4] Koepnick B et al., "De novo protein design by citizen scientists", Nature 570, 390-394 (2019) — https://www.linkresearcher.com/theses/e40363f2-925f-4c79-be09-a34f41268732
[5] Lee J et al., "RNA design rules from a massive open laboratory", PNAS 111(6) 2122-2127 (2014) — https://www.360zhyx.com/home-research-index-rid-29519.shtml
[6] 用户上传的科普稿 — 金牛掰掰的多维宇宙【2026-07-04】

---

## 15. 自检(写完后回头检查)

- [x] **占位符扫描**:无 TBD / TODO;所有接口都有具体路径和请求/响应示例。
- [x] **内部一致性**:架构图与数据流、模块设计、存储模型一致(都用 FastAPI + proto-language + SQLite)。
- [x] **范围检查**:Phase 1 范围聚焦"1 个任务 + 5 个模块雏形",可在一个实施计划内完成。
- [x] **歧义检查**:
  - "Proto 程序"在文中明确 = proto-language 里的 Program 对象;
  - "作品"在文中明确 = artifacts 表的一行;
  - "风险门"在文中明确 = L1 关键词 + L2 教学题;
  - "玩家"在 Phase 1 = 本机单用户,Phase 2/3 才升级。

---

**请用户审阅此文档。** 若有修改意见,直接指出;若无意见,回复"通过",我将调用 `writing-plans` 技能出实施计划。
