# animator · 动画组件子模块（走三道门）

把口播 + HTML 动画 cue 合成出 9:16 短视频。这是 video-editor 的**主力子模块**，走 **三道门** 工作流，结构性错误在 0 渲染阶段就抓到，渲染只在锁了之后发生。

## 何时进 animator（vs 别的子模块）

| 场景 | 用 |
|---|---|
| 已有成片，只下字幕 | `subtitle/` |
| 只烧一个标题卡 | `opener/` |
| 做新动画 cue / 整片合成 | **animator/**（这里） |
| 全流程 | opener → animator → subtitle 串起来 |

## 模板清单

```
animator/
├── chyron/                          ← 文字叠层（透明，叠 talking head）
│   ├── chyron.html                  ← 黄底胶囊 + 4° skew + pop 弹入 1-2s
│   └── chyron_underline.html        ← 米卡 + 关键词黄色下划线 wipe（编辑感）
├── cutaway/                         ← 全屏/卡片切场（覆盖 talking head）
│   ├── scene_blank.html             ← 米底白卡 + caption fade-in（数据卡/抽象概念）
│   ├── scene_listicle.html          ← 编号 1–4 逐行 stagger reveal（"1, 2, 3 列举"）
│   ├── scene_progressive_top_card.html ★ ← 顶部安全位单卡轮播 + 末尾全屏 recap（5+ 项长信息）
│   └── scene_burst_emoji.html ★     ← 群体 emoji 啪啪啪（"X 密度高"视觉冲击）
├── review/
│   └── spec_review_template.html    ← 门 2 spec review HTML（iframe 卡片 + 决策 chip）
└── _hyperframes_meta/               ← hyperframes.json + meta.json（cp 进每个 cue 目录）
```

**触发对应**：

| 用户说 | 模板 |
|---|---|
| "在 X 时刻强调某个词" / "弹出文字" | `chyron/chyron.html` 黄胶囊 |
| 长文字 / 不想抢镜的标注 | `chyron/chyron_underline.html` |
| "1, 2, 3 列举" / "三点 / 四点要素"（≤4 项） | `cutaway/scene_listicle.html` |
| 口播逐个介绍 5+ 项（景点/类型/理由） | `cutaway/scene_progressive_top_card.html` ★ |
| "全屏数据卡 / 对比图" / "切到 X 数据" | `cutaway/scene_blank.html` |
| "X 密度高 / 大量 / 满地" 视觉冲击 | `cutaway/scene_burst_emoji.html` ★ |

## 三道门工作流

```
speech.mov + 文案 / transcript
   ↓ 1. 转录（whisper-cli + ggml-base.bin / ggml-small.bin）
   ↓ 2. 按转录定位每个 cue 的时间和内容
   ↓ 3. 为每个 cue 决定来源：
        a. 主标题片头  → opener/ 子模块（yellow.html）
        b. HTML 动画  → cutaway/scene_blank.html 等
        d. 文字 chyron → chyron/chyron.html
        e. 列举 trio   → cutaway/scene_listicle.html
   ↓ 4. ★★ 门 1 · 文字 cue 方案预审（在对话里给表格，等用户确认）
        ——这是最便宜的 checkpoint：0 HTML / 0 渲染。
        给一份 markdown 表格：
        | # | 时间窗 | 类型 | 动画/视觉概念 | 标题 / 重点字 / 文案 | 数据来源 | 对应口播文本 |
        让用户扫一眼判断：
        - cue 数对不对（不要太多 / 不要漏）
        - 标题文案 / 重点字符是否符合事实（fact-check 在这一步暴露最便宜）
        - **数据来源逐一标注**：在地观察 ✓ / 官方数据 ✓ / Lonely Planet ✓ / 媒体 ✓ / **⚠ 无权威源**
          —— 默认策略：**没权威 single source 的数字不放**，必要时用语义化措辞
          （"密度极高" 而非 "6.7 只/100km² 全球第一"）
        - 动画概念抓不抓得住口播意图
        - 时间窗有没有跟口播节奏对齐
        用户确认或反馈"改 X / 删 Y / 加 Z"，回到 4，可以多轮直到锁定。
        ★ 不要跳过这一步直接写 HTML——除非 cue 极少（≤2 个）且都是已用过
        的 well-known 模板（如纯 opener + 一段 stock）。
   ↓ 5. 写出每个 cue 的 HTML 源文件（不渲染）
   ↓ 6. ★ 门 2 · Spec Review：生成 _review/spec_review.html
        **直接 cp 模板**：
          cp ~/.claude/skills/video-editor/animator/review/spec_review_template.html \
             <project>/_review/spec_review.html
        然后改模板顶部 CONFIG 区（TOTAL_LENGTH + SCENES 数组），不要从零写。
        模板内含：
          - 顶部 ⏱ Cue 时间窗一览表格
          - responsive grid（每张卡 iframe 自动缩到卡宽）
          - **决定 chips（渲 ✓ / 改 HTML / 删除 ✗）+ 问题标签 + 评论 textarea**
          - 顶部"导出反馈→" 一键复制 markdown 给 Claude
        用户审：视觉效果 / 配色 / 字号 / 进场节奏。
        决定：渲 / 改 HTML / 删（点 chip + 写评论 + 导出反馈）。
   ↓ 7. 用户改动反馈 → 改 HTML，回到 6（无渲染成本）
        删 cue 时**保留 id 不 renumber**（数组里跳号即可，如 1,2,3,5,6）。
   ↓ 8. ★ 门 3 · spec 锁了 → 渲染前主动在对话里抛 "last call" 三段问询：
        ① 重述方案：cue 列表 + 时间窗 + 总覆盖时长
        ② 列出我做过的 judgment calls：自动改了什么、字号 / 配色 / 数据来源 /
           cue 增删 / 措辞替换 等
        ③ 视频三选一（措辞要让用户一眼分清"带不带原片"和"是不是一条轨"）：
           - A. 合成的原片 (.mp4 h264 含音频 · 叠层已烧进原片 · 自己看 / 直接发)
           - B. 只有 Alpha 的透明素材 —— **一条对好时间的完整 broll 轨道**
                (.mov ProRes 4444 alpha · 不含原片 · 进剪辑软件叠一层就行)
           - C. 两个都要（定稿期标准）
        ⚠ B 永远是**单条、时间对齐**的整轨（lavfi 透明画布 + 各 cue itsoffset 摆好），
           **绝不是 N 个分片 mov 让用户自己去剪**。用 compose_dual 模板的 Output 2。
           过去踩过的坑：把 "alpha 素材" 误交付成 6 个独立分片，用户得自己摆时间轴。
        ④ 标题透明图层（★ 默认也产出，不用用户单独要）——为 3:4 封面设计的透明 PNG，
           1080×1440，doc-to-slides 封面大标题级别；一图两用（叠视频顶部 + 当封面标题层）。
           做法见 `../recipes/deliverables.md`。
        ⑤ 章节时间轴（★ 默认也产出，所有视频）——从 cue plan + 转写时间码推导，
           粗颗粒 ~1 点/30–40s（2 分钟 3–4 点），写成 `<视频代号>-时间轴.txt`。
        ▷ 三样都落交付文件夹 `~/Movies/<系列>/<视频代号>/`，命名
          `<视频代号>-成片.mp4` / `-标题层.png` / `-时间轴.txt`。规范见
          `做内容/_运营文档/视频成片流水线-模板.md`。
   ↓ 9. 按答案渲染：HyperFrames / timecut 渲每个 cue + ffmpeg compose 出对应输出
   ↓ 10. ★ Result Review（仅在出了整片 mp4 时）：生成 _review/result_review.html
        - poster 抽帧 + hover-loop 整片片段
        - 用户审：实际节奏 / 文字时机 / 微调
   ↓ 11. 反馈 → 改改动的 cue → 单 cue 重渲 + 重 compose
```

### 三道门的分工

| 门 | 何时 | 产物 | 失败成本 | 主要抓什么 |
|---|---|---|---|---|
| **门 1 · 文字方案** | 写 HTML 之前 | chat 里 markdown 表格 | 改 1-2 行字 | 概念错位 / fact-check / 措辞 / cue 增删 / 时间窗 |
| **门 2 · Spec Review HTML** | 写完 HTML / 渲染之前 | `_review/spec_review.html` (iframe) | 改 HTML，~10s 重看 | 视觉效果 / 配色 / 字号 / 进场节奏 |
| **门 3 · 渲前 last call** | spec 锁定 / 开渲之前 | chat 三段问询 | 0（还没渲） | 遗漏约束 / judgment calls / 输出形式 |

每过一道门，下一道门的成本指数级上升——所以越早抓住问题越好。

**Why**：上一版是"先渲后审"，结构性错误（fact-check / 标题样式 / 位置）渲了才发现，每次重渲 ~2 min × 500MB 写盘。三道门把结构性 review 提前到 0 渲染阶段。一期累积省 5-10 min + ~10k token + 1.5 GB。

**例外**：cue 极少（≤2 个）且都是已用过的 well-known 模板（如纯 opener + 一段 stock）→ 可跳过门 1 直接进门 2。但门 1 是默认。

## cue 数量 baseline + 反馈循环

### 健康 cue 密度

| 口播时长 | 健康 cue 数 | 偏多警告（≥）|
|---|---|---|
| 30-60s | **3-5** | 6 |
| 60-90s | **5-7** | 8 |
| 90-120s | **6-9** | 10 |
| 120-180s | **8-12** | 13 |

**经验法则：每分钟 4-6 个 cue 是健康节奏**。超过 8/分钟 = 太密、talking head 长期被遮、观众喘不过气。

### 用户说 "cue 太多" 时的处理脚本

不自动删，按以下步骤走：

1. **扫一遍当前 cue list，按"性价比低"标记候选**：
   - 时间窗 < 1.5s（一闪而过没读完）
   - 跟前后 cue 概念重复
   - 装饰性（emoji burst 没承担说明任务）
   - 没强观点（"这里有个 cue 但内容平平"）

2. **在对话里给一份 markdown 表格 propose 砍单**：
   ```
   | id | 时间窗 | 类型 | 文案 | 状态 | 砍掉理由 |
   |----|--------|------|------|------|---------|
   | 3  | 9-9.8  | chyron | 葡语 | ⚠ 建议砍 | 0.8s 太短 + 信息冗余 |
   | 5  | 22-23  | emoji burst | 🎉×30 | ⚠ 建议砍 | 装饰，无说明意义 |
   ```

3. **等用户确认**：保留/调整/自己挑

4. **改 SCENES 数组**（保留 id 不 renumber，跳号即可，如 1,2,4,6,7）

5. **重渲 spec_review.html 重审**

### 用户说"加 cue"时的处理脚本

接受 3 种输入：

**方式 A · 指定位置 + 类型**（最精确）：
> "在 8s 加一个 chyron 强调 'AI 100 强'"

**方式 B · 指定口播段落**（最自然）：
> "'巴西免签 30 天' 那段太干，加点视觉"

→ 反过来跟用户确认："这段在 12-18s，建议加 listicle（3 项）—— 圣保罗/里约/萨尔瓦多。要这样吗？"

**方式 C · 描述意图**（最快）：
> "16-22s 这段太单调"

→ 扫上下文 + cue 间隔 + 信息密度 → 提案 2-3 种方案让用户选。

**任何方式的输出都是**：chat 里 propose（给 cue 草稿）→ 用户确认 → 改 SCENES 数组 + 写新 cue HTML → 重渲 spec review。

## cue 渲染

> ⚠️ **Node 25 别用 timecut（会挂死）**。改用固化好的逐帧脚本：
> ```bash
> # 帧序列： node <video-editor>/recipes/render_cue_puppeteer.js <html> <durationSec> <framesDir>
> # 单帧图： node <video-editor>/recipes/render_cue_puppeteer.js <html> --t <sec> <outPng>
> # 帧→透明 mov： ffmpeg -framerate 30 -i <framesDir>/f%04d.png -c:v prores_ks -profile:v 4 -pix_fmt yuva444p10le cue.mov
> ```
> 它用 puppeteer-core 直驱系统 Chrome，逐帧 seek `__timelines.main` 截透明 PNG，不挂。下面 timecut 仅作老 node 备查。

```bash
# 1. 复制空模板新建 cue 项目
mkdir my_project/scene_X && cd my_project/scene_X
cp ~/.claude/skills/video-editor/animator/cutaway/scene_blank.html index.html
cp ~/.claude/skills/video-editor/animator/_hyperframes_meta/* .  # hyperframes.json + meta.json

# 2. 编辑 index.html 改文案 / 动画 / 颜色

# 3. 渲染 ProRes 4444 alpha mov（用 timecut，单文件直接渲；hyperframes 需要先 init 项目骨架）
DUR=3.0   # cue 时长（秒）
npx --yes timecut index.html \
  --duration=$DUR --fps=30 --viewport=1080,1920 \
  --transparent-background \
  --output=render.mov \
  --output-options="-c:v prores_ks -profile:v 4 -pix_fmt yuva444p10le" \
  --launch-arguments="--no-sandbox"
```

> ⚠ webm 格式不带 alpha 通道（已知坑），所以一律用 mov + ProRes 4444。详见 `../recipes/PITFALLS.md`。

## 合成（双输出）

参考 `../recipes/compose_dual.sh.template`。改顶部 `SPEECH` / `DURATION` / `OVERLAYS` 数组即可生成 mp4 + 可选 alpha mov 双输出。

## 配套规范

- `../CONVENTIONS.md` —— ★ 必读。safe zone / chyron 时序 / 字号层级 / cutaway 多段规则 / climax 规则
- `../recipes/PITFALLS.md` —— 23 条已知坑（叠帧鬼影 / HyperFrames webm 无 alpha / ffmpeg `#` 转义 / alpha 层变灰 等）

## 叠帧鬼影坑（高频）

3 个连续 chyron 用同一矩形位置，cue 之间只要 0.05s 时间重叠，前一个还在 fade-out（剩余 opacity）+ 后一个 fade-in（已开始上升），两个字同时半透叠在一起 → 视觉鬼影。修法：

- 错开位置（不重叠不冲突）
- 或拉开 cue 间隔到 ≥0.30s gap
- 或改用 `scene_listicle.html` 一次性出全（没有切换问题）
