"""subtitles.py — shared subtitle rendering core (libass-free).

This ffmpeg build may lack libass (no `subtitles`/`ass` filter), so captions
are rendered to transparent PNGs with Pillow (semi-transparent black rounded
box, white text, yellow keywords) and overlaid via ffmpeg's `overlay` filter.

Used by:
  - compose.py        — in-pipeline subtitles (timed via script alignment)
  - add_subtitles.py  — standalone post-edit subtitles (timed via whisper segments)

Style is tuned to match the reference (bottom-third, lifted above platform UI).
"""
import re
from pathlib import Path

# ---- style ----
SUB_FONT_SIZE = 52          # 用户规定 2026-07-11：字幕改小，给抠像人像让位
SUB_MARGIN_V = 375          # px from bottom of 1920 canvas (clears platform UI / lower-third)
SUB_BOX_ALPHA = 165         # 0-255; ~65% opaque black box
SUB_PAD_X = 30
SUB_PAD_Y = 14
SUB_RADIUS = 16
SUB_WHITE = (255, 255, 255, 255)
SUB_YELLOW = (255, 211, 32, 255)   # warm gold like the reference
SUB_MAX_W = 660             # px; 左右各留 210px 抠像走廊（用户规定 2026-07-11），超宽在标点处分段


def find_cjk_font(size: int):
    from PIL import ImageFont
    # (path, ttc_index) — prefer bold/semibold CJK faces
    candidates = [
        ('/System/Library/Fonts/PingFang.ttc', 4),   # PingFang SC Semibold
        ('/System/Library/Fonts/PingFang.ttc', 2),
        ('/System/Library/Fonts/PingFang.ttc', 0),
        ('/System/Library/Fonts/Hiragino Sans GB.ttc', 1),
        ('/System/Library/Fonts/STHeiti Medium.ttc', 0),
        ('/Library/Fonts/Arial Unicode.ttf', 0),
    ]
    for path, idx in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size, index=idx)
            except Exception:
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
    return ImageFont.load_default()


def segment_caption(text: str, keywords=None):
    """Split a caption into [(segment, is_keyword), ...].
    Honors **bold** markers first, then exact keyword substrings."""
    runs = []
    pos = 0
    for m in re.finditer(r'\*\*(.+?)\*\*', text):
        if m.start() > pos:
            runs.append((text[pos:m.start()], False))
        runs.append((m.group(1), True))
        pos = m.end()
    if pos < len(text):
        runs.append((text[pos:], False))
    if not runs:
        runs = [(text, False)]
    if not keywords:
        return runs
    # split the non-keyword runs further by exact keyword matches
    kws = sorted([k for k in keywords if k], key=len, reverse=True)

    def split_seg(seg):
        out = [(seg, False)]
        for kw in kws:
            nxt = []
            for s, is_kw in out:
                if is_kw or kw not in s:
                    nxt.append((s, is_kw))
                    continue
                parts = s.split(kw)
                for i, p in enumerate(parts):
                    if p:
                        nxt.append((p, False))
                    if i < len(parts) - 1:
                        nxt.append((kw, True))
            out = nxt
        return out

    result = []
    for seg, is_kw in runs:
        if is_kw:
            result.append((seg, True))
        else:
            result.extend(split_seg(seg))
    return result


_SPLIT_PUNC = "，、。：；,"   # CJK 断句标点：超宽句优先在此切，最自然


