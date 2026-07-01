#!/usr/bin/env python3
"""add_subtitles.py — burn keyword-highlighted captions onto ANY finished video.

Standalone post-edit subtitle tool (the most common task): transcribe the
video with whisper, apply spelling/term corrections, render PNG captions
(white text + yellow keywords + semi-transparent black box), and overlay them
onto the video keeping the original audio. No script.md needed.

Usage:
  add_subtitles.py <video> [options]

Options:
  --out PATH            output path (default: <video_dir>/<stem>_subtitled.mp4)
  --srt PATH            use an existing (hand-corrected) SRT, skip whisper
  --lang LANG           whisper language (default: zh)
  --keywords "a,b,c"    extra yellow keywords (added to defaults)
  --corrections FILE    extra corrections file (added to the default one)
  --no-default-kw       don't use the built-in keyword list
  --margin PX           subtitle distance from bottom (default: subtitles.SUB_MARGIN_V)
  --fast                videotoolbox encode (default; pass --quality for libx264)
  --quality             libx264 high-quality encode (slower)

Captions support **bold** markers (force a word yellow) in addition to the
keyword list.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import subtitles

# Whisper 模型路径：环境变量优先，默认 ~/.whisper-models/ggml-large-v3-turbo.bin
WHISPER_MODEL = Path(os.environ.get(
    'WHISPER_MODEL_PATH',
    str(Path.home() / '.whisper-models' / 'ggml-large-v3-turbo.bin')
))

# 默认修正词典 —— 公共示例（Claude Code 系列语料，可用作参考）
DEFAULT_CORRECTIONS_FILE = HERE / 'corrections_example.txt'

# 默认关键词高亮列表 —— 公共版默认空
# 你可以通过以下任一方式提供关键词：
#   1. CLI 参数：--keywords "word1,word2,word3"
#   2. 私人 overlay 文件：在 subtitle/ 下建 _private_defaults.py（已加入 .gitignore），
#      里面定义 `DEFAULT_KEYWORDS = ['Claude Code', ...]`，会自动覆盖此处的空列表
DEFAULT_KEYWORDS = []

# ── 私人 overlay 加载（gitignored 不开源）─────────────────────────
# 如果存在 _private_defaults.py，加载它的 DEFAULT_KEYWORDS / DEFAULT_CORRECTIONS_FILE 覆盖默认
_private_overlay = HERE / '_private_defaults.py'
if _private_overlay.exists():
    import importlib.util
    _spec = importlib.util.spec_from_file_location('_private_overlay', _private_overlay)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    DEFAULT_KEYWORDS = getattr(_mod, 'DEFAULT_KEYWORDS', DEFAULT_KEYWORDS)
    if hasattr(_mod, 'DEFAULT_CORRECTIONS_FILE'):
        DEFAULT_CORRECTIONS_FILE = Path(_mod.DEFAULT_CORRECTIONS_FILE)


def load_corrections(*files):
    """Parse '<from> => <to>' lines from one or more files. Returns ordered list."""
    rules = []
    for f in files:
        if not f:
            continue
        p = Path(f)
        if not p.exists():
            print(f"  ⚠ corrections file not found: {p}")
            continue
        for line in p.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=>' not in line:
                continue
            a, b = line.split('=>', 1)
            rules.append((a.strip(), b.strip()))
    return rules


def apply_corrections(text, rules):
    for a, b in rules:
        text = text.replace(a, b)
    return text


def parse_srt(path: Path):
    """Parse an SRT into [(text, start_s, end_s), ...]. Tolerates ',' or '.' ms sep."""
    blocks = re.split(r'\n\s*\n', path.read_text(encoding='utf-8', errors='replace').strip())
    ts = re.compile(r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)')
    out = []
    for b in blocks:
        lines = [l for l in b.splitlines() if l.strip()]
        if len(lines) < 2:
            continue
        m = ts.search(b)   # 时间行通常带序号在第 2 行，少数无序号；整块搜更稳
        if not m:
            continue
        g = list(map(int, m.groups()))
        st = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000.0
        en = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000.0
        body = [l for l in lines if not ts.search(l) and not l.strip().isdigit()]
        text = ' '.join(body).strip()
        if text:
            out.append((text, st, en))
    return out


def transcribe(video: Path, work: Path, lang: str):
    work.mkdir(parents=True, exist_ok=True)
    wav = work / 'audio.wav'
    subprocess.run(['ffmpeg', '-y', '-i', str(video), '-ar', '16000', '-ac', '1',
                    '-c:a', 'pcm_s16le', str(wav)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    prefix = work / 'transcript'
    if not WHISPER_MODEL.exists():
        sys.exit(f"Error: whisper model not found at {WHISPER_MODEL}")
    subprocess.run(['whisper-cli', '-m', str(WHISPER_MODEL), '-l', lang,
                    '-ojf', '-of', str(prefix), str(wav)], check=True)
    return Path(str(prefix) + '.json')


def video_duration(video: Path) -> float:
    return float(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(video)]).strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video', type=Path)
    ap.add_argument('--out', type=Path, default=None)
    ap.add_argument('--lang', default='zh')
    ap.add_argument('--srt', type=Path, default=None,
                    help='use an existing (e.g. hand-corrected) SRT instead of running whisper')
    ap.add_argument('--keywords', default='')
    ap.add_argument('--corrections', default=None)
    ap.add_argument('--no-default-kw', action='store_true')
    ap.add_argument('--margin', type=int, default=subtitles.SUB_MARGIN_V)
    ap.add_argument('--fast', action='store_true', default=True)
    ap.add_argument('--quality', action='store_true')
    args = ap.parse_args()

    video = args.video.expanduser().resolve()
    if not video.exists():
        sys.exit(f"Error: video not found: {video}")
    out = (args.out.expanduser().resolve() if args.out
           else video.with_name(video.stem + '_subtitled.mp4'))
    work = video.parent / f'.{video.stem}.subswork'

    # keywords
    keywords = [] if args.no_default_kw else list(DEFAULT_KEYWORDS)
    keywords += [k.strip() for k in args.keywords.split(',') if k.strip()]

    # corrections
    rules = load_corrections(DEFAULT_CORRECTIONS_FILE, args.corrections)

    print(f"Video: {video.name} | out: {out.name}")
    dur = video_duration(video)

    timed = []
    if args.srt:
        srt = args.srt.expanduser().resolve()
        if not srt.exists():
            sys.exit(f"Error: --srt file not found: {srt}")
        print(f"Using existing SRT: {srt.name} (skipping whisper)")
        for text, st, en in parse_srt(srt):
            text = apply_corrections(text, rules)
            if text:
                timed.append((text, st, en))
    else:
        print(f"Transcribing (whisper, lang={args.lang}) ...")
        tj = transcribe(video, work, args.lang)
        trans = json.loads(tj.read_text(encoding='utf-8', errors='replace'))
        for c in trans['transcription']:
            text = apply_corrections(c['text'].strip(), rules)
            if text:
                timed.append((text, c['offsets']['from'] / 1000.0, c['offsets']['to'] / 1000.0))

    print("\n=== captions (corrected) ===")
    for t, s, e in timed:
        print(f"  {s:6.2f}-{e:6.2f}  {t}")

    events = subtitles.render_subtitle_pngs(timed, keywords, work / 'subs_png', dur)
    print(f"\nRendered {len(events)} caption PNGs (margin={args.margin}, {len(keywords)} keywords)")

    # ffmpeg overlay (keep original audio)
    inputs = ['-i', str(video)]
    for ev in events:
        inputs += ['-loop', '1', '-t', f'{dur:.3f}', '-i', str(Path(ev['png']).resolve())]
    parts, _ = subtitles.overlay_filtergraph(events, base_label='0:v',
                                             first_img_idx=1, out_label='vout',
                                             margin_v=args.margin)
    if args.quality:
        enc = ['-c:v', 'libx264', '-profile:v', 'high', '-preset', 'medium', '-crf', '19']
    else:
        enc = ['-c:v', 'h264_videotoolbox', '-b:v', '8M', '-maxrate', '10M',
               '-bufsize', '16M', '-profile:v', 'high']
    cmd = ['ffmpeg', '-y'] + inputs + [
        '-filter_complex', ';'.join(parts),
        '-map', '[vout]', '-map', '0:a?',
    ] + enc + [
        '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
        '-movflags', '+faststart', str(out),
    ]
    print(f"Burning → {out}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print('\n'.join(proc.stderr.splitlines()[-30:]))
        sys.exit(f"ffmpeg failed ({proc.returncode})")
    print(f"\n✓ Done: {out}")


if __name__ == '__main__':
    main()
