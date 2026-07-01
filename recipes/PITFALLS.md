# PITFALLS — broll-compose

Hard-won technical traps. Read before iterating, save time.

## HyperFrames

### 1. Slice fade-in tail bleeds previous scene
**Symptom**: cutaway starts with 0.2-0.4s flash of the previous scene's content.
**Cause**: HyperFrames reels use 0.4s fade-in/fade-out per scene. Slicing at exact scene boundary catches the previous fade-out tail.
**Fix**: Offset slice start by 0.5s.
```bash
# WRONG:
ffmpeg -ss 9 -i broll_reel.mp4 -t 3 ...   # catches scene 3 fade-out

# RIGHT:
ffmpeg -ss 9.5 -i broll_reel.mp4 -t 2.5 ...   # clean scene 4 only
```
Exception: scene 1 (`-ss 0`) needs no offset — nothing precedes it.

### 2. Parallel render race
**Symptom**: out of 8 parallel renders, one fails with cryptic 404 or "Failed to launch".
**Cause**: HyperFrames CLI has occasional contention with shared Chrome temp state.
**Fix**: Just retry the failed one serially. Don't re-render the rest.

### 3. WebM transparency doesn't work
**Symptom**: `--format webm` outputs `pix_fmt=yuv420p` (no alpha) despite docs saying transparent.
**Cause**: VP9 alpha encoding inconsistent across HyperFrames build versions.
**Fix**: Use `--format mov` for ProRes 4444 (always `yuva444p12le`). For browser preview, composite mov+cream-bg via ffmpeg into mp4.
```bash
ffmpeg -f lavfi -i "color=color=0xFAF6EF:size=1080x1920:duration=3:rate=30" \
       -i scene.mov -filter_complex "[0:v][1:v]overlay=format=auto:shortest=1" \
       -c:v libx264 -pix_fmt yuv420p scene_preview.mp4
```

### 4. Chinese path triggers macOS TCC permission
**Symptom**: HyperFrames render fails with EPERM when project is under a Chinese-named directory.
**Fix**: Always work in `/tmp/joey_build/` or another ASCII path. Symlink final outputs back to user's project dir.

### 5. GSAP `from()` initial state captured by render
**Symptom**: Poster frame extracted right after timeline start shows blank/initial state.
**Cause**: `gsap.from()` sets element to from-state initially; only animates toward natural state.
**Fix**: Extract poster late (after all `from()` durations have elapsed). For 3s clips, use `-ss 2.5` or `-ss 2.7`.

## ffmpeg

### 6. Color filter `#` shell-eaten
**Symptom**: `Error opening input files: Invalid argument` on `color=#FAF6EF`.
**Fix**: Use hex with `0x` prefix:
```bash
# WRONG:
-i "color=#FAF6EF:size=1080x1920..."

# RIGHT:
-i "color=color=0xFAF6EF:size=1080x1920..."
```

### 7. ffprobe trailing newline breaks shell composition
**Symptom**: `dur=$(ffprobe ... -of default ...)` then `ffmpeg ... -duration $dur` fails.
**Fix**: Strip whitespace:
```bash
dur=$(ffprobe ... -of default=noprint_wrappers=1:nokey=1 file.mov | tr -d '[:space:]')
```

### 8. `cp` over symlink doesn't always replace cleanly
**Symptom**: After `cp newfile.mp4 link.mp4`, link.mp4 still resolves to old target.
**Fix**: `rm -f link && cp newfile.mp4 link`. Avoid relying on `cp -f` to dereference symlinks.

### 9. `moov atom not found` mid-write
**Symptom**: ffprobe / play attempt fails with this error on a file that's still encoding.
**Fix**: Wait for ffmpeg to finish before reading. With background processes:
```bash
until ! pgrep -f "ffmpeg.*output.mp4" > /dev/null; do sleep 5; done
```

### 10. media fragment + loop attribute incompatible
**Symptom**: `<video src="clip.mp4#t=0,3" loop>` plays once and stops in Safari/Chrome.
**Cause**: When fragment end == file duration, browsers don't loop reliably.
**Fix**:
- For standalone clips (file is the full clip): drop the fragment entirely. Plain `src="clip.mp4"` + `loop`.
- For sliced clips (fragment selects a range): attach manual `timeupdate` listener:
```js
v.addEventListener("timeupdate", () => {
  if (v.currentTime >= end - 0.05) v.currentTime = start;
});
```

