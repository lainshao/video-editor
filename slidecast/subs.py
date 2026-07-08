# -*- coding: utf-8 -*-
"""slidecast 字幕引擎

SRT → 米底胶囊 PNG（粗体 / 字间距 / 关键词橙色高亮 / 长行自动缩字号不超安全边）
→ 生成两个烧制脚本：burn_preview.sh（叠在米底预览上）、burn_alpha.sh（叠在透明帧轨上出 ProRes4444）。

本机 ffmpeg 无 libass/drawtext，所以字幕只能走 PNG overlay —— 这个脚本就是干这个的。

用法示例：
  python3 subs.py --srt transcript.srt --outdir subs/ \
     --base _noSub.mp4 --frames-list frames_list.txt \
     --preview-out 成片_预览.mp4 --alpha-out 成片_透明层.mov --total 208.6 \
     --keywords keywords.txt --corrections corrections.txt
"""
import re, os, math, argparse
from PIL import Image, ImageDraw, ImageFont

# ---- 样式默认值（贴 case-step 胶囊：米底 cream-deep + 深墨字 + 安全橙关键词）----
INK = (42, 31, 21, 255)
ORANGE = (232, 98, 44, 255)
CHIP = (240, 232, 212, 240)
PADX, PADY = 36, 20

def load_font(size):
    # 优先粗体字面（Hiragino Sans GB W6 / PingFang Semibold），配合 stroke 再加粗
    for path, idx in [("/System/Library/Fonts/Hiragino Sans GB.ttc", 1),
                      ("/System/Library/Fonts/PingFang.ttc", 6),
                      ("/System/Library/Fonts/PingFang.ttc", 4),
                      ("/System/Library/Fonts/PingFang.ttc", 2),
                      ("/System/Library/Fonts/PingFang.ttc", 0)]:
        try:
            return ImageFont.truetype(path, size, index=idx)
        except Exception:
            continue
    return ImageFont.load_default()

def read_lines(path):
    if path and os.path.exists(path):
        return [l.rstrip("\n") for l in open(path, encoding="utf-8") if l.strip() and not l.lstrip().startswith("#")]
    return []

def parse_srt(path, corrections):
    segs = []
    for b in open(path, encoding="utf-8").read().strip().split("\n\n"):
        L = b.split("\n")
        if len(L) < 3:
            continue
        m = re.match(r"(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)", L[1])
        if not m:
            continue
        g = list(map(int, m.groups()))
        start = g[0]*3600 + g[1]*60 + g[2] + g[3]/1000
        end = g[4]*3600 + g[5]*60 + g[6] + g[7]/1000
        text = "".join(L[2:]).strip()
        for pair in corrections:
            if "=" in pair:
                a, b2 = pair.split("=", 1)
                text = text.replace(a, b2)
        segs.append([start, end, text])
    return segs

def merge(segs):
    """whisper 分句已是短语级；只把极短碎片（≤4字 或 <0.9s）粘到相邻前句，保持每行是干净短语。"""
    out = []
    for s, e, t in segs:
        if out:
            ps, pe, pt = out[-1]
            if (len(t) <= 4 or (e - s) < 0.9) and (s - pe) < 0.4 and len(pt) + len(t) <= 18:
                out[-1] = [ps, e, pt + t]
                continue
        out.append([s, e, t])
    return out

def runs(text, keywords):
    mark = [False]*len(text)
    for kw in keywords:
        i = text.find(kw)
        while i != -1:
            for j in range(i, i+len(kw)):
                mark[j] = True
            i = text.find(kw, i+1)
    res = []; cur = ""; cm = None
    for ch, m in zip(text, mark):
        if cm is None:
            cm = m; cur = ch
        elif m == cm:
            cur += ch
        else:
            res.append((cur, cm)); cur = ch; cm = m
    if cur:
        res.append((cur, cm))
    return res

