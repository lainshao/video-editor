# Video Editor 视觉规范（共用 · 必读）

这份文档是 video-editor 三个子模块（opener / animator / subtitle）的**共用视觉约束**。任何一个子模块写 HTML / 渲染 / 烧字幕之前都必须遵守这里的规则。

---

## 一、画布

两种画幅，由 video-editor **第零步路由**确定（SKILL.md）：

- **9:16 portrait** — **1080×1920**（抖音 / 小红书 / 视频号 / Reels）。平台 UI 安全区见第三节。
- **16:9 landscape** — **1920×1080**（YouTube / B站）。子模块模板、数据卡、新闻卡都按此画布出，compose 走 `recipes/compose_16x9.sh.template`。安全区宽松：四边各留 ~5% 边距、关键文字别贴边；底部留 ~12% 给平台进度条/字幕；**右下角默认留给 person-pip 小窗**（见第九节）。
- 帧率：30fps（HyperFrames / timecut 默认）
- 颜色空间：sRGB

---

## 二、Hana 调色板（默认 theme）

| 用途 | hex | 用在哪 |
|---|---|---|
| Canvas | `#FAF6EF` | 米底 scene card / chyron_underline 卡背景 |
| Ink | `#1A1A1C` | 深墨主文字 |
| Accent | `#F2C94C` | 黄胶囊 / marker / 重点强调 |
| Negative | `#E0454C` | 警示 / ❌ / 反向数据 |
| Positive | `#3FA672` | 正向 / ✓ |
| Muted | `#7C7468` | 次级 / 数据来源 footer |

字幕另用一个**暖金**（`#FFD320`）作为字幕关键词高亮色。这是历史遗留，开源前应统一进 Accent `#F2C94C` —— 但当前两者都还在用，先记录差异。

---

## 三、9:16 平台 UI 安全区 ★ 必读

**简单规则**：顶部 10% 留空、底部 15% 留空，文字内容别贴边。

| y 范围 | 用途 | 叠层规则 |
|---|---|---|
| **y = 0–192** (10%) | **顶部留空带** | ⛔ 不放任何要被读到的文字 / 数字 / 关键图标 —— 给 Dynamic Island / 刘海 / 状态栏 / 平台顶部 UI 留呼吸 |
| **y = 192–1632** (75%) | 主可用区 | 所有有意义的内容 —— 卡片 / 动画 / chyron / talking head face |
| **y = 1632–1920** (15%) | **底部留空带** | ⛔ 不放高光内容 —— 给自动字幕 / 账号名 / 点赞 / 商品卡 / CTA 留位置 |

**装饰元素**（burst emoji、orbs、grain 等）可以延伸进留空带，但**不能放任何要被读到的文字 / 数字 / 关键图标**。

**坐标速查（1080×1920 canvas）**：
- **10% = 192px**（顶部边界）｜ 16% = 307px（chyron 中心标准位）｜ 22% = 422px
- 50% = 960px ｜ 75% = 1440px
- **85% = 1632px**（底部边界）｜ 90% = 1728px

**历史细节**：早期版本用 13%/24% 的更紧规则、并打算实拍校准 iPhone 16 + 2025 平台 UI。后来简化为 10%/15%——本质是"内容不贴边"的工艺规则而不是精确的平台死区测量，足够覆盖各机型/平台变体，省去校准成本。

**模板里现成的位置常量**（保持对齐）：
- chyron pill: `top: 16%`（y≈307 中心 / pill 顶 ≈237 / 底 ≈377）
- cutaway 卡片顶边: `top: 280px`
- opener 文本块: `padding-top: 280px`

---

## 四、Chyron 默认样式

- **黄底胶囊** + 4° skew
- **130px 英文** / **96px 长中文**
- pop 动效：power3.out 弹入 + scale 0.9→1
- 默认时长 1.0–2.0s
- 同 type 字号统一：3 个英文 chyron 都同一字号，2 个长中文都同一字号

### Chyron + 动画 时序（避免重叠喧宾夺主）