### 11. Overlay enable=between(t,X,Y) end-edge precision
**Symptom**: cutaway visible 1 frame past intended end.
**Fix**: Use exclusive end (e.g. `between(t,6,8.999)` instead of `between(t,6,9)`) when adjacent overlay starts at the same time. Usually doesn't matter, but worth knowing.

### 12. Overlay alpha format hint
For ProRes 4444 alpha overlays, use `format=auto`:
```
overlay=enable='...':format=auto
```
Without `format=auto`, alpha can be flattened to opaque.

### 23. Alpha broll overlayed onto a transparent base turns cream cards gray
**Symptom**: `spec_review.html` and each cue MOV look correct, but the final `*_broll层.mov` becomes dark gray when placed over the talking-head video. Cream card backgrounds that should read around `srgb(250,245,237)` show up around `srgb(62,60,60)`.

**Cause**: A full-length transparent canvas like `black@0.0` plus repeated `overlay` can leave semi-transparent pixels with premultiplied-looking RGB. Later, the NLE or ffmpeg treats the ProRes 4444 layer as straight alpha and the card gets darkened twice.

**Fix**: For non-overlapping cues, compose the alpha layer by concatenating transparent gaps and rendered cue MOVs:
```
gap_before_cue_1 + cue_1 + gap_between + cue_2 + ... + tail_gap
```
Compute gaps from the **actual** cue duration reported by `ffprobe`, not only from planned timestamps. If a cue rendered 245 frames instead of the planned 270 frames, the next transparent gap must absorb the difference.

Only use an overlay chain for truly simultaneous layers; when possible, render those simultaneous elements into one cue first and then concat that cue into the final alpha track.

**Required QA before delivery**: overlay the final broll MOV onto the original speech video and make a keyframe contact sheet. This catches alpha color, timing, and face-occlusion bugs that the HTML spec review cannot see.

## ProRes 4444 alpha output

Required encoder settings:
```bash
-c:v prores_ks -profile:v 4 -pix_fmt yuva444p10le
```
- profile 4 = ProRes 4444 (alpha-capable)
- yuva444p10le = 10-bit with alpha
- File size: ~30-50 MB per second at 1080×1920. A 122s alpha layer ≈ 450 MB.

## Whisper transcription

### 13. Default install of whisper.cpp doesn't ship multilingual model
**Symptom**: Brew install gives only `for-tests-ggml-tiny.bin` (English-only).
**Fix**: Download Chinese-capable model:
```bash
curl -sL -o ~/.cache/whisper/ggml-base.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin
# Use with: whisper-cli -m ~/.cache/whisper/ggml-base.bin -f audio.wav -l zh -ovtt
```
For higher accuracy on Chinese names: `ggml-small.bin` (466 MB) or `ggml-large-v3.bin`.

### 17. Chyron + 动画同屏期间视觉过载
**Symptom**: 用户反馈"太繁杂"，chyron 黄胶囊和动画 callout box 同时在屏几秒钟看着挤。
**Cause**: chyron 在 cue 开始就 fade in 然后留到 cue 结束（默认 timeline），动画 1s 后才进 → 重叠 ~3-7s 双元素同屏。
**Fix**: 用 3 段时序：
```
0.0s → chyron fade in (back.out 0.35s)
1.0s → chyron fade OUT (power2.in 0.35s) + 动画 fade IN（同步）
...  → 动画 solo 直到 cue 结束
end  → 动画 fade out
```
代码片段（GSAP）：
```js
tl.to("#cw", { opacity: 1, y: 0, scale: 1, duration: 0.35 }, 0.0);
tl.to("#cw", { opacity: 0, y: -10, duration: 0.35, ease: "power2.in" }, 1.0);  // 关键：1.0s 淡出
tl.to("#anim", { opacity: 1, duration: 0.40 }, 1.0);  // 同步入场
```

### 20. cutaway 头部塞 3 行（eyebrow + title + subtitle）信息过载
**Symptom**: 用户反馈"标题上面三行信息太多，大家看不清"。
**Cause**: 模仿网页 hero 区做了 eyebrow（"邵黑瘦·反向版"）+ 主标（"巴西 10 天"）+ 副标（"里约压最后·圣保罗起步"）三层堆叠。视频上观众扫不过来。
**Fix**: 标题区**只留 1 行核心字**，eyebrow/subtitle 该删删 —— 真要传达"反向版"信息让口播说出来，画面省力。

