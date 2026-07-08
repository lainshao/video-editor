# slidecast · 口播实操教学片（3:4 · case-step 录屏窗 + 字幕）

> **本模块只覆盖整条工作流的「阶段 3」**（3:4 壳 + 底部透明背景视频）。
> 完整 5 阶段标准工作流（立项 → PPT 课件 → 录制 → 壳/背景 → 后期 → 文案）见
> `做内容/_运营文档/实操教学片-工作流.md`。

把一段**纯口播录音**变成一条 **3:4 slide 底稿视频**：每段口播对应一张 case-step 帧（米底 + 标题/副标题 + **透明录屏窗**），按转写时间码硬切，底部烧关键词高亮字幕。产两版：

- `成片_预览.mp4` —— 米底填洞 + 音轨，直接看效果/对时间
- `成片_透明层.mov` —— **录屏窗真透明**（ProRes 4444），剪映里把录屏轨放这层**下面**透出来，圆脸再叠上

用户只需在剪映补两件事：**录屏**放进窗口、**圆脸**叠角落。

---

## ★ 何时用（画幅是内容类型决定的，不是默认全 3:4）

| 内容类型 | 画幅 | 走谁 |
|---|---|---|
| **实操教学 / 录屏演示**（"我怎么用 AI 做 X"、要展示屏幕操作） | **3:4** | ✅ **slidecast**（本模块） |
| 讲观点 / vlog / 泛文化 / 普通口播 | 9:16 | video-editor 主流程（opener/animator/subtitle），**不用本模块** |

**进来第一件事：确认"这条是不是实操教学类"。** 是 → 3:4，往下走；不是 → 回 video-editor 主流程按 9:16 做。别把普通口播硬塞进 3:4 录屏窗版式。

---

## 三道门（和 animator 一样，每道门 STOP 等确认）

**门 1 · 帧方案**
1. 转写：`whisper-cli`（build.sh 会自动做，或先单独跑拿 `transcript.srt`）。
2. 读转写，把口播切成段（开场 / 第一点 / 第二点 / 板块…），**每段一张 case-step 帧**：
   - `title` = 当前板块（如"为什么用 AI 做 PPT"）
   - `sub` = 当前的点（"① 快" / "② 互动性强"…，对应口播的第一/第二/第三）
   - **底部不放内容**——留给字幕
3. 在 chat 里给「分段表」：`帧 | 时间码 | title | sub`。**STOP 等用户 OK/改/砍。**

**门 2 · 渲帧 review**
4. 写 `manifest.yaml`（doc-to-slides，`template: case-step`，`theme: hannah`，deck 级 `series`/`index`）+ `timeline.tsv`（`帧文件名<TAB>秒`，秒 = 该段口播时长，从 SRT 段边界对齐）。
5. 渲：`python3 ~/.claude/skills/doc-to-slides/render.py <proj>/manifest.yaml`。给用户看 `frames/review.html`。**STOP。**

**门 3 · 出片**
6. `bash build.sh <proj>` → 出 `成片_预览.mp4` + `成片_透明层.mov` + **`字幕自检.png`**。
7. **出片必做 · 全幕字幕自检**：打开 `<proj>/字幕自检.png`（build 自动生成的 contact sheet，全部字幕胶囊一屏），**逐幕**核验字号（都够大）/ 断词（英文词、中文词没被切开）/ 关键词染橙 / 转写错字。**字幕是逐幕都可能出问题的东西，必须全看，不能只抽样、不能只看用户截的那张。** 发现问题回去改（`--minsize` / `keywords.txt` / `corrections.txt`）重跑。
   - 3:4 壳帧**不在这步重看**：壳在门 2 的 `frames/review.html` 已审过，自检只针对字幕。
8. 抽 2-3 帧确认字幕叠在画面上的位置/时间无误 → 交付到 `~/Movies/<系列>/<代号>/`。

---

## 工程目录（build.sh 的输入）

```
<proj>/
├── voiceover.mov      纯口播（任意画幅，只取音轨）
├── manifest.yaml      doc-to-slides case-step 帧清单（门 2 写）
├── timeline.tsv       每行「帧文件名<TAB>秒」（门 2 写，秒从 transcript 对齐）
├── keywords.txt       可选 · 每行一关键词，字幕命中染安全橙
├── corrections.txt    可选 · 每行 wrong=right，修转写错字
└── （自动生成）transcript.srt / frames/ / subs/ / 成片_*.{mp4,mov}
```

跑：`bash ~/.claude/skills/video-editor/slidecast/build.sh <proj>`

## case-step 帧长什么样
doc-to-slides 的 `case-step` 模板（3:4 · 1080×1440 · 安全橙硬编码）：
表头左=系列名黑胶囊 / 右=序号（如 `001`）· 大衬线标题 + 副标题 · **近满宽 16:9 透明录屏窗** · 底部空（留字幕）· 右下 300×300 真人安全区（不放 placeholder，剪映叠圆脸）。改 manifest 的 `title`/`sub` 即可。

## 字幕样式（subs.py）
米底胶囊 + 深墨**粗体**（Hiragino W6 + stroke）+ **字间距 6px**（不拥挤）+ **关键词安全橙** + **长行自动缩字号**不超安全边（maxw 880）。位置在录屏窗洞底之下（y≈978）。本机 ffmpeg 无 libass/drawtext，所以字幕走 PNG overlay —— 这是刻意的，别改用 drawtext。

## 参考成品
`~/Movies/AI/AI 100件事/001 PPT/`（100 个 AI 实操案例 · 001 做 PPT）——第一条用这套做的，可对照。
