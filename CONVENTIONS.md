# Video Editor 视觉规范（共用 · 必读）

这份文档是 video-editor 三个子模块（opener / animator / subtitle）的**共用视觉约束**。任何一个子模块写 HTML / 渲染 / 烧字幕之前都必须遵守这里的规则。

---

## 一、画布

- **唯一支持比例**：9:16 portrait，**1080×1920** canvas（v1）
- 16:9 横屏：v2 roadmap，目前不支持
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

**层级公式（每级 ~30-40% 跳跃）**：

| Tier | px | 用途 | 示例 |
|---|---|---|---|
| **Display** | 96-110 | 主标题（每张卡只能 1 个） | "巴西 10 天" |
| H1 | 48-56 | 卡片标题 / Phase 标题 | "圣保罗·缓时差" |
| H2 | 40-48 | 段落 marker / 强调数字 | "D1-2" |
| H3 | 36-40 | 卡片内子项标题 | "千湖沙漠" |
| Body-L | 30-32 | 副标 / callout 标题 | "里约压最后·圣保罗起步" |
| Body-M | 26-30 | 正文描述 | "巴西+阿根廷两侧都要去" |
| Caption | 22-26 | 数据来源 / footer / 标签小字 | "数据来源：…" |
| Icon | 40-48 | emoji 装饰图标 | 🐆 📷 🌴 |

**例外**：chyron 黄胶囊（黄底 + 4° skew）已经是 96-130px 显眼字号，不在这个层级表里。

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
