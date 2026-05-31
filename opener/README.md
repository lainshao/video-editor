# opener · 标题卡子模块

4.5s 1080×1920 标题卡，**透明 alpha** 叠在 talking head 顶部第三方位（不替换主持人）。渲染为 ProRes 4444 alpha mov，喂给 `recipes/compose_dual.sh.template`。

**不走三道门** —— 这是单点操作，3 输入 + 渲染 = 完事。

## 模板：`yellow.html`

| 视觉 | 适用 |
|---|---|
| 透明背景 · 黄色加粗衬线大标题 `#ffd12e` + 白色斜体副标题 + 顶部方块 logo · 弹性入场 + 呼吸 + 结尾淡出 | 通用 9:16 口播标题卡（AI / 干货 / 泛文化都能用） |

> 顶部那枚陶土方块 logo 是可替换的占位元素——改 `.logo` 的 `background` 和里面的 `<svg>` 就能换成你自己的标记，或整块删掉。

## 3 个输入

| Slot | 占位符 | 内容 | 例子 |
|---|---|---|---|
| 大标题第一行 | `{{TITLE_LINE1}}` | 衬线大字上半 | `Claude Code` / `泰国 10 天` |
| 大标题第二行 | `{{TITLE_LINE2}}` | 衬线大字下半 | `到底怎么用？` / `新手抄作业` |
| 副标题 | `{{SUBTITLE}}` | 白色斜体一行 | `第一次也能跟上` / `完整路线 + 避坑` |

**视觉钩子**：两行大标题是主信息，副标题补一句钩子。标题别太长，溢出就拆短或降字号（见下）。

## 用法

```bash
# 1. cp 模板进项目
cp ~/.claude/skills/video-editor/opener/yellow.html my_project/opener/01_opener.html

# 2. 编辑：替换 {{TITLE_LINE1}} / {{TITLE_LINE2}} / {{SUBTITLE}}

# 3. 渲染到 ProRes 4444 alpha mov（默认透明叠层模式）
cd my_project/opener
npx --yes timecut 01_opener.html \
  --duration=4.5 --fps=30 --viewport=1080,1920 \
  --transparent-background \
  --output=01_opener.mov \
  --output-options="-c:v prores_ks -profile:v 4 -pix_fmt yuva444p10le" \
  --launch-arguments="--no-sandbox"
```

输出 ~80MB / 4.5s。直接喂给 `recipes/compose_dual.sh.template` 的 `OVERLAYS` 数组。

> 用 `timecut` 而不是 `hyperframes render`，因为后者需要先 `hyperframes init` 建项目骨架；单 cp 出来的 html 用 timecut 一行就跑。已在 Node v25.9 实测通过。

## 字号调整（最常需要改的地方）

模板字号按「2 行短标题 + 1 行副标」调好的（`.title` 138px，`.sub` 56px）。如果文字溢出：

- **标题任一行 wrap 了**：把 `.t1` / `.t2` **一起**降到 110–120px（保持两行配对，单边变小看着 broken）
- **副标题太长**：`.sub` 从 56px 降到 44–48px，或把副标拆短
- 中文斜体用 `transform: skewX(-8deg)`（**不是** CSS `font-style: italic`，中文合成斜体丑）

## 0s 默认位置

**标题卡永远叠在视频 0s**——即使口播在 22s 才说到这个 phrase，标题仍在 0s 出。除非用户**明说**"标题在 X 时刻出"才改位置。

## 视觉规范

所有 opener 文字必须遵守 `../CONVENTIONS.md` 的 **9:16 安全区**（顶部 10% 留空、文本块在 top-third）+ Hana 调色板。