def split_overwide_captions(timed, max_w=SUB_MAX_W):
    """把单行渲染宽度超过 max_w 的字幕拆成多条顺序子字幕，时长按字数比例切。
    切点优先级：中文标点(切在标点后) → 空格 → 字符中点。递归处理超长句。
    timed: [(text, start, end), ...]，text 可含 **bold** 标记。返回新的 timed。

    无空格/无标点的纯 CJK 长句也能切（按字符中点），避免 PNG 比画面宽被裁。
    """
    from PIL import Image, ImageDraw
    font = find_cjk_font(SUB_FONT_SIZE)
    pd = ImageDraw.Draw(Image.new('RGBA', (10, 10)))

    def width(s):
        try:
            return pd.textlength(s, font=font)
        except Exception:
            bb = pd.textbbox((0, 0), s, font=font)
            return bb[2] - bb[0]

    def split_point(txt):
        mid = len(txt) // 2
        for pool, after in ((_SPLIT_PUNC, True), (' ', False)):
            best, bestd = None, 10 ** 9
            for i, ch in enumerate(txt):
                # 句尾标点不能当切点——切完一边是空串，rec 会放弃分段（历史 bug）
                if ch in pool and abs(i - mid) < bestd and 0 < i < len(txt) - 2:
                    best, bestd = i, abs(i - mid)
            if best is not None:
                cut = best + 1 if after else best
                return txt[:cut].strip(), txt[best + 1:].strip()
        # 字符中点兜底：切点不许落在英文/数字单词内部（Claude→Claud/e 的历史 bug）
        i, j = mid, mid
        def in_word(k):
            return 0 < k < len(txt) and txt[k - 1].isalnum() and txt[k].isalnum() \
                and (ord(txt[k - 1]) < 0x2E80 or ord(txt[k]) < 0x2E80)
        while in_word(i) and i > 1:
            i -= 1
        while in_word(j) and j < len(txt) - 1:
            j += 1
        cut = i if (mid - i) <= (j - mid) else j
        return txt[:cut].strip(), txt[cut:].strip()

    def rec(text, st, en):
        plain = text.replace('**', '')
        if width(plain) + SUB_PAD_X * 2 <= max_w or len(plain) < 8:
            return [(text, st, en)]
        a, b = split_point(text)
        # 不切坏 **bold** 配对，也不产生空串
        if not a or not b or a.count('**') % 2 or b.count('**') % 2:
            return [(text, st, en)]
        la, lb = len(a.replace('**', '')), len(b.replace('**', ''))
        midt = st + (en - st) * (la / max(1, la + lb))
        return rec(a, st, midt) + rec(b, midt, en)

    out = []
    for text, st, en in timed:
        out.extend(rec(text, st, en))
    return out


def render_subtitle_pngs(timed, keywords, out_dir: Path, total_duration: float):
    """Render each caption to a transparent PNG. Returns
    [{'png': Path, 'start': float, 'end': float}, ...] sorted by start.

    timed: list of (text, start_s, end_s). text may contain **bold** markers.
    keywords: list of substrings to colour yellow.
    """
    from PIL import Image, ImageDraw
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob('sub_*.png'):
        old.unlink()
    timed = split_overwide_captions(timed)   # 超宽句自动按标点拆分，避免被裁
    font = find_cjk_font(SUB_FONT_SIZE)
    probe = Image.new('RGBA', (10, 10))
    pd = ImageDraw.Draw(probe)
    asc, desc = font.getmetrics() if hasattr(font, 'getmetrics') else (SUB_FONT_SIZE, 0)
    line_h = asc + desc

    events = []
    idx = 0
    for text, start, end in timed:
        if end <= start or start >= total_duration:
            continue
        end = min(end, total_duration)
        runs = segment_caption(text, keywords)
        seg_w = []
        for seg, _ in runs:
            try:
                w = pd.textlength(seg, font=font)
            except Exception:
                bb = pd.textbbox((0, 0), seg, font=font)
                w = bb[2] - bb[0]
            seg_w.append(w)
        text_w = sum(seg_w)
        box_w = int(text_w + SUB_PAD_X * 2)
        box_h = int(line_h + SUB_PAD_Y * 2)
        img = Image.new('RGBA', (box_w, box_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, box_w - 1, box_h - 1], radius=SUB_RADIUS,
                            fill=(0, 0, 0, SUB_BOX_ALPHA))
        x = SUB_PAD_X
        for (seg, is_kw), w in zip(runs, seg_w):
            d.text((x, SUB_PAD_Y), seg, font=font,
                   fill=(SUB_YELLOW if is_kw else SUB_WHITE))
            x += w
        png = out_dir / f'sub_{idx:03d}.png'
        img.save(png)
        events.append({'png': png, 'start': start, 'end': end})
        idx += 1
    return sorted(events, key=lambda e: e['start'])


def overlay_filtergraph(events, base_label='0:v', first_img_idx=1, out_label='vout',
                        margin_v=SUB_MARGIN_V):
    """Build the chained ffmpeg overlay filtergraph for subtitle PNGs.
    Returns (filter_parts:list[str], n_inputs:int). Image inputs are expected
    at [first_img_idx], [first_img_idx+1], ... in input order."""
    parts = []
    cur = base_label
    for i, ev in enumerate(events):
        img_idx = first_img_idx + i
        lbl = out_label if i == len(events) - 1 else f'_sub{i}'
        parts.append(
            f"[{cur}][{img_idx}:v]overlay=x=(W-w)/2:y=H-h-{margin_v}:"
            f"enable='between(t,{ev['start']:.3f},{ev['end']:.3f})'[{lbl}]")
        cur = lbl
    return parts, len(events)