cue 内有 chyron + 动画两个元素时，**默认走这个 3 段时序**：

```
0.0s  ─►  chyron 弹入 (back.out 0.35s)
1.0s  ─►  chyron 淡出 (power2.in 0.35s) ┬─ 同时动画开始进场
                                        └─ 让 chyron 不和动画长期同屏
...  ─►  动画播放完毕
end   ─►  动画淡出 (power2.in 0.40s)
```

**Why**：chyron + 动画长期同屏视觉繁杂。先重点字 solo 1s 立住信息，再淡出让动画接力。

**例外**：cue 只有 chyron 没动画（如片尾预告 chyron）→ chyron 保留到 cue 结束。

### 顶边对齐（chyron pill → 动画 容器）

chyron 淡出 + 动画 fade in 的过渡瞬间，**两者顶边应该重合**，否则用户会看到 chyron 的边缘"露出来"再被覆盖：

- chyron pill 顶边 ≈ y=250（`top:16%` 中心 ≈ y=307，pill_height ~140，顶边 ~y=237）
- 动画容器**顶边也设为 y=250–280**：
  - 卡片型（绝对定位）：`top: 280px`
  - 中心锚 + `translate(-50%,-50%)`：`top: (250 + height/2) / 1920 * 100%`，常见 `top: 18%`–`top: 22%`

---

## 五、字号层级（cutaway 整页 + 卡片型）

9:16 视频在手机上播放，1080×1920 canvas 缩到 ~390px 宽，**scale ≈ 0.36**。canvas 上 14px 文字 → 手机上看 ~5px，不可读。

**最小字号底线：22px**（手机上 ~8px，刚好读得清）。所有数据来源 / footer 类小字不低于这个值。

**层级阶梯 —— 固定值，不是区间。同一个语义角色，全模板必须同一个号**（区间会让每个模板各取一个值、互相漂移，这是历史上"列表项名 listicle=92 / progressive=64"不一致的根因）：

| Token | px | 用途 | 示例 |
|---|---|---|---|
| **Hero** | 138 | opener 开场大标题（仅开场卡） | "Claude Code" |
| **Display** | 96 | 整页主标题 / recap 标题 / 总结金句大字（每张卡只 1 个） | "这 5 个景点" |
| **H1** ★基准 | 72 | 列表项主名 / 卡片标题 | "圣保罗·缓时差" |
| H2 | 56 | 次级标题 / 强调数字 / 圆圈编号 | "D1-2" / "①" |
| H3 | 44 | 卡片内子项标题 | "千湖沙漠" |
| Body | 32 | 副标 / 描述 / callout | "里约压最后·圣保罗起步" |
| Caption | 24 | 数据来源 / footer / 角标小字（**地板，不再低**） | "数据来源：…" |

**Icon 单独一条轨**（emoji 装饰图标，不混进文字阶梯）：`XL 140 / L 96 / M 64`。

**配套属性跟字号绑定**（别再凭手感给 letter-spacing / line-height）：
- 大字（≥72）：`letter-spacing: -0.02em`；`line-height: 1.0–1.1`（紧）
- 正文（≤32）：`letter-spacing: 0`；`line-height: 1.3–1.4`（松）
- 全大写英文 / 眉签：`letter-spacing: +0.08–0.18em`

**例外**：chyron 黄胶囊（黄底 + 4° skew）已经是 96-130px 显眼字号，不在这个层级表里。

---

### 五·B 行宽 / 换行（长文案不许撑满左右）★

字数一多就贴边、零留白，是因为"字号钉死、文案一长只能往边上顶"。正确顺序是 **先降号、再换行，永远不动 80px 安全边**：

1. **大标题（≥72）设 `max-width: 840px; margin: 0 auto;`** —— 比 920 安全框再内缩一档，两侧永远留得出可见留白。留白是设计，不是浪费。
2. **中文大标题每行 ≤ 12–14 字**。超了：① 先在语义停顿处主动 `<br>` 断行（**别在词中间断**）；② 还挤就**降一档字号**（96→72→56）。
3. **最多 2 行**。一句标题撑到 3 行 = 字号选大了或文案该砍。
4. **绝不靠缩小左右边距硬塞**。横向边距全模板统一 **80px**（不是 64）。

