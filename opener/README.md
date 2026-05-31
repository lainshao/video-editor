# opener · 标题卡子模块

4.5s 1080×1920 标题卡，**透明 alpha** 叠在 talking head 顶部第三方位（不替换主持人）。渲染为 ProRes 4444 alpha mov，喂给 `recipes/compose_dual.sh.template`。

**不走三道门** —— 这是单点操作，4 输入 + 渲染 = 完事。

## 两个模板

| 模板 | 视觉 | 适用 |
|---|---|---|
| **`gold.html`** | 透明背景 · 白字 + 6 段金属渐变金色关键词（`#6e5a1f → #b89a3e → #f5e6a8 → #d8b95a → #8a722a → #5a4715`）· clip-path wipe + diagonal shimmer + breathing | **拉美 / 巴西 / 出海 / 泛文化系列**。默认 |
| **`yellow.html`** | 砖红底 `#cc6b49` · 纯黄字 `#ffd12e`（实心非渐变）· 黄色衬线大字 + 顶部 logo + 白色斜体副标 | **AI / Claude Code / "AI 101" 扫盲系列**。砖红底是不透明模式 |

**怎么选**：

| 用户原话 | 模板 |
|---|---|
| "片头" / "标题卡" / "opener"（无品牌指向） | 默认 **gold.html** |
| "拉美系列" / "巴西" / "出海" / "金色关键字" / "Hana 风" | **gold.html** |
| "AI 系列" / "Claude Code" / "黄字片头" / "砖红底" / "AI 101" | **yellow.html** |

## 4 个输入

| Slot | 内容 | 例子 |
|---|---|---|
| `eyebrow` | 顶部小标签（series tag） | `— 出海笔记` / `— AI 101` / `— SERIES 03` |
| `line1` | 第一行白色大字（设问前半） | `什么人` / `How to build a` |
| `line2` | 第二行白色大字（设问后半） | `适合做` / `business with` |
| `keyword` | 金色/黄色关键字（点题） | `国际化？` / `creative` |

**视觉钩子**：`keyword` 最后落地、看着 expensive，前面是铺垫。选**真正点题**的词当 keyword，不要选连接词。

## 用法

```bash
# 1. cp 模板进项目
cp ~/.claude/skills/video-editor/opener/gold.html  my_project/opener/01_opener.html
# 或
cp ~/.claude/skills/video-editor/opener/yellow.html my_project/opener/01_opener.html

# 2. 编辑：替换 {{EYEBROW}} / {{LINE1}} / {{LINE2}} / {{KEYWORD}}

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

## 字号调整（最常需要改的地方）

模板字号按"3–6 char 中文 / 2–3 word 英文 keyword"调好的。如果文字溢出：

- **短 keyword**（1–3 中文字 / ≤6 英文字符）：默认 `font-size: 210px`，可冲 230–250px
- **中等 keyword**（4–6 中文字 / 7–10 英文字符）：210px 边界，验证不溢就用，否则降到 180–190px
- **长 keyword**（7+ 中文字 / 11+ 英文字符）：降到 140–170px，并劝用户**拆短**——`keyword` 太长就失去 punchline 感
- **`line1` / `line2`**：任何一行 wrap 了就**一起**降到 140px（保持配对，单边变小看着 broken）

斜体效果用 `transform: skewX(-6deg)` GSAP tween（**不是** CSS `font-style: italic`，中文合成斜体丑）。

## 0s 默认位置

**标题卡永远叠在视频 0s**——即使口播在 22s 才说到这个 phrase，标题仍在 0s 出。除非用户**明说**"标题在 X 时刻出"才改位置。

## ⚠ Node 版本

`timecut` / `hyperframes` 需要 Node ≥ 22 < 25。Node 25 有静默 init 失败的已知坑——遇到立刻降版。

## 完整短视频配方

`references/video-template-hana.md` 是这个 opener 所嵌入的**完整 9:16 短视频模板**：opener → talking head with B-roll overlays → big captions → CTA。如果用户要"做整个短视频"而不是只要 opener，参考这个文档。

## 视觉规范

所有 opener 文字必须遵守 `../CONVENTIONS.md` 的 **9:16 安全区**（顶部 y=0–250 死区、文本块 `padding-top: 280px` 在 top-third）+ Hana 调色板。
