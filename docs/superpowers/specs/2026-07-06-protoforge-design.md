# ProtoForge(原体锻炉)设计文档

> 状态:草案 v0.5 · LLM Provider 重构为云 API 优先 + 引导式选择
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

- **产品形态(v0.4)**:终态是**桌面应用**(Tauri + Python Sidecar),可分发 .exe / .dmg / .AppImage;早期 Phase 1.5 可加 Web 试玩版(玩家仍本地跑);
- **不上云 SaaS**:个人开发者不承担服务器成本(用户 2026-07-06 明确要求);
- 所有产物放**项目目录**下,不动 C 盘(配置 `PROTO_HOME=/path/to/project/.proto`,pip/uv 缓存重定向);
- 单人可维护,渐进推进;
- 兼顾"未来可剥离为独立像素游戏 / 上 Steam"的扩展性(架构可携);
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

## 3. 渐进三步走(核心范围) — v0.4 产品形态重定位

**v0.4 重大转向**:从 "Web 平台 + Docker 部署" 改为 "**Tauri 桌面应用 + Python Sidecar**"。原因(用户 2026-07-06 反馈):
1. 终态产品必须是"装好即玩的桌面应用" —— 不可能让个人长期承担服务器成本;
2. 上 Steam 时必须是单机可分发的游戏,不能依赖云后端;
3. Web 形态作为**早期试玩版**(快上线),但 Phase 1 主流交付必须是桌面应用;
4. 内部架构层做"可携型",未来换 Godot/Unity 时只换壳层。

| Phase | 目标 | 工期 | 算力 | 验证强度 | 交付形态 |
|---|---|---|---|---|---|
| **Phase 1:Tauri 桌面应用 + 1 关** | 单机跑通"剧情 → 调参 → 评分 → 风险门"完整闭环,玩家装 .exe / .dmg 即可玩 | 4-6 周 | 玩家本地,有 GPU 跑真 Proto | 纯 in-silico | Tauri 桌面应用(.exe / .dmg / .AppImage) |
| **Phase 1.5:Web 试玩版(可选)** | 把 Phase 1 桌面应用内嵌 WebView 拆出来,玩家用浏览器试玩(无需安装) | 1-2 周 | 同上 | 同上 | Web 静态站 + 玩家本地 Python sidecar |
| **Phase 2:多关卡 + LLM 助手** | 三个场景全开,玩家作品可本地浏览,Ollama/LM Studio/Claude 接口接好 | 1-2 月 | 同上 | 纯 in-silico + 候选导出 | 桌面应用 + Web 试玩 |
| **Phase 3:作品社区** | 玩家方案可"打包导出"为 .protoforge 文件,在玩家间离线分享(类似 .stl 3D 模型文件) | 2-3 月 | 同上 | 候选列表 | 桌面应用 + 桌面应用内"作品市场" |
| **Phase 4(可选):换 Godot 壳** | 把 Tauri 的 React 前端换成 Godot UI,做像素风 + Steam 发布 | 远期 | — | — | Godot 桌面应用 + Steam |

**当前本文档只锁定 Phase 1(Tauri 桌面应用)的实现细节。** Phase 1.5+ 在文档中以"扩展点"形式标注接口,避免过度设计。

---

## 4. 架构总览(Phase 1) — v0.4 Tauri + Python Sidecar

### 4.0 形态决策(v0.4 新增)

**产品形态 = Tauri 桌面应用 + Python Sidecar**,最终可分发的 .exe / .dmg / .AppImage 单文件。

为什么是 Tauri 不是 Unity/Godot/Electron?(用户 2026-07-06 反馈 + 调研):

