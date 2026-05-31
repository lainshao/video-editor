#!/usr/bin/env bash
# lint_template.sh — 静态检查动画模板是否符合 CONVENTIONS.md § 10 "模板契约"
#
# 用法：
#   bash recipes/lint_template.sh path/to/template.html
#   bash recipes/lint_template.sh animator/chyron/chyron.html
#   bash recipes/lint_template.sh --all          # 检查 skill 自带全部模板
#
# 返回码：
#   0 = 全部通过
#   1 = 有 FAIL
#   2 = 有 WARN 但无 FAIL

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"

# 颜色（终端支持时启用）
if [[ -t 1 ]]; then
  C_OK=$'\033[32m'; C_WARN=$'\033[33m'; C_FAIL=$'\033[31m'; C_DIM=$'\033[2m'; C_RST=$'\033[0m'
else
  C_OK=''; C_WARN=''; C_FAIL=''; C_DIM=''; C_RST=''
fi

# ──────────────────────────────────────────────────────────────
# 检查函数：每个返回 0=ok / 1=fail / 2=warn
# ──────────────────────────────────────────────────────────────

check_viewport() {
  grep -qE '<meta[^>]+viewport[^>]+width=1080[^>]+height=1920' "$1"
}

check_root_container() {
  grep -qE 'data-composition-id="main"' "$1" && \
  grep -qE 'data-(start|duration|width|height)=' "$1"
}

check_body_dimensions() {
  grep -qE 'width:\s*1080px' "$1" && \
  grep -qE 'height:\s*1920px' "$1"
}

check_transparent_bg() {
  # body / html 必须 transparent（让 ProRes 有 alpha）。允许 .scene 等单独不透明。
  grep -qE 'background:\s*transparent' "$1"
}

check_font_stack() {
  # 至少有一个中文字体在栈里
  grep -qE 'font-family:[^;]*("PingFang SC"|"Noto Sans SC"|"Hiragino|"STHeiti)' "$1"
}

check_gsap_cdn() {
  grep -qE 'gsap@[0-9]+\.[0-9]+' "$1"
}

check_timeline_register() {
  grep -qE 'window\.__timelines\["main"\]\s*=\s*tl' "$1"
}

check_autoplay() {
  # 任一形式都行：if (!__hyperframes_runtime) tl.play()  OR  if (__hyperframes_runtime) return
  grep -qE 'tl\.play\(\)' "$1" && \
  grep -qE 'window\.__hyperframes_runtime' "$1"
}

check_no_brown_shadow() {
  ! grep -qE 'rgba\(60,\s*40,\s*0,' "$1"
}

check_no_debug_label() {
  # 模板可以定义 .scene-label class，但不能在 body 实际渲染（成片 cp 后用户应删）
  # 此检查只在源模板里找 <div class="scene-label">，如果只在 CSS 里出现是 OK 的
  ! grep -qE '<[a-z]+[^>]*class="[^"]*scene-label' "$1"
}

check_placeholder_syntax() {
  # 警告：有占位符则必须用 {{UPPER_SNAKE}} 形式
  # 如果有 {{...}} 但格式不对（小写 / 含空格）则 warn
  if grep -qE '\{\{' "$1"; then
    # 找所有 {{...}}
    bad=$(grep -oE '\{\{[^}]+\}\}' "$1" | grep -vE '\{\{[A-Z_][A-Z0-9_]*\}\}' || true)
    if [[ -n "$bad" ]]; then
      return 2  # warn
    fi
  fi
  return 0
}

check_fontsize_ladder() {
  # CONVENTIONS.md §五 字号阶梯：font-size 必须命中固定 token，不许出现区间内任意值
  # token = 文字阶梯 {24 32 44 56 72 96 138} ∪ icon 轨 {64 96 140} ∪ chyron 例外 {130}
  # ⚠ 改这里前先改 CONVENTIONS §五 的表，保持单一事实源
  local allowed=" 24 32 44 56 64 72 96 130 138 140 "
  local bad="" s
  for s in $(grep -oE 'font-size:\s*[0-9]+px' "$1" | grep -oE '[0-9]+' | sort -n | uniq); do
    case "$allowed" in
      *" $s "*) ;;
      *) bad="$bad ${s}px" ;;
    esac
  done
  if [[ -n "$bad" ]]; then
    RUN_DETAIL="越界字号:${bad} → 收到最近 token (24/32/44/56/64/72/96/130/138/140)"
    return 1
  fi
  return 0
}

check_text_overflow_risk() {
  # 启发式：找 white-space: nowrap + font-size > 100px 的 .text/.chyron-text/.line
  # 如果有就 warn（可能溢出）
  if grep -qE 'font-size:\s*(1[3-9][0-9]|[2-9][0-9]{2})px' "$1" && \
     grep -qE 'white-space:\s*nowrap' "$1"; then
    return 2
  fi
  return 0
}

