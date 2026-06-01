---
name: video-editor
description: 9:16 短视频合成 / 剪辑 skill。三个子模块——**opener**（黄字衬线 4.5s 标题卡）、**animator**（chyron / cutaway / listicle / spec_review HTML 评审，走"三道门"工作流）、**subtitle**（whisper 自动转写 + 关键词高亮 PNG overlay 烧字幕）。触发后**先问做什么**：① 只下字幕 ② 只烧标题 ③ 做新动画 cue / 整片合成 ④ 全流程（口播→cue→动画→合成→字幕）。输出 ① 预览整片 mp4 ② 可选 alpha 通道 broll 层 mov。触发关键词："剪一下这个视频"、"剪视频 / 剪辑"、"做一期视频"、"出整片"、"加动效 / 动画"、"加字幕 / chyron / 弹出文字"、"片头 / 标题卡 / opener"、"把口播和 B-roll 合成"、"新一期 X 系列"。实拍 stock 素材抓取不在本 skill 范围内。
---

# Video Editor · 视频工人

把 9:16 talking-head 口播 + 叠层素材（标题 / B-roll cutaway / chyron / 字幕）合成出短视频。**自给自足**——不依赖其他 skill。实拍 stock 素材抓取不在本 skill 范围内。

## 何时触发

用户说：
- **"剪一下这个视频"、"剪视频"、"剪辑"** —— 最常见入口
- "做一期视频"、"出整片"、"把口播和 B-roll 合成"
- "新一期 [出海 / AI 创业 / X 系列]"
- "给口播加字幕 / chyron / 弹出文字 / 标题卡"
- **"加动效 / 加动画 / 加视觉"**

不触发但相关：
- 实拍 stock 素材 / stock footage → 调 `stock-video` skill（不在本 skill 内）
- 纯 16:9 横屏、纯 voice-over 生成、低于 30s 的短素材 → 不触发

## 第一步 · 路由问询（★ 触发后立即执行）

不要预设用户要走全流程。先用 AskUserQuestion 问一次。**按"最后要做成什么样"（成品形态）来分，不是按"你要干什么"（动作）**——用户脑子里装的是成品，不是流程。

> 你这次最后要做成什么样？
>   1. **一条带字幕的成片**：已有成片，只加字幕             → `subtitle/` 子模块（不走三道门）
>   2. **一个标题卡 / 片头**：4.5s 透明 alpha 叠层          → `opener/` 子模块（不走三道门）
>   3. **一条带动效的整片**：加 chyron / cutaway / 列举动画  → `animator/` 子模块（走三道门）
>   4. **从零做成一整条**：口播 → 标题 → 动效 → 字幕 全包    → opener → animator → subtitle 依次串

**选项标号规范**：AskUserQuestion 的选项前缀**只用纯数字 1 / 2 / 3 / 4**，禁用 ①②③④、㋐㋑㋒㋓ 之类带圈 / 片假名字符——用户字体常不支持，渲染成乱码。

**判断捷径**（不用问就能直达的情况）：

| 用户原话 | 直达 |
|---|---|
| "帮我下字幕 / 加字幕 / 烧字幕" | 1 · subtitle/ |
| "做个片头 / 标题卡 / opener" | 2 · opener/ |
| "新一期 X 系列" / "做一期视频" / "出整片" | 4 · 全流程 |
| 上下文已经在做整片，想加 chyron / cutaway | 3 · animator/ |

**关键原则**：1、2 是单点操作，**不走三道门**；3、4 必须走三道门。

---

## ★ 三道门工作流（选项 3、4 必走，不许跳）

**⚠ 路由选项不是渲染许可**——用户选了 3 或 4 只代表"想走 animator 流程"。**进 animator 之后必须按三道门走，每道门 STOP 等用户明确确认才能进下一步**。即使用户已经告诉你标题 / cue 数 / 文案，**也不代表他允许你跳门**。

```
门 1 · 文字方案      ─►  在 chat 里给 markdown cue 表
                         STOP · 等用户回「OK / 改 X / 砍 Y / 锁定」之类明确表达
                         ❌ 不要写任何 cue HTML
                         ❌ 不要开始渲染
                              │
门 2 · Spec Review   ─►  写每个 cue 的 HTML + 生成 _review/spec_review.html
                         STOP · 告诉用户「打开 file:///<project>/_review/spec_review.html 看，反馈后回我」
                         ❌ 不要渲染 ProRes mov
                         ❌ 不要 compose 整片
                              │
门 3 · 渲前 last call ─►  AskUserQuestion: recap + judgment calls + 输出形式三选一
                          STOP · 等用户选完
                          ❌ 不要预设输出形式
                              │
渲染 + compose + 字幕
```

**用户没说"锁定 / 确认 / 开始 / 渲 / OK"等明确肯定表达之前，你都还在前一道门。**

