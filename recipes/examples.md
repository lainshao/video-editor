# Worked examples — scene types from 出海系列

> **For external users**: these examples come from the original author's real project
> (a Chinese 9:16 short-form series called「出海」on going-abroad / global topics).
> File paths and series names reference the author's local project structure —
> they're kept here as **visual & structural reference**, not as a working dataset.
>
> Use these as a "look at how the original author solved problem X" library;
> copy the **structure / HTML / animation pattern** into your own project,
> not the literal paths.

Concrete reference for designing new B-roll scenes. Each is a real composition that shipped in the 出海系列 project. Copy the structure, swap the content.

## 1. Word + Red X (negation)
**Use case**: "默认答案不是英文" — strike out a wrong answer.
**Visual**: huge word at center, red X drawn over it via SVG line stroke.
```html
<div class="word">英文
  <svg class="x-svg">
    <line class="x-line" x1=80 y1=80 x2=720 y2=520/>
    <line class="x-line" x1=720 y1=80 x2=80 y2=520/>
  </svg>
</div>
<div class="caption">默认答案 ≠ 真答案</div>  <!-- top: 280px (避顶部 UI 死区) -->
```
Animation: word `back.out(1.4)` bounce in → SVG stroke draw via `strokeDashoffset 1000→0`.

## 2. Compare 2 cards (vs)
**Use case**: 表象 vs 根因.
```html
<div class="compare">
  <div class="col neg"><h3>表象</h3><div class="val strikethrough">英文</div></div>
  <div class="vs">vs</div>
  <div class="col pos"><h3>根因</h3><div class="val">?</div></div>
</div>
```
neg col: red border-top + strikethrough. pos col: yellow border-top.
Animation: left card slides x:-120, right slides x:120, "vs" `scale:0 rotation:-180` pop.

## 3. Forbidden symbol over keyboard keys
**Use case**: "不能直接 Copy & Paste".
```html
<div class="keys">
  <div class="key">⌘ C</div>
  <div class="key">⌘ V</div>
</div>
<div class="ban"></div>  <!-- circle + diagonal line via CSS -->
```
keys: white card + bold border + hard shadow (key-cap look).
ban: 500px circle, 12px red border, ::after pseudo for diagonal.

## 4. Medal + X (false reward)
**Use case**: 镀金 — the "for-show only" warning.
Radial gradient gold disc + label "镀金" + red X overlay.
Background: `radial-gradient(#FFE38A → #F2C94C → #B58E1F)`.

## 5. Three icons in a row (life changes)
**Use case**: 朋友圈 / 社交圈 / 外卖 — three things that change.
```html
<div class="emoji-row">
  <div class="item"><div class="icon">👥</div><div class="item-label">朋友圈</div></div>
  <div class="item"><div class="icon">📞</div><div class="item-label">社交圈</div></div>
  <div class="item"><div class="icon">🥡</div><div class="item-label">外卖</div></div>
</div>
```
Each item: 200px white circle + soft shadow. Stagger fall-in 200ms `back.out(1.6)`.

## 6. Data bars (comparison)
**Use case**: 100% 恐惧 vs 0% 期待 — dual progress bars.
```html
<div class="bars">
  <div id="fear">
    <div class="bar-row"><div class="bar-label">恐惧</div><div class="bar-pct">100%</div></div>
    <div class="bar-track"><div class="bar-fill"></div></div>
  </div>
  <div id="hope">…</div>
</div>
```
Animation: red fill width `0% → 100%` + count-up `innerText 0→100` simultaneously.

## 7. Checklist (no burdens)
**Use case**: 无负担清单 — list of crossed-out items.
White rounded panel, panel-title at top, 3 items with red ✗ + strikethrough text.
Stagger items in `x:-60 opacity:0 back.out(1.4)` 250ms apart.

## 8. Role progression with arrow
**Use case**: IC → 管理者.
Two role pills + SVG arrow between.
- before pill: white bg + grey border + muted text
- after pill: yellow bg + ink text + heavy box-shadow
- arrow: stroke-dasharray draw animation

⚠️ **WIDTH GOTCHA**: 4-char Chinese role at 140px overflows. Use 110px + `padding: 20px 44px` + `white-space: nowrap`. (See PITFALLS.md.)

## 9. Gold quote (summary)
**Use case**: "在不确定中找到节奏 / 在混沌中保持好奇心".
```html
<div class="lead">引言文字（muted）</div>
<div class="quote-block">
  <div class="quote-line line1">在不确定中<span class="hi">找到节奏</span></div>
  <div class="quote-line line2">在混沌中保持<span class="hi">好奇心</span></div>
</div>
<div class="corner-mark tl">"</div>
<div class="corner-mark br">"</div>
```
`.hi` = yellow capsule (`background: var(--accent); padding: 6px 22px; border-radius: 18px`).
corner-mark: 320px Georgia serif quote, 25% opacity.

## 10. Title (transparent overlay)
**Use case**: "天选出海人 / 都有这 / 三个特质".
- 4.5s composition
- Eyebrow (small uppercase label)
- 2 lines white text (168px)
- Keyword: gold metallic gradient (6-stop), 210px, skewX -6° via GSAP transform
- Reveals: clip-path wipe + diagonal shimmer + subtle breathing pulse
- Background: transparent + soft elliptical dark vignette behind text (so white reads on light footage)

See `~/.claude/skills/broll-opener/assets/template.html` for the full template.

## 11. Chyron text (yellow capsule)
**Use case**: Be Humble / Be Curious / Be Bold / 敢于冒险的年轻人 etc.
- 1.5–2.0s composition
- **Top safe zone** (`top: 16%` center, y≈307) — chyron pill top edge ≈ y=237，避开 y<250 顶部 UI 死区（刘海/Dynamic Island/平台关注按钮）
- Yellow capsule + 4° skew + bold ink text
- pop animation: `from {opacity:0, y:24, scale:0.9}` 0.22s power3.out → hold → fade-out 0.30s power2.in
- 卡片阴影只用 `rgba(0,0,0,X)` 中性灰，**不用 `rgba(60,40,0,X)` brown** —— brown 在暗背景上像"金色光晕"被嫌弃过

See `~/.claude/skills/broll-compose/templates/chyron.html`.