# ──────────────────────────────────────────────────────────────
# 主检查流程
# ──────────────────────────────────────────────────────────────

lint_one() {
  local f="$1"
  local rel="${f#$SKILL_ROOT/}"

  if [[ ! -f "$f" ]]; then
    echo "${C_FAIL}✗${C_RST} 文件不存在: $f"
    return 1
  fi

  echo ""
  echo "${C_DIM}─────────────────────────────────────────${C_RST}"
  echo "  ${rel}"
  echo "${C_DIM}─────────────────────────────────────────${C_RST}"

  local fails=0
  local warns=0

  run() {
    local label="$1"; shift
    local fn="$1"; shift
    RUN_DETAIL=""   # 检查函数可往这里写一行明细，失败/警告时打印
    if $fn "$f"; then
      echo "  ${C_OK}✓${C_RST} ${label}"
    else
      local rc=$?
      if [[ $rc == 2 ]]; then
        echo "  ${C_WARN}⚠${C_RST} ${label}"
        warns=$((warns+1))
      else
        echo "  ${C_FAIL}✗${C_RST} ${label}"
        fails=$((fails+1))
      fi
      [[ -n "$RUN_DETAIL" ]] && echo "      ${C_DIM}${RUN_DETAIL}${C_RST}"
    fi
  }

  echo "${C_DIM}— 结构层 —${C_RST}"
  run "viewport meta = 1080×1920"           check_viewport
  run "根容器 data-composition-id + 属性"   check_root_container
  run "body 尺寸 1080×1920"                 check_body_dimensions
  run "body 背景 transparent（保 alpha）"   check_transparent_bg
  run "CJK 字体栈存在"                       check_font_stack

  echo "${C_DIM}— 动画层 —${C_RST}"
  run "GSAP CDN 引入"                       check_gsap_cdn
  run "window.__timelines[\"main\"] 注册"   check_timeline_register
  run "autoplay 钩子（! __hyperframes_runtime → tl.play）" check_autoplay

  echo "${C_DIM}— 视觉规范 —${C_RST}"
  run "无 brown shadow rgba(60,40,0,…)"     check_no_brown_shadow
  run "无 <div class=\"scene-label\"> 残留" check_no_debug_label
  run "字号命中 token 阶梯（§五）"          check_fontsize_ladder

  echo "${C_DIM}— 软规则（warn）—${C_RST}"
  run "占位符语法 {{UPPER_SNAKE}}"          check_placeholder_syntax
  run "无文字溢出风险（>120px nowrap）"     check_text_overflow_risk

  if [[ $fails -gt 0 ]]; then
    echo ""
    echo "  ${C_FAIL}❌ FAIL ${fails} 项${C_RST}（必修才能 cp 给用户用）"
    return 1
  elif [[ $warns -gt 0 ]]; then
    echo ""
    echo "  ${C_WARN}⚠ WARN ${warns} 项${C_RST}（建议修，不阻塞）"
    return 2
  else
    echo ""
    echo "  ${C_OK}✅ ALL PASS${C_RST}"
    return 0
  fi
}

# ──────────────────────────────────────────────────────────────
# 入口
# ──────────────────────────────────────────────────────────────

if [[ $# -eq 0 ]]; then
  echo "用法: bash $0 <template.html> | --all"
  exit 2
fi

if [[ "$1" == "--all" ]]; then
  any_fail=0
  any_warn=0
  while IFS= read -r f; do
    lint_one "$f"
    rc=$?
    [[ $rc == 1 ]] && any_fail=1
    [[ $rc == 2 ]] && any_warn=1
  done < <(find "$SKILL_ROOT/animator" "$SKILL_ROOT/opener" -type f -name "*.html" ! -path "*_hyperframes_meta*" ! -name "spec_review_template.html" | sort)
  echo ""
  echo "${C_DIM}═════════════════════════════════════════${C_RST}"
  if [[ $any_fail == 1 ]]; then
    echo "${C_FAIL}❌ 至少有一个模板 FAIL${C_RST}"
    exit 1
  elif [[ $any_warn == 1 ]]; then
    echo "${C_WARN}⚠ 全 PASS 但有 WARN${C_RST}"
    exit 2
  else
    echo "${C_OK}✅ 全部模板通过${C_RST}"
    exit 0
  fi
else
  # 单文件模式：支持相对 skill 根的路径
  target="$1"
  [[ ! -f "$target" ]] && target="$SKILL_ROOT/$1"
  lint_one "$target"
  exit $?
fi
