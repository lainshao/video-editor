# video-editor

> 🌏 **中文版: [README.md](./README.md)**

> An Agent Skill (Claude Code / OpenAI Codex) for composing 9:16 short-form videos from a talking-head recording
> plus animated overlays — title cards, kinetic typography, full-screen data cards,
> burned-in subtitles. Outputs an integrated MP4 preview and an optional ProRes 4444
> alpha overlay layer for editing-software workflows.

**Status**: pre-1.0, optimized for Chinese-language short-form on 抖音 / 小红书 / 视频号 / Reels / Shorts. The default visual identity ("Hana theme") ships with the templates — see [Theming](#theming) for rebranding notes.

---

## What it does

You give the skill a finished talking-head recording (`speech.mov`, 9:16 portrait). It helps you:

| Task | Submodule | How |
|---|---|---|
| Burn a 4.5s kinetic **title card** at 0s | `opener/` | Transparent overlay: bold yellow serif headline + white italic subtitle (`yellow.html`) |
| Add **animated overlays** during talking head — pop-up keywords, full-screen data cards, numbered lists, multi-phase carousels | `animator/` | 7 HTML templates, GSAP-driven, rendered by HyperFrames CLI or timecut |
| Burn **keyword-highlighted captions** onto the finished video | `subtitle/` | Auto-transcribe with whisper, apply spelling corrections, overlay PNG captions with yellow keyword highlighting |
| Compose **dual outputs** — integrated MP4 + alpha-channel ProRes overlay layer | `recipes/compose_dual.sh.template` | ffmpeg recipe; both share the same overlay chain |

The skill is **routing-first**: when invoked it asks what you want to do (subtitles only? title card only? new cue / full compose? entire pipeline?), then dispatches to the right submodule. It does not force a full pipeline.

---

## Quick start

### Install

This is an **Agent Skill** — the open `SKILL.md` format supported by both [Claude Code](https://docs.claude.com/en/docs/claude-code) and [OpenAI Codex](https://developers.openai.com/codex/skills). Clone it into your agent's skills directory:

```bash
# Claude Code
git clone https://github.com/lainshao/video-editor.git ~/.claude/skills/video-editor

# OpenAI Codex
git clone https://github.com/lainshao/video-editor.git ~/.agents/skills/video-editor
```

Restart your agent (or start a new session) so it picks up the skill. Then just say
"剪一下这个视频" / "帮我加字幕" / "做个片头" and it routes you to the right submodule.

> **Cross-agent note**: The HTML templates, ffmpeg recipes, and Python/whisper scripts are
> agent-agnostic. The only Claude-specific touch is the routing step, which uses Claude Code's
> `AskUserQuestion` for a clickable menu; under Codex it degrades gracefully to a plain-text
> question. Both engines auto-trigger the skill from the `description` keywords in `SKILL.md`.

### Dependencies

```bash
# Required system binaries
brew install ffmpeg                    # video compose + caption burn
brew install whisper-cpp               # transcription (cli is `whisper-cli`)
brew install node                      # for HyperFrames / timecut

# HyperFrames CLI (HTML → video renderer)
npm install -g hyperframes             # or use `npx --yes hyperframes` ad-hoc

# Whisper model (~1.6GB)
mkdir -p ~/.whisper-models
curl -L -o ~/.whisper-models/ggml-large-v3-turbo.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin

# Python deps for subtitle module (Pillow only)
pip install -r subtitle/requirements.txt
```

**Node version**: 22 ≤ Node < 25. Node 25 has known silent init failures in `timecut` / `hyperframes`.

**Optional env var**:
```bash
export WHISPER_MODEL_PATH=/path/to/ggml-base.bin   # if you don't use the default
```

### Invoking from Claude Code

Once installed under `~/.claude/skills/video-editor/`, the skill auto-triggers when you say:

| You say | Goes to |
|---|---|
| "Add subtitles to this video" | `subtitle/` (no routing prompt) |
| "Make me a title card" | `opener/` (`yellow.html`) |
| "New episode" / "do a full video" | Full pipeline through the Three Gates workflow |
| "Add a chyron at X seconds" | `animator/` |

Or invoke explicitly: ask Claude to "use the video-editor skill".

---

## The Three Gates workflow

The `animator/` submodule (and by extension full-pipeline mode) runs every new video through a **three-gate review pipeline** before any rendering. This is the skill's main opinion — review structural decisions while changes are still cheap (markdown edits), not after 30 seconds of rendering + 500MB of disk write.

| Gate | When | Output | Cost of failure |
|---|---|---|---|
| **Gate 1 · Cue plan (text)** | Before writing any HTML | Markdown table in chat | Edit 1-2 words |
| **Gate 2 · Spec Review (HTML)** | After writing HTML, before rendering | Interactive `_review/spec_review.html` with iframe previews + decision chips + comment box | Edit HTML, ~10s reload |
| **Gate 3 · Pre-render last call** | Spec locked, about to render | Three-part check in chat: recap + judgment calls + output format choice | Zero (nothing rendered yet) |

See [`animator/README.md`](animator/README.md) for the full workflow including cue-density baselines and add/remove feedback scripts.

---

## File structure

```
video-editor/
├── SKILL.md                Routing entry (Claude reads this first)
├── CONVENTIONS.md          Visual rules: safe zones, palette, type scale, etc.
├── README.md               You are here
├── LICENSE                 MIT
├── gallery.html            Open in browser for visual inventory of all templates
│
├── opener/                 Title card submodule
│   ├── README.md
│   ├── yellow.html         Transparent overlay: yellow serif headline + white italic subtitle
│   └── render_opener.py    Optional frame-by-frame Python renderer
│
├── animator/               HTML overlay templates
│   ├── README.md           Three Gates workflow + cue baselines
│   ├── chyron/             Keyword pop-ups (pill or underlined card)
│   ├── cutaway/            Full-screen scenes (blank, listicle, progressive, burst)
│   ├── review/             Spec Review template
│   └── _hyperframes_meta/  hyperframes.json + meta.json for cue projects
│
├── subtitle/               Caption burning submodule
│   ├── README.md
│   ├── subtitles.py        PNG-overlay caption renderer (libass-free)
│   ├── add_subtitles.py    CLI entry: video → transcribed & captioned video
│   ├── corrections_example.txt
│   └── requirements.txt    Just Pillow
│
├── themes/                 Reference docs for the visual identity
│   ├── _base.css           Canonical structural CSS (templates inline equivalents)
│   └── hana.css            Canonical Hana palette
│
└── recipes/
    ├── compose_dual.sh.template   ffmpeg dual-output (mp4 + alpha mov)
    ├── PITFALLS.md                 22 known pitfalls
    └── examples.md                 Original author's worked examples (reference only)
```

---

## Theming

The skill ships with a single baked-in visual identity called **Hana** — cream background (`#FAF6EF`), yellow marker accent (`#F2C94C`), inked typography. This is the original author's signature look for Latin-America-themed short-form content.

**Important for forkers**: the templates inline their colors directly. The `themes/` directory is a **canonical reference** documenting what the standard looks like, but it does not act as a runtime dependency.

To rebrand:
1. Copy `themes/hana.css` to `themes/<your-brand>.css`, edit the color tokens
2. In each template's `<style>` block, find the `:root` section and replace the color values to match
3. Or globally `sed` the hex codes across all templates

A future version may extract these into linked stylesheets (see `CONVENTIONS.md § 9`), but for now templates remain self-contained so a single `cp` is enough to drop them into a project.

---

## Safe zones

Simple rule: **leave the top 10% empty, leave the bottom 15% empty, don't let text content touch the edges.** This is a craft rule (gives breathing room for platform UI variants) rather than a precise device-by-device measurement, and is generous enough to survive iPhone Dynamic Island variants + 抖音/小红书/视频号/Reels/Shorts top & bottom chrome.

On a 1080×1920 canvas:

| y range | Use |
|---|---|
| **0–192** (top 10%) | ⛔ No readable text/numbers/key icons — leave space for Dynamic Island, status bar, platform top UI |
| 192–1632 (75%) | ✅ Main usable area — cards, animations, chyrons, talking head |
| **1632–1920** (bottom 15%) | ⛔ No high-signal content — auto-captions, account chips, like/comment, product cards, CTA |

See `CONVENTIONS.md § 3` for ready-to-use position constants the templates already obey (chyron `top: 16%`, cutaway `top: 280px`, opener `padding-top: 280px`).

---

## What this skill is **not**

- ❌ Stock-footage scraper (Pexels / Pixabay etc.) — out of scope for this skill
- ❌ Voice-over generator — use the [`hyperframes`](https://www.hyperframes.dev) skill's TTS module
- ❌ 16:9 horizontal support (v2 roadmap)
- ❌ Auto content compliance review — use the `content-audit` skill before publishing

---

## Roadmap (v2 ideas)

- **16:9 horizontal support** — every template needs a landscape variant + separate safe zone rules
- **Theme system A-plan** — extract CSS into linked stylesheets, ship neutral.css as default for forkers
- **Safe zone calibration video** — committed to `examples/safe_zone_calibration/` for users to verify on their own devices
- **`compose.py`** — in-pipeline subtitle burning (currently `add_subtitles.py` is a post-edit tool)
- **Gallery enhancements** — recorded GIF previews instead of live iframes

---

## Origin

This skill was built incrementally while producing a series of Chinese 9:16 short-form videos on Latin America travel ("拉美系列 / 巴西免签系列") and AI literacy ("AI 101 / Claude Code 扫盲"). Many design choices encode lessons learned the hard way — see `recipes/PITFALLS.md` for the 22 most expensive mistakes.

---

## License

MIT — see [LICENSE](LICENSE).