### 22. Climax 段用整块高饱和色背景 → "太黄/太红"廉价感
**Symptom**: 用户反馈"黄色面积太大块了，太黄了"。把最后一段做成纯黄/纯红 gradient 整张卡 → 大色块刺眼 + 跟前面 phase 卡片视觉断裂。
**Cause**: 模仿"促销/特卖"卡片设计逻辑，整块单色填满想强调"压轴"。但视频内容卡片调性不需要这种 hype。
**Fix**: 收尾段保持**白底 + 浅 tint** 跟其他段一致，仅用 ① 彩色边框（3px） ② 右上 ribbon 角标（约 5% 屏占）表达"特殊"。详见 SKILL.md「Climax / 收尾段强调」节。

### 21. cutaway 多段全显 → 观众扫不过来
**Symptom**: 时间轴 / 多段对比表 cutaway 把 4-6 段全显屏上，口播讲到某段时观众找不到对应的视觉重点。
**Cause**: 模仿 PPT 的"全显示+灰掉不讲的"策略。但视频是流不是页，观众不能暂停扫。
**Fix**: 走"一次一段 + 进度条"范式 —— 顶部 day-strip 进度条高亮当前段，主舞台 absolute 切换只显当前 phase 卡片。详见 SKILL.md「Cutaway 多段时间轴 默认用'一次一段 + 进度条'」节。

### 19. cutaway 卡片字号小于 22px → 手机上不可读
**Symptom**: 全屏 cutaway / 时间轴卡 / 决策矩阵 等"信息卡"在 spec_review 看着还行，渲染到手机上一片模糊看不清。
**Cause**: canvas 1080×1920 在手机上缩到 ~390px 宽（scale ~0.36）。canvas 上 14px → 手机上 5px，不可读阈值。
**Fix**: 所有文字字号 ≥ **22px**（手机上 ~8px 起步刚能读）。层级公式见 SKILL.md「字号层级」节。
**预防**：写 cutaway HTML 时心算 `font-size * 0.36`，<8px 一律放大。或 grep `font-size: [0-9]px\|font-size: 1[0-9]px` 找小字。

### 18. Chyron 顶边和动画顶边不对齐 → 看到"边边"
**Symptom**: chyron 淡出 + 动画进场过渡瞬间，用户能看到 chyron 旁边一条 callout box 的边缘"探出来"再被覆盖。
**Cause**: chyron 在 y≈237（top:16% 中心 - pill/2），动画在 y=100 / y=400 之类。两者顶边不重合 → 过渡帧里动画顶边 visible 在 chyron 下面或上面。
**Fix**: 动画容器**顶边也设到 y≈250–280**（同时这也是顶部 UI 死区 y<250 的安全线）：
- 绝对定位卡片：`top: 280px`
- 中心锚 + `translate(-50%,-50%)`：center y ≈ 250 + height/2，反推 `top: X%`（常见 18%-22%）

视觉效果：chyron 消失 → 动画从同一个 y 位置接力 → 无边缘错位。

⚠ 不要把 chyron / 动画顶边回到 y=21 / y=100：那是 Dynamic Island / 状态栏 / 平台关注按钮的死区，iPhone 上会被切。

## Spec review iframe

### 14. iframe 默认不 scale，卡片只看到左上角 1/4
**Symptom**: spec_review.html 卡片里只显示 1080×1920 内容的左上角小块，不是完整的 9:16 内容。
**Cause**: iframe 加载 1080-wide HTML，但卡片宽度只有 ~300px。如果不缩放，iframe 视口比 body 小，只显示 clip。
**Fix**: JS 钩子在 load + resize 时设 `transform: scale(wrap.clientWidth / 1080)`，配合 `transform-origin: top left` + iframe `width: 1080px`。

```css
.iframe-wrap { position: relative; aspect-ratio: 9 / 16; overflow: hidden; }
.iframe-wrap iframe {
  position: absolute; top: 0; left: 0;
  width: 1080px; height: 1920px;
  transform-origin: top left;
  transform: scale(0.25);  /* JS overrides */
}
```
```js
function scaleIframes() {
  document.querySelectorAll(".iframe-wrap").forEach(wrap => {
    const iframe = wrap.querySelector("iframe");
    if (!iframe) return;
    const w = wrap.clientWidth;
    if (w > 0) iframe.style.transform = "scale(" + (w / 1080) + ")";
  });
}
window.addEventListener("resize", scaleIframes);
window.addEventListener("load", scaleIframes);
```
纯 CSS 解法（cqw/vw）会撞 `transform: scale() rejects length` 坑，必须 JS。模板 `templates/spec_review_template.html` 已内置这个钩子。