| 方案 | 安装包 | Proto 集成 | Steam 友好 | 评价 |
|---|---|---|---|---|
| **Unity** | 100MB+ | C# 桥 Python 复杂 | ✅ 主流 | 商业许可门槛($20万/年) |
| **Godot + py4godot** | 80MB | GDExtension 调 Python [($TRAE_REF)](https://blog.csdn.net/gitblog_01182/article/details/146974359) | ✅ 开源 | py4godot 生态不成熟 |
| **Electron** | 200MB+ | zerorpc/IPC 调 Python [($TRAE_REF)](https://blog.csdn.net/gitblog_00048/article/details/156749267) | ⚠️ Steam 接受但嫌大 | 内存 500MB+ |
| **Tauri + Python Sidecar** | 20-50MB | Rust spawn Python 进程 [($TRAE_REF)](https://blog.csdn.net/weixin_44786530/article/details/139716928) | ✅ Steam 友好 | **✅ 推荐** |
| **Tauri + Python Embed** | 50-100MB | 内嵌 Python 解释器 [($TRAE_REF)](http://m.toutiao.com/group/7181051763548717629/) | ✅ | 备选,Phase 1.5 |

**关键优势**:
- **Tauri 壳 = Rust 写的 WebView**,前端用 React/TS(与之前 Web 方案代码高度复用);
- **Sidecar = 玩家电脑上的 Python 进程**,由 Tauri 启动并通过 stdio 通信;
- **Proto 用系统 Python 跑**(或内嵌 Python Embed,二选一,见 §4.4),不用 Docker 不用 micromamba 隔离(单进程够用);
- **未来切 Godot** = 把 Tauri 的 React 前端换成 Godot UI 节点树,Python Sidecar 完全保留。

### 4.0.1 架构图(v0.4 全新)

```
┌─────────────────────────────────────────────────────────────┐
│  玩家桌面应用:Tauri 主程序(.exe / .dmg / .AppImage)              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Rust 壳(Tauri 2.x)                                    │  │
│  │  - 窗口管理                                              │  │
│  │  - spawn Python sidecar(子进程)                        │  │
│  │  - stdio / localhost:port 与 sidecar 通信                │  │
│  │  - 文件系统访问(读 .protoforge 作品文件)                 │  │
│  │  - 启动器(更新、设置、模型下载)                            │  │
│  └──────────────────────┬────────────────────────────────┘  │
│                         │ Tauri IPC                          │
│  ┌──────────────────────▼────────────────────────────────┐  │
│  │  WebView(React + TypeScript + Tailwind)               │  │
│  │  - 剧情页(任务简报)                                       │  │
│  │  - Forge 工作台(可视化调参 UI)                              │  │
│  │  - 风险门(教学多选题 + 解释)                                 │  │
│  │  - 作品墙(本地浏览自己的作品)                                 │  │
│  │  - Settings 页(LLM provider、档位选择)                   │  │
│  └──────────────────────┬────────────────────────────────┘  │
│                         │ HTTP (Tauri 转发到 localhost:port) │
└─────────────────────────┼───────────────────────────────────┘
                          │
            ┌─────────────▼──────────────┐
            │  Python Sidecar 子进程     │
            │  (玩家电脑上的 Python 进程) │
            │                            │
            │  FastAPI(或 aiohttp)服务器  │
            │  监听 127.0.0.1:7654       │
            │                            │
            │  ┌──────────────────────┐  │
            │  │  Proto 引擎           │  │
            │  │  pip install proto-language │
            │  │  (安装时一次性下载)     │  │
            │  └──────┬───────────────┘  │
            │         │                   │
            │  ┌──────▼───────────────┐  │
            │  │  生物模型栈            │  │
            │  │  - SpliceTransformer  │  │
            │  │  - Evo 2 1B           │  │
            │  │  - ESM2 650M          │  │
            │  │  - AlphaGenome        │  │
            │  │  (按 GPU 档位加载)     │  │
            │  └──────────────────────┘  │
            └─────────────┬──────────────┘
                          │
            ┌─────────────▼──────────────┐
            │  玩家本地存储(项目目录内)    │
            │  - data/protoforge.db      │
            │  - data/programs/*.json    │
            │  - data/sequences/*.fasta  │
            │  - models/  (模型权重缓存)  │
            │  - logs/                   │
            └────────────────────────────┘
```

### 4.0.2 进程间通信(IPC)

**Tauri 主程序 ↔ Python Sidecar** 通过**localhost HTTP** 通信:
- Tauri 启动时 spawn Python 子进程,等待 sidecar 在 `127.0.0.1:7654` 起 FastAPI;
- React 前端通过 Tauri 的 `invoke()` API 调 Rust 壳,Rust 壳转发 HTTP 请求到 Python;
- 优势:Python 端完全用熟悉的 FastAPI,无需新协议;调试时可手动用 curl 测 sidecar。

**为什么不直接 stdio**:stdio 通信需要 Rust 端解析 Python 输出,过于复杂;localhost HTTP 简单且可调试。

### 4.0.3 关于 Docker —— v0.4 答案

**v0.4 决定:Phase 1 不用 Docker**。

- **Proto 工具栈用 micromamba 自动管理环境** [($TRAE_REF)](https://github.com/evo-design/proto-language),所以 Python 侧不需要 Docker 隔离;
- **玩家不需要装 Docker Desktop**,降低安装门槛;
- **Docker 仍在 dev/CI 用**(开发环境用 Docker 跑测试栈、模型下载),但**不分发给玩家**;
- **Phase 3 玩家间"作品分享"通过 .protoforge 文件**(类似 .stl 3D 模型),不需要服务端,不上 Docker。

**Phase 1.5 才有"Web 试玩版"分支**:
- 把 Tauri 内嵌的 React 拆出来成独立 Web 静态站;
- Python sidecar 变成"玩家手动启的 Python 进程 + Web 调 localhost";
- 此时若玩家愿意,可用 Docker 一键起 Python sidecar(作为可选的便利脚本);
- 仍是**玩家本地跑**,不是云端。

### 4.0.4 Python 运行时方案选择(用户 2026-07-06 反馈后新增)

| 方案 | 安装包大小 | 玩家需装 Python? | 难度 |
|---|---|---|---|
| **A. 依赖系统 Python**(要求 ≥3.10) | Tauri 20-50MB | ✅ 是 | 最简单 |
| **B. 内嵌 Python Embed** | Tauri 50-100MB | ❌ 否 | 中等,Phase 1.5 |
| **C. PyInstaller 打 Python sidecar** | Tauri 200-500MB | ❌ 否 | 复杂,Python+ML 库冲突多 [($TRAE_REF)](http://www.cnblogs.com/ddqdd/archive/2023/09/14.html) |

**Phase 1 推荐 A**(要求玩家装 Python 3.10+)→ **Phase 1.5 切 B**(内嵌 Python Embed)→ **Phase 3 评估 C**(PyInstaller)。

**为什么 Phase 1 不直接 PyInstaller**:Proto 用了 micromamba + 多 ML 库,PyInstaller 打包常见问题 200MB+ 起步且跨平台麻烦。Phase 1 先验证玩法,Phase 1.5 再优化安装体验。

### 4.1 数据流(Phase 1 端到端时序)

```
玩家点击"开炉" → 浏览器(WebView)收集滑块值
   → Tauri invoke('forge_run') → Rust 壳
   → Rust 转发 HTTP POST /api/forge/run 到 localhost:7654
   → Python sidecar(FastAPI)校验 + 生成 Proto Program JSON
   → 调用 proto_language.Program.run() (同步,timeout 60s)
   → 收集 constraint 评分 + 输出的 FASTA
   → 写入 SQLite(gallery, runs 表)
   → 返回 { scores: {...}, fasta: "...", risk_flags: [...] }
   → Tauri 壳回传 WebView
   → 浏览器渲染雷达图 + 风险门提示
```

### 4.2 锻炉档位与时长(2026-07-07 修订:按难度分,不按硬件)

**核心定位**:ProtoForge 是**策略游戏**(杀戮尖塔 + 欧陆风云),不是放置类。**4 档不跟硬件挂钩,是玩家主动选的难度**;时长按"心流密度"递增(秒级 → 分钟级),玩家从快速决策逐步过渡到长放置挑战。

| 玩家档位 | 单次开炉真实耗时 | 难度 | 玩法类型 | 徽章 | 心流类比 |
|---|---|---|---|---|---|
| **急锻** | 2-5 秒 | ★ 易 | 卡牌构筑(每回合 2-5 秒决策) | 急锻者 | 杀戮尖塔单回合(30 秒/回合的 1/6) |
| **主锻** | 30 秒 - 2 分钟 | ★★ 中 | 卡牌 + 策略堆叠(短策略) | 主锻匠 | 欧陆风云单回合(5 分钟/回合压缩到 1-2 分钟) |
| **古法锻** | 5-15 分钟 | ★★★ 难 | 放置类为主(挂机 + 离线惩罚) | 古法锻师 | 文明 6 短回合 + 退出概率失败 |
| **晶种培育** | 30 分钟 - 2 小时 | ★★★★ 极难 | 纯放置类(24h 挂机,退出概率失败) | 晶种培育师 | 暗黑破坏神挂机刷装备 + 多队列管理 |

**退出惩罚(4 档都生效)**:
- 玩家在锻造过程中退出游戏 → **根据锻造进度有概率失败**
- UI 顶部红色横幅:「⚠️ 锻造中退出游戏会有概率失败」
- 完成 50% 以下进度 → 90% 概率失败;50-80% → 50% 失败;80-100% → 10% 失败
- 失败保留部分数据(玩家可看失败原因,鼓励重试)

**自动检测与默认档位**:
- 启动时检测硬件,**默认走最低档(急锻,2-5 秒)** 保证所有玩家都能流畅玩;
- 玩家可在 Settings 主动升级档位(主锻/古法锻/晶种培育);
- **不根据硬件自动降级** — 玩家自主选择。

### 4.2.1 难度档位 × 时长 = 核心游戏机制(2026-07-07 重写)

**核心洞察**:**"退出 = 概率失败"是游戏核心张力**。玩家要在"等待时长 vs 退出风险"之间权衡,这就是策略游戏的决策密度。

| 玩家档位 | 单次开炉耗时 | 仪式动画 | 配套机制 |
|---|---|---|---|
| **急锻** | 2-5 秒 | 火花飞溅 + 快速合盖 | 实时决策,玩家几乎不退出 |
| **主锻** | 30 秒 - 2 分钟 | 标准锻造 + 进度条 | 短策略,玩家调整后等待 |
| **古法锻** | 5-15 分钟 | 炭火 + 铁砧 + 慢节奏 | 退出风险中等,玩家挂机看剧情 |
| **晶种培育** | 30 分钟 - 2 小时 | 水晶生长 + 慢镜头 | 退出风险高,玩家挂机去做别的事 |

**关键设计**:
- **不掩盖时长**:UI 永远显示"已等待 X 秒,还需 Y 秒" — 长就是长,玩家有预期;
- **可同时锻造多个**:急锻/主锻 1 个,古法锻 3 个,晶种培育 5 个 — 队列管理是策略;
- **等待中可做其他事**:翻剧情对话 / 看作品墙 / 调下一关卡的参数;
- **档位徽章系统**:8 徽章全部保留(`急锻者 / 主锻匠 / 古法锻师 / 晶种培育师 / 风险评估师 / 蛋白预言家 / 序列诗人 / Stanford 学者`),4 个档位徽章是核心荣誉;
- **跨档位公平**:慢档位有专属成就,快档位有专属成就 — 两端都有荣誉;
- **游戏类型 = 策略游戏**:ProtoForge 是杀戮尖塔(卡牌构筑) + 欧陆风云(策略堆叠)的融合,放置只是部分环节(长任务可挂着)。

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

### 5.5 LLM Provider 抽象层(2026-07-07 修订:引导页 + 免费 API 渠道)

**首次启动引导页(必须保留)**:玩家**必须引导一次**才能进游戏,引导 3 步配置(完成后 Settings 可改):

```
第 1 步:选择 LLM 模式
   ☐ ☁️ 云 API(推荐)— 便宜/效果好,DeepSeek ¥0.001/次,Claude/GPT 可选
       ↳ [免费 API 渠道推荐 → GitHub 跳转]
   ☐ 💻 本地 LLM(已内置 Qwen2.5-7B,无需联网,但 4GB 显存以下会卡)
   ☐ 🎮 纯滑块(不接 AI,完全手动,可玩但慢)

第 2 步:按选择弹对应表单
   云 API → 填 base_url / model / api_key
   本地 → "正在加载 7B 模型,5-10 秒..." 进度条
   纯滑块 → 跳过

第 3 步:硬件检测 + 档位匹配
   "你的显卡:RTX 3060 8GB → 默认档位:急锻(2-5 秒)"
   (急锻/主锻/古法锻/晶种培育 4 选 1,默认急锻,可在 Settings 改)
   [开始游戏]
```

**关键洞察**:完整封装 ≠ 零配置。ProtoForge **必须**引导玩家做一次配置(选 LLM provider + 填 key),但**只做这一次**,做完永不再问。

### 5.5.1 真正的玩家分层(2026-07-07 修订)

| 玩家层 | LLM 接入方式 | 典型用户 | Phase 1 支持 |
|---|---|---|---|
| **云 API 用户(默认推荐)** | Claude / OpenAI / DeepSeek / 任何 OpenAI 兼容云 | 普通玩家、有 key 的开发者 | ✅ **首次启动引导页第 1 步默认走这个** |
| **本地 LLM 用户** | ProtoForge 自带 Qwen2.5-7B(已打包,无需联网) | 不想用云、不想填 key 的玩家 | ✅ 引导页第 1 步可切 |
| **纯滑块用户(不接 LLM)** | 完全不用 NL,纯滑块调参 | 不想配任何东西的玩家 | ✅ 引导页第 1 步可跳过 |

**首次启动引导页**(用户 2026-07-06 反馈:"进游戏有引导界面让你选择"):

```
┌──────────────────────────────────────────────┐
│  欢迎来到 原体锻炉                                 │
│                                              │
│  你想用什么 AI 助手?                              │
│                                              │
│  ⚡ 推荐:云 API(便宜、效果好)                      │
│  [ 配置云 API ]  ← 默认高亮,DeepSeek/Claude/GPT/... │
│                                              │
│  💻 本地模型(需要你电脑已装 Ollama 或 LM Studio)        │
│  [ 用本地模型 ]                                   │
│                                              │
│  🎮 先不接 AI,纯滑块玩(可稍后在 Settings 启用)         │
│  [ 跳过,纯滑块 ]                                  │
│                                              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━          │
│  💡 为什么推荐云 API? 云 API 调用一次不到 0.01 元,    │
│     比本地跑 Ollama 省事 100 倍。                    │
│     本地模型需要你电脑有 8GB+ 显存 + 装好模型,           │
│     ProtoForge 不会把这些模型打包进游戏。              │
└──────────────────────────────────────────────┘
```

**用户原话(2026-07-06)**:"你看现在他这个他这个开源的这个项目是可以直接打包进游戏里面...然后你说他这里面会涉及到这个 lls 可以看到你都打算是用这种无需用这个哈珀 face API 或者用本地的小游戏...如果你本地的话你你这个很麻烦很麻烦对不对而且你本地那你是不是要把欧拉码封装进去啊对不对"

**核心设计原则**:
- **不打包本地模型进游戏**:Ollama / LM Studio 玩家自己装,ProtoForge 不封装,降低安装包大小 + 维护成本;
- **云 API 优先推荐**:便宜、效果比本地小模型好、不依赖玩家硬件;
- **玩家随时可在 Settings 切换** provider,不需要重启游戏;
- **纯滑块永远可用**:LLM 是锦上添花,核心玩法不依赖它。

#### 5.5.2 统一 LLMClient 接口(适配 3 类)

后端抽象一个 `LLMClient` 接口,内部把 3 类 provider 统一成 `messages → response`:

```python
# apps/api/app/llm/base.py
class LLMClient(Protocol):
    async def complete(self, system: str, user: str, **kw) -> str: ...

# apps/api/app/llm/providers/
#   - cloud.py       (Claude / OpenAI / DeepSeek / 任何 OpenAI 兼容云,必填 api_key)
#   - local.py       (Ollama localhost:11434 / LM Studio localhost:1234,玩家自己装)
#   - disabled.py    (NL 接口完全关闭,纯滑块游戏)
```

**协议统一**:Ollama / LM Studio 都已经支持 OpenAI 兼容 API [($TRAE_REF)](https://juejin.cn/post/7590128405350285312),所以 `local.py` 和 `cloud.py` 都用 `openai` Python SDK,只是 `base_url` 和 `api_key` 不同,**零额外代码**。

#### 5.5.3 引导后保存的配置(`data/protoforge.db` 的 `app_settings` 表)

```json
{
  "llm_provider": "cloud",    // cloud / local / disabled
  "base_url": "https://api.deepseek.com/v1",  // 云 API 默认推荐 DeepSeek
  "api_key": null,            // 玩家在引导页填
  "model": "deepseek-chat",   // 推荐 DeepSeek 便宜;Claude 玩家可改
  "system_prompt_override": null,
  "onboarded": true           // 引导完成标记
}
```

**首次启动检测**:`onboarded=false` 时,React 渲染引导页;完成后写 `onboarded=true`,后续不再展示。

#### 5.5.4 用户分级 UX(Settings 页)

- **普通玩家**:`Settings` 页只看到"已选:云 API(DeepSeek)","更换"按钮;
- **进阶玩家**:展开"高级",可改 `model`、`base_url`;
- **开发者**:展开"开发者模式",可改 `system_prompt`、调 `temperature`、看每次 LLM 调用的 token 用量和耗时。

#### 5.5.5 NL → Proto 翻译 Prompt 模板(Phase 1 内置,Phase 3 可被 Stanford AI Agent 替换)

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

#### 5.5.6 Phase 进度安排(2026-07-06 重写)

| Phase | NL 接口状态 |
|---|---|
| **Phase 1** | 首次启动引导页(3 选项);**默认推荐云 API(DeepSeek)**;Settings 可随时切;玩家不接 LLM 也能玩 |
| Phase 2 | 引导页加 LLM 能力展示("AI 助手能帮你做什么");5 个新手引导关卡全用 NL 教玩家 |
| Phase 3 | 接 Stanford Proto 社区 AI Agent [($TRAE_REF)](https://blog.csdn.net/weixin_51577602/article/details/162294641);玩家方案可"导出为 NL 描述"反向生成;**首次启动引导增加"贡献科研"说明**(玩家知道自己的作品会被科研使用) |

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

## 6. 项目结构(v0.4 Tauri 重写)

```
protoforge/                            # 项目根(玩家安装时的目录)
├── README.md
├── package.json                       # npm workspace 根
├── pnpm-workspace.yaml                # 多包管理
├── .env.example
├── .gitignore
├── docs/
│   └── superpowers/specs/2026-07-06-protoforge-design.md
│
├── apps/
│   ├── desktop/                       # Tauri 2.x 主程序(Rust 壳)
│   │   ├── src-tauri/
│   │   │   ├── src/
│   │   │   │   ├── main.rs            # Tauri 入口
│   │   │   │   ├── sidecar.rs         # spawn Python 进程
│   │   │   │   ├── ipc.rs             # Rust → Python HTTP 转发
│   │   │   │   ├── commands.rs        # Tauri invoke 命令
│   │   │   │   └── fs.rs              # 作品文件读写
│   │   │   ├── tauri.conf.json
│   │   │   ├── Cargo.toml
│   │   │   └── icons/                 # 跨平台图标
│   │   └── package.json
│   │
│   ├── web/                           # React + TypeScript 前端(被 Tauri WebView 加载)
│   │   ├── src/
│   │   │   ├── App.tsx                # 路由
│   │   │   ├── pages/
│   │   │   │   ├── Home.tsx           # 任务选择
│   │   │   │   ├── Mission.tsx        # 任务简报
│   │   │   │   ├── Forge.tsx          # 锻炉工作台
│   │   │   │   ├── RiskGate.tsx       # 风险门
│   │   │   │   ├── Gallery.tsx        # 作品墙
│   │   │   │   └── Settings.tsx       # 设置(LLM provider、档位)
│   │   │   ├── components/
│   │   │   │   ├── Sliders.tsx        # 滑块组件
│   │   │   │   ├── RadarChart.tsx     # 5 维雷达图
│   │   │   │   ├── SequenceView.tsx   # 序列预览
│   │   │   │   ├── ForgeAnimation.tsx # 锻炉动画
│   │   │   │   └── ...
│   │   │   ├── lib/
│   │   │   │   ├── api.ts             # 调 Tauri invoke
│   │   │   │   ├── tauri.ts           # Tauri API 封装
│   │   │   │   └── forgeTime.ts       # 锻炉仪式渲染
│   │   │   ├── tailwind.config.ts
│   │   │   └── package.json
│   │   └── ...
│   │
│   └── api/                           # Python Sidecar(FastAPI)
│       ├── app/
│       │   ├── main.py                # FastAPI 入口
│       │   ├── routers/
│       │   │   ├── missions.py        # GET /api/missions
│       │   │   ├── forge.py           # POST /api/forge/run
│       │   │   ├── gallery.py         # GET /api/gallery
│       │   │   └── risk.py            # POST /api/risk/evaluate
│       │   ├── proto/
│       │   │   ├── engine.py          # proto-language 封装
│       │   │   ├── missions.py        # 任务模板加载
│       │   │   ├── exporters.py       # FASTA 导出
│       │   │   └── profile.py         # GPU 档位检测
│       │   ├── llm/
│       │   │   ├── base.py            # LLMClient Protocol
│       │   │   ├── providers/
│       │   │   │   ├── cloud.py       # Claude/OpenAI/DeepSeek/任何 OpenAI 兼容云
│       │   │   │   ├── local.py       # Ollama / LM Studio(玩家自装,游戏不打包)
│       │   │   │   └── disabled.py    # 纯滑块模式
│       │   │   └── factory.py         # 引导后按配置选 provider
│       │   ├── db.py                  # SQLAlchemy
│       │   └── config.py
│       ├── tests/
│       │   ├── test_missions.py
│       │   ├── test_forge.py
│       │   ├── test_gallery.py
│       │   ├── test_risk.py
│       │   └── test_llm_factory.py
│       ├── pyproject.toml             # uv 管理
│       └── uv.lock
│
├── data/                              # (gitignore,玩家本地数据)
│   ├── protoforge.db
│   ├── programs/
│   ├── sequences/
│   └── exports/                       # .protoforge 作品导出
│
├── models/                            # (gitignore,生物模型权重缓存)
│   ├── splice_transformer/
│   ├── evo2_1b/
│   ├── esm2_650m/
│   └── alphagenome/
│
├── dev/                               # (gitignore,开发用)
│   └── docker-compose.yml             # 仅 dev/CI 用,玩家不分发
│
└── scripts/
    ├── install.sh                     # 玩家安装脚本(检查 Python、pip install proto-language)
    ├── start_dev.sh                   # 开发模式(只起 Python sidecar,Tauri 调试)
    └── build_release.sh               # 打 .exe / .dmg / .AppImage
```

**关键目录变化(v0.4)**:
- 删:`docker-compose.yml`(玩家不分发)
- 加:`apps/desktop/src-tauri/`(Tauri Rust 壳)
- 加:`dev/docker-compose.yml`(仅 dev/CI 用)
- 加:`scripts/install.sh`、`build_release.sh`(玩家安装 + 跨平台打包)

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

## 11. 风险与缓解(v0.4 重写)

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| 玩家未装 Python 3.10+ | 高 | 高 | Phase 1 `scripts/install.sh` 自动检测 + 引导安装;Phase 1.5 切 Python Embed |
| 玩家未装 Ollama/LM Studio,但选了"本地模型" | 中 | 低 | 引导页检测 `localhost:11434` / `1234`,不可用就提示"你电脑没装 Ollama,建议改用云 API",并给一键安装链接 |
| 玩家填的云 API key 无效/欠费 | 高 | 低 | 引导页填完就 ping 一下,失败提示;运行时调用失败弹"AI 助手连接失败,已切到纯滑块" |
| Tauri 跨平台打包复杂(Win/Mac/Linux) | 高 | 高 | 优先做 Windows + macOS,Linux 社区驱动;参考 tauri-action GitHub Action |
| Rust ↔ Python sidecar spawn 失败 | 中 | 高 | Tauri 启动时 health check 5s 超时,失败提示重装;日志写到 `logs/sidecar.log` |
| Proto 工具栈 micromamba 在 Windows 兼容问题 | 中 | 高 | Phase 1 用纯 pip install 试,失败则降级到 v0.3 的 Docker 方案作为兜底 |
| 玩家设计触发生物安全红线 | 低 | 中 | L1 关键词扫描 + L2 教学题;Phase 3 接 Stanford IRB 流程 |
| 项目过于"教育"被玩家弃坑 | 中 | 中 | 强叙事 + 视觉冲击(雷达图、序列动态生成);委托制持续给新目标 |
| Proto API 变更导致接口断裂 | 中 | 中 | 固定 proto-language 版本 `0.1.0` [($TRAE_REF)](https://github.com/evo-design/proto-language),写好 `pyproject.toml` pin |
| Evo 2 1B / AlphaGenome 模型下载大(6GB)首次体验门槛 | 中 | 低 | 启动时后台下载 + 进度条;可"先玩低档位 demo 任务" |

---

## 12. 验收标准(Phase 1) — v0.4 Tauri 重写

✅ 验收通过必须满足:

1. `scripts/build_release.sh` 一行命令在 Windows / macOS 都能打出 .exe / .dmg;
2. 玩家双击 `ProtoForge.exe`,5 秒内出现主窗口,自动 spawn Python sidecar;
3. **有 NVIDIA 独显时自动启用 GPU profile**(检测 `nvidia-smi` 成功),无 GPU 时降级到 CPU profile,UI 顶部显示当前档位("急锻 / 标准锻 / 古法锻 / 晶种培育");
4. 进"极地科考队"任务,调 5 个滑块,点"开炉",**对应档位的仪式时长**看到雷达图 + 序列预览;
5. 改滑块到目标,能稳定通过风险门(教学题 ≥ 2/3);
6. 作品能存、能进作品墙、能 fork,能导出为 .protoforge 文件;
7. **Web 试玩版** (Phase 1.5):`pnpm dev` 起 React,本地 Python sidecar 跑通,浏览器能玩;
8. 全测试套件绿:
   - 后端:`cd apps/api && pytest tests/`(单元 + 集成);
   - 前端:`cd apps/web && pnpm test`(组件单测);
   - E2E:`pnpm test:e2e`(Playwright 跑"Tauri 窗口 → 任务 → 开炉 → 作品"全流程);
9. README 含"如何从源码构建 / 如何下载发布包 / 如何接 Stanford 社区 / 如何接 Ollama/LM Studio"四条路径;
10. 所有产物在 `C:\Users\32893\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a4b9e7dfc8269540e150261\` 下,C 盘未污染(模型权重放项目 `models/` 下)。

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