### ❌ 反例（不要这么干）

| 错误行为 | 损失 |
|---|---|
| 用户选了 4 + 给了标题 → 你直接抽口播 + 转录 + 写 HTML + 渲染 | 跳过门 1 "改 1-2 行字就修"的最便宜 checkpoint，省 5-10 min + 10k token |
| 用户说"我要这样" → 你判断"既然他要那就直接开渲" | 跳过门 2，HTML 视觉/字号错了重渲贵 5 倍（30s 渲 × 失败次数） |
| 用户在门 2 反馈"cue 3 改 X" → 改完直接渲 | 跳过门 3 last call，没让用户挑输出形式（mp4 only / 双输出 / broll only），可能多渲 500MB ProRes |
| 用户没说肯定 → 你猜他想推进就推进 | 用户审视未完成，渲出来跑偏要重做整轮 |

### ✅ 正例

> "进入 animator。先转录 + 出 cue plan markdown 表给你看。**这是门 1**——不写 HTML 不渲染，等你回 OK / 改 / 砍。"

每道门结束都用类似句式 explicit 告诉用户"现在到门 X，等你 OK"——别默默推进。

详细流程 + 各门具体产物清单 + cue 数量 baseline 见 `animator/README.md`。

---

## 子模块入口

| 子模块 | 干嘛 | 入口文档 |
|---|---|---|
| `opener/` | 4.5s 黄字衬线标题卡，透明 alpha 叠层 | `opener/README.md` |
| `animator/` | chyron / cutaway / listicle / spec_review，三道门工作流 | `animator/README.md` |
| `subtitle/` | whisper 转写 → 关键词高亮 PNG overlay → 烧字幕 | `subtitle/README.md` |

## 共用规范

- **视觉规范**：`CONVENTIONS.md`（safe zone、Hana 调色板、chyron 时序、字号层级、climax 规则） —— 任何子模块写 HTML 前必读
- **ffmpeg 双输出 recipe**：`recipes/compose_dual.sh.template`（mp4 + 可选 alpha mov）
- **已知坑**：`recipes/PITFALLS.md`（broll_reel 闪现 / HyperFrames webm 无 alpha / ffmpeg `#` 转义 / 中文路径 TCC 等 22 条）
- **历史案例索引**：`recipes/examples.md`（你的真实视频中的 11 个 cue 范式）

## 双输出策略

| 文件 | 用途 | 何时出 | 规格 |
|---|---|---|---|
| `<片名>_整片.mp4` | 预览 / 发布 / review | **每轮迭代都出** | H.264 yuv420p · CRF 20 · 含音频 + 叠层 |
| `<片名>_broll层.mov` | 剪辑软件叠层（Premiere / AE / FCP） | 用户明说"定稿 / 出剪辑层 / 出 ProRes 层"才出 | ProRes 4444 yuva444p10le · 透明 · 静音 |

迭代期间默认只出整片 mp4。broll 层单次渲染 ~30s + 写盘 ~500MB，迭代期间 review 用不到。

## 标题决策矩阵（用户说"加标题 / 加片头 / 重点字"时如何抉择）

| 用户说 | 默认 = | 关键参数 |
|---|---|---|
| "加标题" / "title card" / "片头" / "opener" | `opener/yellow.html`（黄字衬线大标题 + 白色斜体副标题） | 透明 alpha · 0s 视频起始 · top-third（padding-top 280px）· 4.5s · ProRes 4444 mov |
| "在 X 时刻强调某个词" / "弹出文字" | `animator/chyron/chyron.html` | 黄胶囊 · top 16% (y≈307 中心) · 1-2s pop |
| "1, 2, 3 列举" / "三点 / 四点要素" | `animator/cutaway/scene_listicle.html` | 编号列表逐行揭示 · 卡片 top 280px |
| "全屏数据卡 / 对比图" / "切到 X 数据" | `animator/cutaway/scene_blank.html` | 全屏白底 cutaway · caption top 280px · 不透明 mp4 |

**关键原则**：
- **视频"标题" = 0s 片头**，默认就是。即使口播在 22s 才说到这个 phrase，标题仍然在 0s 出。
- **片头标题 = 透明 alpha 叠在 talking head 上**。不是金色实底独立镜头。
- **数据卡 cutaway = 不透明全屏**，覆盖 talking head；其他叠层（标题 / chyron）默认透明。

## 配套 skill

- **`hyperframes` / `hyperframes-cli`** — HyperFrames CLI（渲 HTML → mov/mp4），动画子模块的渲染依赖

## 不在本 skill 范围

- 实拍 stock 素材抓取（Pexels / Pixabay 等）→ 本 skill 不做
- 16:9 横屏视频 → v2 roadmap
- 文字稿生成 / 口播 TTS → `hyperframes` skill 的 TTS 功能
- 内容合规审核 → `content-audit` skill
