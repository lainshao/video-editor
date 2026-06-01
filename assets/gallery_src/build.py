#!/usr/bin/env python3
"""Fill mock (Thailand/AI) copy into templates + add deterministic ?t= seek shim,
write to gallery_src/. All copy is PLACEHOLDER — not real episode content."""
import re, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]   # skill root
SRC  = ROOT / "assets" / "gallery_src"

SEEK_SHIM = """
<script>
/* gallery render shim: ?t=SECONDS seeks the main timeline to a hero frame and pauses.
   Set __hyperframes_runtime at parse time so the template's own autoplay fallback skips. */
(function () {
  var p = new URLSearchParams(location.search);
  if (!p.has("t")) return;
  window.__hyperframes_runtime = true;
  window.addEventListener("load", function () {
    var tl = window.__timelines && window.__timelines.main;
    if (tl) { tl.pause(); tl.time(parseFloat(p.get("t"))); }
  });
})();
</script>
"""

def write(name, text):
    # inject shim right before </body>
    text = text.replace("</body>", SEEK_SHIM + "</body>", 1)
    (SRC / name).write_text(text, encoding="utf-8")
    print("wrote", name)

# ── opener (yellow.html already supports ?t=, just fill tokens) ──
t = (ROOT / "opener" / "yellow.html").read_text(encoding="utf-8")
t = t.replace("{{TITLE_LINE1}}", "泰国 10 天")
t = t.replace("{{TITLE_LINE2}}", "新手抄作业")
t = t.replace("{{SUBTITLE}}", "完整路线 + 避坑")
(SRC / "opener.html").write_text(t, encoding="utf-8")   # no shim needed
print("wrote opener.html")

# ── chyron (yellow pill) ──
t = (ROOT / "animator" / "chyron" / "chyron.html").read_text(encoding="utf-8")
t = t.replace("{{TEXT}}", "古城必去")
write("chyron.html", t)

# ── chyron_underline ──
t = (ROOT / "animator" / "chyron" / "chyron_underline.html").read_text(encoding="utf-8")
t = t.replace("{{PREFIX}}", "清迈").replace("{{KEYWORD}}", "古城必去")
write("chyron_underline.html", t)

# ── scene_listicle ──
t = (ROOT / "animator" / "cutaway" / "scene_listicle.html").read_text(encoding="utf-8")
t = t.replace("{{ITEM_1}}", "落地缓时差")
t = t.replace("{{ITEM_2}}", "古城慢游")
t = t.replace("{{ITEM_3}}", "海岛跳岛")
write("scene_listicle.html", t)

# ── scene_blank: fill caption/heading + a simple mock 3-chip visual ──
t = (ROOT / "animator" / "cutaway" / "scene_blank.html").read_text(encoding="utf-8")
t = t.replace("{{CAPTION_TEXT}}", "海岛<b>三选一</b>")
t = t.replace("{{HEADING_TEXT}}", "D5–8 这 4 天怎么排？")
visual = """
      <div style="display:flex;flex-direction:column;gap:28px;width:100%;max-width:760px;margin:0 auto;">
        <div style="display:flex;align-items:center;gap:28px;background:#fff;border:2px solid rgba(0,0,0,0.08);border-radius:20px;padding:30px 36px;box-shadow:0 8px 22px rgba(26,26,28,0.10);">
          <span style="font-size:72px;">📷</span><div style="font-size:48px;font-weight:800;">普吉岛 · 拍照</div></div>
        <div style="display:flex;align-items:center;gap:28px;background:#fff;border:2px solid rgba(0,0,0,0.08);border-radius:20px;padding:30px 36px;box-shadow:0 8px 22px rgba(26,26,28,0.10);">
          <span style="font-size:72px;">🐘</span><div style="font-size:48px;font-weight:800;">象岛 · 安静</div></div>
        <div style="display:flex;align-items:center;gap:28px;background:#fff;border:2px solid rgba(0,0,0,0.08);border-radius:20px;padding:30px 36px;box-shadow:0 8px 22px rgba(26,26,28,0.10);">
          <span style="font-size:72px;">🌴</span><div style="font-size:48px;font-weight:800;">苏梅岛 · 跳岛</div></div>
      </div>
"""
t = t.replace('<div class="visual">', '<div class="visual">' + visual, 1)
# remove the now-stale comment block inside visual (harmless, leave)
write("scene_blank.html", t)

# ── scene_progressive_top_card: replace SPOTS/RECAP with Thailand mock ──
t = (ROOT / "animator" / "cutaway" / "scene_progressive_top_card.html").read_text(encoding="utf-8")
spots_new = """const SPOTS = [
  { num: "01", icon: "🛕",   name: "示例 · 曼谷",   sub: "占位副标 · 缓时差 · 大皇宫 + 夜市" },
  { num: "02", icon: "☕",   name: "示例 · 清迈",   sub: "占位副标 · 古城慢游 · 寺庙 + 咖啡" },
  { num: "03", icon: "🏝️",  name: "示例 · 海岛段", sub: "占位副标 · 三选一 · 普吉 / 象岛 / 苏梅" },
  { num: "04", icon: "💆",   name: "示例 · 按摩",   sub: "占位副标 · 收尾放松 · 夜市河滨" },
  { num: "05", icon: "✈️",   name: "示例 · 返程",   sub: "占位副标 · 购物收尾 · 机场退税" },
];"""
t = re.sub(r"const SPOTS = \[.*?\];", spots_new, t, count=1, flags=re.S)
recap_new = """const RECAP = {
  eyebrow: "示例 · 完整路线",
  mark: "✓",
  title: "泰国 10 天",
  footer: "示例占位文本 placeholder · 仅用于演示",
  in: 48.7,
  out: 50.3,
  rowStagger: 0.20,
};"""
t = re.sub(r"const RECAP = \{.*?\};", recap_new, t, count=1, flags=re.S)
write("scene_progressive_top_card.html", t)

# ── scene_burst_emoji ──
t = (ROOT / "animator" / "cutaway" / "scene_burst_emoji.html").read_text(encoding="utf-8")
t = t.replace('const LABEL = "示例 · X 密度极高";', 'const LABEL = "示例 · 庙宇遍地都是";')
t = re.sub(r"const ICONS = \[.*?\];",
           "const ICONS = ['🛕', '🙏', '🛕', '🛕', '🙏'];", t, count=1, flags=re.S)
write("scene_burst_emoji.html", t)

print("done")
