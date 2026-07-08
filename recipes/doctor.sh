#!/bin/bash
# doctor.sh — video-editor 环境自检
# 跑一遍就知道缺啥。装新机器 / 删过 venv / 跨平台时先跑这个。
#
# 用法：
#   bash recipes/doctor.sh
#
# 退出码：
#   0 = 全 OK
#   1 = 有至少 1 个必需依赖缺失

set -u
PASS=0
FAIL=0

color() { printf "\033[%sm%s\033[0m" "$1" "$2"; }
ok()    { echo "$(color 32 "✓") $1"; PASS=$((PASS+1)); }
fail()  { echo "$(color 31 "✗") $1 — $2"; FAIL=$((FAIL+1)); }
warn()  { echo "$(color 33 "⚠") $1 — $2"; }

echo ""
echo "════════════════════════════════════════════"
echo "  video-editor · 环境自检"
echo "════════════════════════════════════════════"

# ───────────────────────────────────────────────
# 系统二进制（必须）
# ───────────────────────────────────────────────
echo ""
echo "[系统 binaries]"

if command -v ffmpeg >/dev/null 2>&1; then
  ok "ffmpeg ($(ffmpeg -version 2>&1 | head -1 | awk '{print $3}'))"
else
  fail "ffmpeg" "缺失。装：brew install ffmpeg"
fi

if command -v whisper-cli >/dev/null 2>&1; then
  ok "whisper-cli"
else
  fail "whisper-cli" "缺失。装：brew install whisper-cpp（注意命令名是 whisper-cli，不是 whisper）"
fi

if command -v node >/dev/null 2>&1; then
  NODE_VER=$(node --version)
  NODE_MAJOR=$(echo "$NODE_VER" | sed 's/v\([0-9]*\).*/\1/')
  if [ "$NODE_MAJOR" -ge 22 ]; then
    ok "node $NODE_VER"
  else
    fail "node $NODE_VER" "需要 Node ≥ 22（当前太低）"
  fi
else
  fail "node" "缺失。装：brew install node"
fi

if command -v npx >/dev/null 2>&1; then
  ok "npx"
else
  fail "npx" "缺失（应该跟 node 一起来的，检查 PATH）"
fi

# ───────────────────────────────────────────────
# Python 依赖（subtitle 子模块）
# ───────────────────────────────────────────────
echo ""
echo "[Python · subtitle 子模块]"

if command -v python3 >/dev/null 2>&1; then
  ok "python3 ($(python3 --version 2>&1 | awk '{print $2}'))"
else
  fail "python3" "缺失"
fi

if python3 -c "from PIL import Image" 2>/dev/null; then
  ok "Pillow (PIL)"
else
  fail "Pillow" "缺失。装：pip install -r subtitle/requirements.txt（或单装 pip install Pillow）"
fi

# ───────────────────────────────────────────────
# whisper 模型（subtitle 子模块）
# ───────────────────────────────────────────────
echo ""
echo "[whisper 模型]"

WHISPER_DIR="${WHISPER_MODEL_PATH:-$HOME/.whisper-models}"
WHISPER_DIR=$(dirname "$WHISPER_DIR" 2>/dev/null || echo "$HOME/.whisper-models")

if [ -f "$HOME/.whisper-models/ggml-large-v3-turbo.bin" ]; then
  ok "ggml-large-v3-turbo.bin (1.6GB · 字幕推荐)"
elif [ -f "$HOME/.whisper-models/ggml-base.bin" ]; then
  warn "ggml-base.bin (150MB · 快但中文不准)" "建议下载 large-v3-turbo 烧字幕用，base 仅 cue plan 转录够用"
elif [ -n "${WHISPER_MODEL_PATH:-}" ] && [ -f "$WHISPER_MODEL_PATH" ]; then
  ok "WHISPER_MODEL_PATH=$WHISPER_MODEL_PATH"
else
  fail "whisper 模型" "缺失。下载：
       mkdir -p ~/.whisper-models
       curl -L -o ~/.whisper-models/ggml-large-v3-turbo.bin \\
         https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin"
fi

# ───────────────────────────────────────────────
# 字体（中文渲染 + 字幕 PNG）
# 用 PIL 实测能不能渲一个中文字符——subtitle 子模块就是这么用的
# ───────────────────────────────────────────────
echo ""
echo "[字体 · CJK]"

CJK_FONT=$(python3 -c "
import sys
try:
    from PIL import ImageFont
except ImportError:
    sys.exit(1)
# subtitle/subtitles.py find_cjk_font() 同一套 fallback chain
candidates = [
    ('/System/Library/Fonts/PingFang.ttc', 4),
    ('/System/Library/Fonts/Supplemental/PingFang.ttc', 4),
    ('/System/Library/Fonts/Hiragino Sans GB.ttc', 1),
    ('/System/Library/Fonts/STHeiti Medium.ttc', 0),
    ('/Library/Fonts/Arial Unicode.ttf', 0),
]
from pathlib import Path
for path, idx in candidates:
    if Path(path).exists():
        try:
            ImageFont.truetype(path, 24, index=idx)
            print(path)
            sys.exit(0)
        except Exception:
            continue
sys.exit(1)
" 2>/dev/null)

if [ -n "$CJK_FONT" ]; then
  ok "CJK 字体可用 ($(basename "$CJK_FONT"))"
else
  fail "CJK 字体" "subtitle 子模块的 fallback chain 都没找到。macOS 一般自带 PingFang，没的话装：brew install --cask font-noto-sans-cjk"
fi

# ───────────────────────────────────────────────
# 渲染链（animator/opener 渲 cue + lint_layout 都靠这三样）
# ───────────────────────────────────────────────
echo ""
echo "[渲染链 · Chrome + puppeteer]"

CHROME_BIN="${CHROME_BIN:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
if [ -x "$CHROME_BIN" ]; then
  ok "Chrome ($CHROME_BIN)"
else
  fail "Chrome" "缺失。render_cue_puppeteer.js / lint_layout.js 直驱系统 Chrome。装 Chrome 或 export CHROME_BIN=<路径>"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if (cd "$SCRIPT_DIR" && node -e "require('puppeteer-core')" 2>/dev/null); then
  ok "puppeteer-core (recipes/node_modules)"
else
  fail "puppeteer-core" "缺失。装：cd $SCRIPT_DIR && npm i puppeteer-core"
fi

if command -v avconvert >/dev/null 2>&1; then
  ok "avconvert (剪映 HEVC-alpha → ProRes4444 转码)"
else
  warn "avconvert" "缺失（macOS 自带，非 mac 平台跳过）。剪映/CapCut 导出的 HEVC-alpha 透明视频 ffmpeg 解不出 alpha，需要它转 ProRes4444"
fi

# ───────────────────────────────────────────────
# 总结
# ───────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════"
echo "  结果：通过 $PASS · 失败 $FAIL"
echo "════════════════════════════════════════════"

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "$(color 31 "✗") 有 $FAIL 项依赖缺失，video-editor 不能完整跑。按上面提示装齐再试。"
  exit 1
else
  echo ""
  echo "$(color 32 "✓") 全部通过，video-editor 可以跑。"
  exit 0
fi