### 五·C 间隔网格（8px 基准）

所有 `gap / padding / margin` 只取 8 的倍数：**8 / 16 / 24 / 32 / 48 / 64 / 80**。禁止再出现 12 / 26 / 36 / 42 / 50 / 52 这种手感值。行内间隙 24–32、堆叠行距 24、卡片内边距 48、标题→副标 16。

---

## 六、Cutaway 多段时间轴 / 决策表

口播逐段讲多段（如 D1-2 → D3-4 → D5-8 → D9-10）时，**不要把所有段一锅炖在屏上**让观众扫，走 PPT 投影式逻辑：

1. **标题区永远只放核心 1 行**（如「巴西 10 天」），不要堆叠 eyebrow + title + subtitle 三层 —— 信息过载
2. **顶部 day-strip 当进度条**：4-6 个格子，灰底默认，口播讲到哪段就高亮哪格（涂彩色 + box-shadow）
3. **主舞台一次只显示一张 phase-card**：`position: absolute; inset: 0; opacity: 0`，切换时 `opacity 0 ↔ 1` 0.6s 过渡
4. **inactive 段彻底隐藏**（opacity 0），**不**用 dim grey
5. **当前段卡片充满主舞台**：D-label 90+px、headline 70+px、desc 35+px

同样的范式也适用于"5 段对比"、「决策矩阵分屏」、"Q&A 列表"之类口播 walk-through cutaway。

**Why**：视频是流不是页，观众不能"暂停扫"，所以一次只投影一段比 dim-grey 全显更清晰。

---

## 七、Climax / 收尾段强调：避免大块满色背景

最后一段（"压轴" / final / climax phase）想视觉上区分时，**不要用整块高饱和色填满卡片**（如纯黄、纯红、纯橘渐变）。

**正确做法**：
- 主体白底（跟其他段一致）+ 浅色 tint gradient（如 `linear-gradient(180deg, #FFFBEB 0%, #FFFFFF 60%)`）
- **彩色 accent 集中在边框 + 角标 ribbon**（合计约 5% 屏占）：
  - 3px solid 国旗色边框（黄/绿/红任一）
  - 右上 ribbon `position: absolute; top:0; right:0; border-radius: 0 0 0 16px;` 写「压轴 / FINAL / 收官」
- 文字保持深色（黑/灰）保证可读
- 主色 accent（如 D-label）跟前段一致

**Why**：高饱和满色背景 ① 跟前 N 段视觉断裂感太强 ② 大色块易盖过文字读不清 ③ 看着廉价/促销感重。Ribbon + 边框的 5% accent 已足够"特殊"标记。

---

## 八、其他视觉硬规则

- **卡片阴影只用中性灰**：`box-shadow: 0 10px 28px rgba(0,0,0,0.18)`（或近似）—— **不要用 brown `rgba(60,40,0,X)`**，brown shadow 在暗背景上像"金色光晕"
- **不出现 debug 角标**：成片绝不留 `.scene-label`
- **Caption 是 takeaway / 结论**，heading 是设问；结论上、设问下
- **Trio listicle 双叠**：每项叠两次（trio reveal + section start）
- **长信息（5+ 项）默认用 `scene_progressive_top_card.html`**（卡片渐进出现 + 末尾 recap），不要用 6s+ 全屏 listicle —— 后者阻塞 talking head 节奏断
- **群体 emoji 啪啪啪用 `scene_burst_emoji.html`**（透明叠 + drop-shadow），**不加 radial vignette 暗罩** —— 暗罩叠 talking head 脸上视觉怪

---

## 九、Theme 系统 · C 方案（参考文档版）

`themes/` 目录已建好，作为 **canonical 参考文档** —— **不是模板加载的依赖文件**：

```
themes/
├── _base.css     ← 结构性 CSS 标准（viewport / 容器 / safe zone 常量 / 字号层级）
└── hana.css      ← Hana 调色板 + 字幕/opener 子集色值
```

