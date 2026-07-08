#!/usr/bin/env bash
# slidecast —— 口播录音 → 3:4 case-step 字幕片
# 产出：成片_预览.mp4（米底填洞+音轨，直接看）+ 成片_透明层.mov（录屏洞透明 ProRes4444，剪映叠录屏/脸）
#
# 用法：  bash build.sh <project_dir>
# project_dir 里需要（门 1/门 2 由 LLM 先准备好）：
#   voiceover.mov        —— 纯口播（任意画幅，只取音轨）
#   manifest.yaml        —— doc-to-slides case-step 帧清单（每段口播一帧：title/sub/透明录屏窗）
#   timeline.tsv         —— 每行「帧文件名<TAB>秒数」，秒数=该段口播时长（从 transcript 对齐）
#   keywords.txt（可选）  —— 每行一个关键词，字幕里命中的字染安全橙
#   corrections.txt（可选）—— 每行 wrong=right，修 whisper 转写错字
set -euo pipefail
DIR="${1:?用法: bash build.sh <project_dir>}"
DIR="$(cd "$DIR" && pwd)"
HERE="$(cd "$(dirname "$0")" && pwd)"
DTS="$HOME/.claude/skills/doc-to-slides"
WMODEL="${WHISPER_MODEL:-$HOME/.whisper-models/ggml-large-v3-turbo.bin}"
VO="$DIR/voiceover.mov"

echo "== [1/5] 转写（whisper-cli）=="
if [ ! -f "$DIR/transcript.srt" ]; then
  ffmpeg -y -i "$VO" -ar 16000 -ac 1 -c:a pcm_s16le "$DIR/audio.wav" -v error
  whisper-cli -m "$WMODEL" -f "$DIR/audio.wav" -l zh -osrt -of "$DIR/transcript" >/dev/null 2>&1
  echo "  → transcript.srt（LLM 据此写 timeline.tsv / 门 1）"
else
  echo "  transcript.srt 已存在，跳过"
fi

echo "== [2/5] 渲 case-step 帧（doc-to-slides）=="
_missing() { python3 - "$DIR" <<'PY'
import sys, os
d = sys.argv[1]
miss = [l.split("\t")[0].strip() for l in open(os.path.join(d, "timeline.tsv"), encoding="utf-8")
        if l.strip() and not l.startswith("#")
        and not os.path.exists(os.path.join(d, "frames", l.split("\t")[0].strip()))]
print(" ".join(miss))
PY
}
python3 "$DTS/render.py" "$DIR/manifest.yaml" >/dev/null
M="$(_missing)"
if [ -n "$M" ]; then echo "  ⚠ 缺帧【$M】—— Chrome headless 偶发失败，重渲一次…"; python3 "$DTS/render.py" "$DIR/manifest.yaml" >/dev/null; M="$(_missing)"; fi
if [ -n "$M" ]; then echo "  ✗ 重渲后仍缺帧【$M】，停。"; exit 1; fi
echo "  → frames/（门 2 review 页可看，17/17 齐）"

echo "== [3/5] 时间线 concat（硬切）=="
TOTAL="$(python3 - "$DIR" <<'PY'
import sys, os
d = sys.argv[1]; fr = os.path.join(d, "frames")
rows = [l.rstrip("\n").split("\t") for l in open(os.path.join(d, "timeline.tsv"), encoding="utf-8")
        if l.strip() and not l.startswith("#")]
out = ["ffconcat version 1.0"]
for fn, dur in rows:
    out += [f"file '{fr}/{fn.strip()}'", f"duration {float(dur):.3f}"]
out.append(f"file '{fr}/{rows[-1][0].strip()}'")   # concat 末帧要重复一次
open(os.path.join(d, "frames_list.txt"), "w").write("\n".join(out) + "\n")
print(f"{sum(float(r[1]) for r in rows):.3f}")
PY
)"
echo "  总时长 ${TOTAL}s"

echo "== [4/5] 合无字幕预览（米底填洞 + 音轨）=="
ffmpeg -y -f concat -safe 0 -i "$DIR/frames_list.txt" -i "$VO" \
  -filter_complex "[0:v]fps=30,scale=1080:1440,format=rgba[fr];color=c=0xf5efe1:s=1080x1440:r=30[bg];[bg][fr]overlay=format=auto:shortest=1,format=yuv420p[v]" \
  -map "[v]" -map 1:a -c:v libx264 -preset veryfast -crf 20 -c:a aac -b:a 160k \
  -movflags +faststart -t "$TOTAL" "$DIR/_noSub.mp4" -v error

echo "== [5/5] 字幕（PNG overlay）→ 烧预览 + 透明层 =="
KW=(); [ -f "$DIR/keywords.txt" ] && KW=(--keywords "$DIR/keywords.txt")
CR=(); [ -f "$DIR/corrections.txt" ] && CR=(--corrections "$DIR/corrections.txt")
python3 "$HERE/subs.py" --srt "$DIR/transcript.srt" --outdir "$DIR/subs" \
  --base "$DIR/_noSub.mp4" --frames-list "$DIR/frames_list.txt" \
  --preview-out "$DIR/成片_预览.mp4" --alpha-out "$DIR/成片_透明层.mov" \
  --total "$TOTAL" "${KW[@]}" "${CR[@]}"
bash "$DIR/subs/burn_preview.sh" 2>&1 | tail -1
bash "$DIR/subs/burn_alpha.sh" 2>&1 | tail -1

echo ""
echo "完成："
echo "  预览（米底填洞+音轨）: $DIR/成片_预览.mp4"
echo "  透明层（录屏洞透明）  : $DIR/成片_透明层.mov"