### 16. spec_review SCENES 数组 warn/script 字符串里的直引号
**Symptom**: spec_review.html 打开后只有 header + 说明文字，timing 表空，cue 卡片网格不出现。
**Cause**: SCENES 数组里某个 `warn:"...含"X"..."` 或 `script:"...含"Y"..."` 字符串包含**未转义的直引号** → JS 解析 SCENES 数组语法错 → 后续 `render()` 全部不跑。错误在浏览器 console 里有，但页面看不出来。
**Fix**: 字符串里的内层引号一律用**中文「」或""（curly quotes）**，不要用直引号。
```js
// WRONG — 直引号嵌套：
warn:"按你定不画城市，emoji 表达"哭崩"。"

// RIGHT — 中文括号：
warn:"按你定不画城市，emoji 表达「哭崩」。"

// 或转义（不优雅但管用）：
warn:"按你定不画城市，emoji 表达\"哭崩\"。"
```
**预防**：写 SCENES 时 grep 自查 `grep -n '"[^"]*"[^"]*"' file.html` 找嵌套直引号。

## Overlay 长度阈值

### 15. listicle 全屏 cutaway 超过 6s 阻塞 talking head 节奏
**Symptom**: 6.5s+ 全屏 cream listicle cutaway 让观众等太久，talking head 完全消失节奏断。
**Cause**: scene_listicle.html 是"一锤定全屏"模式，长内容（5+ 项）一次性塞不下。
**Fix**: 改用 `scene_progressive_top_card.html` —— 卡片渐进出现、跟着口播节奏逐项 reveal、末尾 2-3s phase B 全屏 recap。拉美 04 实测：6.5s 全屏 cutaway → 50.7s 渐进式后用户认可。
**经验规则**：listicle 项数 ≤ 4 用 `scene_listicle.html`；≥ 5 项用 `scene_progressive_top_card.html`。

## Stock B-roll

实拍素材（Pexels/Pixabay/Mixkit/GIPHY）抓取走 `b-roll-generator` skill，本 skill 不直接抓。其相关坑（API rate limit、aspect mismatch blur-fill、抓取后处理）见 `~/.claude/skills/b-roll-generator/`。

## 抠像人物 / Alpha / 字幕

### 17. 剪映/CapCut 的「透明视频」是 Apple HEVC alpha，ffmpeg 解不出 alpha
**Symptom**: 用户在剪映/CapCut 导了「透明背景」人物视频给你 overlay，结果叠上去是**黑底**不是透明。`ffprobe` 显示 `pix_fmt=yuv420p`（不是 yuva）。
**Cause**: 剪映 Mac 导透明用的是 **Apple HEVC alpha**（alpha 存成辅助层），brew ffmpeg 的 hevc 解码器只读基础层、丢 alpha。
**Fix**: 用 macOS 自带 `avconvert` 转成 ProRes 4444（ffmpeg 能读 alpha）：
```bash
avconvert -s in.mov -o /tmp/out.mov -p PresetAppleProRes4444LPCM   # 输出必须 /tmp，路径不能有中文！
ffprobe ... → pix_fmt=yuva444p12le ✅
ffmpeg -i /tmp/out.mov -vf scale=1080:1920 -c:v prores_ks -profile:v 4 -pix_fmt yuva444p10le person.mov  # 降分辨率删 10GB 临时
```
**坑**：avconvert 输出路径含中文/特殊字符 → `Cannot create file`。ProRes4444 体积巨大（162s@4K≈10GB），降到 1080 后删临时文件。
**分工建议**：真人抠像让用户在剪映一键做（本地 rembg 抠 4K 直接 OOM，质量也差），你只 avconvert + overlay 合成。

### 18. 本机 ffmpeg 无 libass/drawtext → 字幕/文字只能 PNG overlay
**Symptom**: `ffmpeg -filters | grep subtitles` 空；`-vf subtitles=...` / `drawtext=...` 报 No such filter。
**Cause**: brew ffmpeg 8.x 这个 build 没编 libass/libfreetype。
**Fix**: 走 `subtitle/` 子模块的 PNG overlay 路线（Pillow 渲透明 PNG → ffmpeg overlay）。已有清洗好的 SRT 时用 `add_subtitles.py --srt clean.srt`（跳过 whisper）；超宽 CJK 句 `subtitles.py` 会自动按标点拆分不被裁。