### 为什么不抽成真正的 CSS 共享文件

抽真正共享会让模板必须配 `themes/` 文件夹才能渲染（cp 模板时多一步），换来的 dedup 只有 ~90 行。性价比不值。所以走"参考文档"路线：

- **模板继续自包含** —— 每个 `<style>` 块内联自己的 `:root` 和结构 CSS。cp 一个文件就能用
- **`themes/_base.css` 和 `themes/hana.css` 是"色卡参考书"** —— 写新模板时照着抄；将来批量改色时也照着改

### 想换皮肤怎么办

1. 复制 `themes/hana.css` 为 `themes/my-brand.css`，改色值
2. 在所有用到该色的模板 `<style>` 里找 `--canvas / --ink / --accent` 等替换
3. 批量替换可以靠 `sed` 或 IDE 全局替换

### 升级到 A 方案（真共享）的路径

将来如果决定换 A 方案（节省 cp 时的麻烦虽然不大，但也算正经基础设施）：

1. 写一个 `recipes/bootstrap_cue.sh`：cp 模板时自动 cp `themes/` 到项目根
2. 把所有模板 `<style>` 顶部的 `:root` 块 + 结构 CSS 删掉，改成 `<link href="../themes/_base.css">` + `<link id="theme" href="../themes/hana.css">`
3. 改 README 说明 cp 要带上 themes/
4. 切 theme = 改 `<link id="theme">` 的 href

`themes/` 现在的两个文件已经是 A 方案所需的格式，将来无缝升级。

---

## 十、模板契约（写新模板 / 改老模板必须满足）

`opener/` 和 `animator/` 下每个 `.html` 模板都必须满足以下契约，否则在 `gallery.html` / `spec_review.html` 等 iframe 预览场景会出现"黑卡"、"被切"、"溢出"等 silent bug。`recipes/lint_template.sh` 会做静态检查。

### A · 结构层（必须）

| 项 | 要求 | 不满足的后果 |
|---|---|---|
| viewport meta | `<meta name="viewport" content="width=1080, height=1920" />` | HyperFrames 渲出来分辨率不对 |
| 根容器 | 含 `[data-composition-id="main"]` 的 `<div>`，带 `data-start` / `data-duration` / `data-width="1080"` / `data-height="1920"` 属性 | HyperFrames 找不到"渲哪一段" |
| `<html>` / `<body>` | `width:1080px; height:1920px; overflow:hidden; background:transparent` | 渲染时多余白边 / alpha 丢失 |
| 字体栈 | `"Inter", "Noto Sans SC", "PingFang SC", system-ui, sans-serif` 顺序（CJK 后兜底）| 中英文混排断字 |

### B · 动画层（必须）

| 项 | 要求 | 不满足的后果 |
|---|---|---|
| GSAP CDN | `<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js">` | 动画跑不起来 |
| 时间线注册 | `window.__timelines["main"] = tl;` —— HyperFrames 通过这个对象 seek | HyperFrames 渲不出 |
| **autoplay 钩子** | 末尾必须有：<br>`window.addEventListener("load", function () {`<br>`  if (!window.__hyperframes_runtime) { tl.play(); }`<br>`});` | **iframe 预览黑屏**（这次 cue 5-8 踩的坑）|

### C · 安全区（必须）

| 项 | 要求 | 不满足的后果 |
|---|---|---|
| 顶部文字 | `top: ≥192px` 或 `padding-top: ≥192px` | 被刘海 / 状态栏切 |
| 底部文字 | `bottom: ≥288px` 或不进 y>1632 | 被自动字幕 / 商品卡盖 |
| 文字宽度 | 单行文字宽度 ≤ 920px（canvas 1080 − 边距 80×2）| 字溢出 canvas（cue 9 / 11 踩过）|

### D · 视觉规范（必须）