def build_contact_sheet(chips, out_path, rowH=84, colw=1180, per=27):
    """把全部字幕胶囊拼成一张 contact sheet，供出片前逐幕核验（字号/断词/关键词/错字）。
    chips: [(label, RGBA_img), ...]。3:4 壳帧不在此（壳在门 2 review 过）。"""
    if not chips:
        return
    CREAM = (245, 239, 225, 255)
    cols = [chips[i:i+per] for i in range(0, len(chips), per)]
    rows = per if len(chips) > per else len(chips)
    sheet = Image.new("RGBA", (len(cols)*colw + 40, rows*rowH + 40), CREAM)
    sd = ImageDraw.Draw(sheet)
    for ci, col in enumerate(cols):
        for ri, (lab, im) in enumerate(col):
            im = im.convert("RGBA")
            sc = min(1.0, (colw-120)/im.width, (rowH-16)/im.height)
            if sc < 1.0:
                im = im.resize((max(1, int(im.width*sc)), max(1, int(im.height*sc))))
            y = 20 + ri*rowH + (rowH - im.height)//2
            sd.text((20 + ci*colw + 8, y + im.height//2 - 8), lab, fill=(150, 120, 90, 255))
            sheet.alpha_composite(im, (20 + ci*colw + 70, y))
    sheet.convert("RGB").save(out_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--srt", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--base", help="预览底(_noSub.mp4)，给了才写 burn_preview.sh")
    ap.add_argument("--frames-list", help="透明帧 concat 清单，给了才写 burn_alpha.sh")
    ap.add_argument("--preview-out", default="成片_预览.mp4")
    ap.add_argument("--alpha-out", default="成片_透明层.mov")
    ap.add_argument("--total", type=float, default=0)
    ap.add_argument("--keywords", help="每行一个关键词，命中的字染橙")
    ap.add_argument("--corrections", help="每行 wrong=right，修转写错字")
    ap.add_argument("--fontsize", type=int, default=46)
    ap.add_argument("--minsize", type=int, default=38, help="字号下限；缩到这个还放不下就把这行拆成多幕")
    ap.add_argument("--y", type=int, default=978, help="字幕在画面里的 y（录屏窗洞底之下）")
    ap.add_argument("--maxw", type=int, default=880, help="文字最大宽度，超了先缩字号、到下限再拆幕")
    ap.add_argument("--lsp", type=int, default=6, help="字间距 px，避免拥挤")
    a = ap.parse_args()

    os.makedirs(a.outdir, exist_ok=True)
    keywords = read_lines(a.keywords)
    corrections = read_lines(a.corrections)

    fcache = {}
    def gf(sz):
        if sz not in fcache:
            fcache[sz] = load_font(sz)
        return fcache[sz]

    meas = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    def spaced_width(rr, f):
        w = 0.0; n = 0
        for run, _ in rr:
            for ch in run:
                w += meas.textlength(ch, font=f); n += 1
        return w + a.lsp * max(0, n - 1)

    def fit_size(text):
        rr = runs(text, keywords)
        sz = a.fontsize
        while sz > a.minsize:
            if spaced_width(rr, gf(sz)) <= a.maxw:
                break
            sz -= 2
        return sz, rr

    PUNCT = "，。、；：！？,.!?; "
    GOOD_END = "的了呢吧么啊呀吗嘛"   # 语气助词/软停顿，断在它后面读着自然
    def _alnum(ch):
        return ch.isascii() and ch.isalnum()
    def _find(text, target, L, chars, win):
        for d in range(win + 1):
            for cand in (target + d, target - d):
                if 0 < cand < L and text[cand-1] in chars:
                    return cand
        return None
    def split_text(text, n):
        """把一行按语义/字数切成 n 段：优先标点后 → 助词后 → 字数中点；
        绝不切开英文/数字词，尽量不切开中文词。"""
        if n <= 1:
            return [text]
        L = len(text); cuts = []
        for k in range(1, n):
            target = round(L * k / n)
            best = _find(text, target, L, PUNCT, 4)          # 1 标点后
            if best is None:
                best = _find(text, target, L, GOOD_END, 3)   # 2 助词后
            if best is None:
                best = target                                # 3 字数中点
            # 不在英文/数字词内部断开：断点落在 alnum 连续块中间就挪到块边界
            if 0 < best < L and _alnum(text[best-1]) and _alnum(text[best]):
                lo = best
                while lo > 0 and _alnum(text[lo-1]):
                    lo -= 1
                hi = best
                while hi < L and _alnum(text[hi]):
                    hi += 1
                cand = [x for x in (lo, hi) if 0 < x < L]
                if cand:
                    best = min(cand, key=lambda x: abs(x - best))
            cuts.append(best)
        cuts = sorted(set(c for c in cuts if 0 < c < L))
        pieces = []; prev = 0
        for c in cuts:
            pieces.append(text[prev:c]); prev = c
        pieces.append(text[prev:])
        return [p for p in pieces if p]

    lines = merge(parse_srt(a.srt, corrections))
    # 拆幕判断按「理想字号」算：放不下理想字号就拆，保证每幕都尽量大字，
    # 而不是先缩到下限再硬塞（下限只作单幕安全兜底）。每幕按字数比例分该行时间。
    cards = []
    for (s, e, text) in lines:
        w_ref = spaced_width(runs(text, keywords), gf(a.fontsize))
        n = max(1, math.ceil(w_ref / a.maxw))
        pieces = split_text(text, n)
        tot = sum(len(p) for p in pieces) or 1
        t0 = s
        for p in pieces:
            t1 = t0 + (len(p) / tot) * (e - s)
            cards.append((p, t0, t1))
            t0 = t1

    timing = []
    chips = []
    for i, (text, s, e) in enumerate(cards):
        sz, rr = fit_size(text)
        f = gf(sz)
        w = spaced_width(rr, f)
        asc, desc = f.getmetrics()
        H = asc + desc + PADY*2
        W = int(w) + PADX*2
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, W-1, H-1], radius=18, fill=CHIP)
        x = PADX
        for run, ism in rr:
            col = ORANGE if ism else INK
            for ch in run:
                d.text((x, PADY), ch, font=f, fill=col, stroke_width=1, stroke_fill=col)
                x += meas.textlength(ch, font=f) + a.lsp
        img.save(os.path.join(a.outdir, f"sub_{i:03d}.png"))
        chips.append((f"{i:03d}", img))
        timing.append((i, s, e))

    # 出片必做：全幕字幕自检图（逐幕核验字号/断词/关键词/错字）。壳帧在门 2 已审，不在此。
    sheet_path = os.path.join(os.path.dirname(a.outdir) or ".", "字幕自检.png")
    build_contact_sheet(chips, sheet_path)
    print(f"★ 字幕自检图（出片前逐幕核验）: {sheet_path}")

    inputs = " ".join(f'-i "{a.outdir}/sub_{i:03d}.png"' for i, _, _ in timing)

    def overlays(base_label):
        fc = []
        prev = base_label
        for k, (i, s, e) in enumerate(timing):
            out = f"[v{k}]" if k < len(timing)-1 else "[vout]"
            fc.append(f"{prev}[{k+1}:v]overlay=x=(W-w)/2:y={a.y}:enable='between(t,{s:.3f},{e:.3f})'{out}")
            prev = f"[v{k}]"
        return ";".join(fc)

    if a.base:
        open(os.path.join(a.outdir, "fc_preview.txt"), "w").write(overlays("[0:v]"))
        open(os.path.join(a.outdir, "burn_preview.sh"), "w").write(
            f'ffmpeg -y -i "{a.base}" {inputs} -filter_complex_script "{a.outdir}/fc_preview.txt" '
            f'-map "[vout]" -map 0:a -c:v libx264 -preset veryfast -crf 20 -c:a aac -b:a 160k '
            f'-movflags +faststart "{a.preview_out}"\n')

    if a.frames_list:
        open(os.path.join(a.outdir, "fc_alpha.txt"), "w").write("[0:v]fps=30,format=rgba[b];" + overlays("[b]"))
        tflag = f"-t {a.total} " if a.total else ""
        open(os.path.join(a.outdir, "burn_alpha.sh"), "w").write(
            f'ffmpeg -y -f concat -safe 0 -i "{a.frames_list}" {inputs} '
            f'-filter_complex_script "{a.outdir}/fc_alpha.txt" -map "[vout]" '
            f'-c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le -an {tflag}"{a.alpha_out}"\n')

    print(f"字幕 {len(lines)} 行 → {len(cards)} 幕（下限 {a.minsize}px）→ {a.outdir}")

if __name__ == "__main__":
    main()
