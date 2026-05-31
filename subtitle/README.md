# subtitle · 字幕子模块

给任意 9:16 成片烧字幕：**whisper 自动转写 → 术语修正 → 关键词高亮 PNG → ffmpeg overlay 烧入**，保留原音。

**libass-free** —— 不依赖 ffmpeg 的 `subtitles`/`ass` filter（macOS brew ffmpeg 默认没 libass），用 Pillow 把每句字幕渲成透明 PNG 再 overlay。

**不走三道门** —— 这是单点后处理工具，跑一条命令完事。

## 装依赖

```bash
# Python 依赖（仅 Pillow）
pip install -r ~/.claude/skills/video-editor/subtitle/requirements.txt

# 系统 binary（必须在 PATH）
brew install ffmpeg          # 烧字幕用
brew install whisper-cpp     # 转写用（注意命令名是 whisper-cli 不是 whisper）

# Whisper 模型（默认大模型，转写质量好）
mkdir -p ~/.whisper-models
curl -L -o ~/.whisper-models/ggml-large-v3-turbo.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
```

## 用法

```bash
# 最简：默认转中文 + 烧字幕，输出 <video>_subtitled.mp4
python ~/.claude/skills/video-editor/subtitle/add_subtitles.py speech.mov

# 加自定义关键词（高亮成黄色）
python add_subtitles.py speech.mov --keywords "Claude Code,statusline,/status"

# 用自定义修正词典（"contact"→"context" 这种 whisper 错听修正）
python add_subtitles.py speech.mov --corrections my_corrections.txt

# 指定输出
python add_subtitles.py speech.mov --out final_with_subs.mp4

# 高质量编码（默认 videotoolbox 快；--quality 走 libx264 CRF 19 慢但小）
python add_subtitles.py speech.mov --quality

# 改字幕位置（默认 bottom margin 375px 避开平台底部 UI）
python add_subtitles.py speech.mov --margin 400

# 英文视频
python add_subtitles.py speech.mov --lang en
```

## 样式规范

| 属性 | 值 | 备注 |
|---|---|---|
| 字号 | 58px | 1080×1920 canvas 上 |
| 底部 margin | 375px from bottom | 避开自动字幕 / 商品卡 / 关注 CTA 死区 |
| 背景框 | 半透明黑 alpha 165 (~65%) + 圆角 16px | 文本可读 |
| 主字色 | 白 `#FFFFFF` | |
| 关键词高亮 | 暖金 `#FFD320` | 与 animator 的 chyron 黄 `#F2C94C` 不一致——开源前应统一 |
| 字体 | PingFang SC Semibold → Hiragino → STHeiti → Arial Unicode | CJK fallback chain |

样式调整改 `subtitles.py` 顶部常量：
```python
SUB_FONT_SIZE = 58
SUB_MARGIN_V = 375
SUB_BOX_ALPHA = 165
SUB_RADIUS = 16
SUB_YELLOW = (255, 211, 32, 255)
```

## 关键词高亮：两种方式

**方式 1 · CLI 传词列表**：
```bash
--keywords "Claude Code,statusline,token"
```
匹配到这些子串的字幕段被涂成黄色。匹配按 longest-first 优先（避免 "status" 抢了 "statusline" 的高亮）。

**方式 2 · 字幕里直接打 `**bold**`**：

如果你在 corrections 里把某句改成 `这里要**重点**强调`，PNG 渲染时 `**重点**` 会被涂黄。比 `--keywords` 灵活，因为可以精确控制单句里哪个词高亮。

两种方式可以混用。

## 术语修正词典（corrections）

whisper 经常听错：`cloud` 听成 `Claude`、`contact` 听成 `context`、`get` 听成 `git`、`中端` 听成 `终端`。所以转写出来要跑一遍修正。

`corrections_example.txt` 是个示例（Claude Code 视频系列的语料）。格式：

```
# 注释行
<错> => <对>
cloud => Claude Code
contact => context
中端 => 终端
```

- 一行一条，`=>` 分隔，顺序应用（顶部到底部）
- `#` 开头是注释
- 长字符串放上面（优先匹配），短的放下面
- 你应该按**自己的视频内容**写新的，不要直接用 Claude Code 系列的语料

## 工作流

```
任意 9:16 mp4 / mov
  ↓ 1. ffmpeg 抽音轨成 16kHz mono pcm wav
  ↓ 2. whisper-cli 转写 → JSON（带时间戳）
  ↓ 3. 应用 corrections（"cloud"→"Claude Code" 等）
  ↓ 4. Pillow 把每段字幕渲成透明 PNG
       - 半透明黑圆角框 + 白字 + 黄关键词
       - 自动量宽（紧贴文字 + padding）
  ↓ 5. ffmpeg overlay 链：每段字幕在自己时间窗内 overlay 到视频上
       - 保留原音
       - videotoolbox / libx264 编码
  ↓ 6. 输出 <name>_subtitled.mp4
```

## 进 video-editor 全流程时

主模块路由问询用户选 "④ 全流程" 时，subtitle 会在最后一步**自动**跑（在 animator 渲完整片 mp4 之后）。这时通常不需要你手工调 CLI，主模块会代为执行。

如果只走 ④ 中的某个子步骤（比如已经有 animator 渲出的 mp4，只补字幕），就走 `add_subtitles.py` CLI。

## 已知坑

- **whisper 多语言模型选错**：brew 自带的 `ggml-tiny.bin` 是英文 only。中文必须用 `ggml-base.bin` / `ggml-small.bin` / `ggml-large-v3-turbo.bin`（从 HuggingFace 下）
- **ggml-large-v3-turbo.bin 占 1.6 GB**：第一次下载慢。如果磁盘紧张可降级到 `ggml-base.bin`（~150MB）但中文识别准确率会掉
- **关键词长 vs 短匹配**：`--keywords "status,statusline"` 时，先 split "statusline" 才不会被 "status" 截一半。代码已经按 longest-first 排序，但传参顺序无所谓
- **CJK 字体缺失**：macOS 自带 PingFang，Linux 没有，要手动指定字体路径