| 项 | 要求 |
|---|---|
| `:root` 含 Hana 调色板 | `--canvas / --ink / --accent` 至少 |
| 阴影只用中性灰 | 禁 `rgba(60,40,0,X)` brown shadow（暗背景上像金光晕）|
| 无 debug 角标残留 | 不能留 `.scene-label` 在成片 |

### E · 占位符（写模板时）

| 项 | 要求 |
|---|---|
| 占位符语法 | `{{NAME}}` 全大写 + 下划线，如 `{{TITLE}} / {{EYEBROW}} / {{KEYWORD}}` |
| 凡是面向使用者的可变文案/数字 | 必须做成占位符，不能 hardcode |
| 模板顶部注释 | 必须列出全部占位符 + 推荐输入范围 |

### F · 跑 lint

加新模板 / 改老模板前：

```bash
bash recipes/lint_template.sh animator/chyron/my_new_chyron.html
# 输出：
# ✓ viewport / 根容器 / 字体栈 ...
# ✓ GSAP / __timelines / autoplay
# ✗ 字符串 "Lorem ipsum" 看起来是英文占位，应改用 {{...}} 占位符
# ✗ 检测到 brown shadow rgba(60,40,0,...)，违反阴影规则
```

把每个检查项写成"过 / 不过"二元判定，绿灯才能 cp 给用户用。

---

## 八、渲染 QA 原则（轻量 · 必读）

QA 是为了"早发现错、少返工"，不是仪式。原则是**便宜的先验、贵的后做**：

1. **排版验在 HTML 截图阶段，别等渲完视频才验。** HTML 在无头 Chrome 截一张静帧 ~1 秒；渲 mp4/mov 要几十秒。文字溢出、撞标题、字号、配色这类**布局错，截图阶段就该抓**，过了再渲视频——省掉整个"渲→发现错→重渲"循环。（真实教训：数据图 `$50` 撞副标题，渲完才发现、白渲一次。）
2. **一批一张 contact sheet，读一次。** 别每个素材都"渲→抽帧→读图"逐个验。一批做完，抽各自关键帧拼**一张** contact sheet 一次过（`montage *.png -tile NxM`，中文文件名/字体警告无害）。
3. **信任已验证的模板，只抽检。** 同模板出的第 2、3 张（如第二张 news 卡），管线已证明可用，不必逐张读图，抽检一张即可。
4. **不重复双验。** 一种 compose 方法**第一次**用，值得叠真底 QA（alpha 叠品红 / 叠口播）；方法验证过之后，后续只留一张预览 contact sheet 即可。
5. **唯一不能省**：交付 alpha 整轨 / person-pip 整片前，**把成品叠回真实底**抽 4–8 帧——HTML / spec_review 看不出 alpha 变灰、遮脸、timing 漂移，只有真底图叠加能看出（见 PITFALLS #23）。

口诀：**便宜验在前、一批一张图、信任老模板、别双验、交付前叠真底。**

---

## 九、person-pip 自动小窗/大窗（16:9）

适用：用户给一条**干净的、只有真人满屏的口播**（不带 demo/PPT；人脸录死在角落里的不算——那种没法后期缩放）。compose 按"画面上有没有内容"自动切人物大小：

- **没内容时** → 人物 **大窗**（满屏）。
- **有内容/动效时**（B-roll cutaway / 数据卡 / 新闻卡 / 全屏 chyron）→ 内容 **大窗**铺满，人物自动缩成**右下小窗**（圆角 + 细白描边，默认方形宽 ~26%、右下边距 ~64px）。

实现：`recipes/compose_16x9.sh.template` 的 `PERSON_PIP=1` 模式。人物口播是 base 轨；内容 cue 按时间码全屏 overlay；同一窗口再把 base 居中裁方、缩小、圆角，overlay 到右下（enable 取所有 cue 窗口的**并集**，所以 pip overlay 必须放在 content overlay **之后**才压在内容上）。圆角用 `geq` 算 alpha、描边用 `pad`。

小窗摆位：默认右下；若某张数据卡右下有内容（柱子/数字）会被挡，改摆左下、或那张卡不叠人物——这是 human-in-the-loop 的判断点，**渲前确认**。
