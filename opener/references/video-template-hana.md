# Video Template Hana — 完整短视频配方

This recipe documents **Video Template Hana**, the full vertical short-form video format that this `broll-opener` skill plugs into. The kinetic gold-keyword title card produced by the parent skill is just the first 3.5 seconds of this template — read this file when building a complete short, not just the title card.

The template is named after careerhannah on Instagram (the reference video that established its visual language). It's a high-engagement format designed for IG Reels, TikTok, 小红书, and YouTube Shorts.

## When this template applies

Use this when the user wants a vertical short-form video that:

- Opens with a hook question or statement
- Is anchored by talking-head footage (the creator on camera) for most of its length
- Cuts to visual aids (screenshots, big text cards, data) at key moments to reinforce specific points
- Targets 30–90 seconds total
- Lives on IG / TikTok / 小红书 / YouTube Shorts

Do NOT use this template for: documentary-style edits, music-driven montages, vlog cuts, dialogue-heavy scenes with multiple speakers, or anything longer than 90 seconds.

## The four-layer stack

Every Hana-style composition is the same four layers, stacked z-bottom to z-top:

```
┌─────────────────────────────────────┐  z=30  (top)
│  TITLE CARD     0–3.5s only         │  Kinetic gold-keyword opener
│  (covers everything during opener)  │  ← see broll-opener skill
├─────────────────────────────────────┤  z=20
│  B-ROLL TAKEOVERS                   │  Full-canvas cards at 4–6 key beats
│  (cover talking head briefly)       │  Slide-in / Ken Burns / slide-out
├─────────────────────────────────────┤  z=10
│  CAPTIONS (big white text)          │  1–3 words at a time, sync'd to speech
│  (always above talking head)        │  Bottom 30% of canvas
├─────────────────────────────────────┤  z=1   (bottom)
│  TALKING HEAD VIDEO                 │  The creator on camera
│  (full canvas, plays continuously)  │  Audio drives the whole timeline
└─────────────────────────────────────┘
```

The talking head and its audio are the **timeline spine** — every other element is positioned relative to what's being said. Build that layer first, then layer everything else on top.

## Timing budget for a 60-second short

| Section | Duration | What's on screen |
|---|---|---|
| **Hook** | 0 – 3.5s | Kinetic title card (use `broll-opener` skill) |
| **Body** | 3.5 – 55s | Talking head + 3–5 B-roll takeovers + continuous captions |
| **CTA** | 55 – 60s | Talking head only with bottom-half text card "Comment your X" |

Adjust proportionally for 30s or 90s versions.

## Layer 1: Talking head (the spine)

**Recording requirements:**
- Vertical 1080×1920 (or anything that crops cleanly to 9:16)
- Speaker centered or slightly upper-third
- Audio volume normalized — this layer drives the whole timeline
- 30 fps, dense keyframes (`-g 30 -keyint_min 30` if re-encoding)
- **NOT HDR** — convert to SDR before passing to HyperFrames. iPhone footage defaults to HDR (HLG) and the renderer's HDR composite path can break clip-visibility logic. Force SDR with explicit color flags:
  ```bash
  ffmpeg -i source.MOV -vf "format=yuv420p" \
    -c:v libx264 -crf 22 -r 30 -g 30 -keyint_min 30 \
    -color_primaries bt709 -colorspace bt709 -color_trc bt709 \
    -x264-params "colorprim=bt709:transfer=bt709:colormatrix=bt709" \
    -c:a aac -b:a 128k -movflags +faststart \
    talking-head.mp4
  ```
  If the source is true HDR (PQ or HLG), you also need a tone-map step (zscale + tonemap, or ffmpeg with libplacebo). Verify with `ffprobe -show_entries stream=color_primaries,color_transfer` — `color_primaries` should read `bt709`, NOT `bt2020`.

**HyperFrames pattern** (mute the video, separate audio element drives sound):
```html
<video id="th-vid" class="clip"
  data-start="3.5" data-duration="56.5" data-track-index="0"
  src="talking-head.mp4" muted playsinline></video>
<audio id="th-aud" class="clip"
  data-start="3.5" data-duration="56.5" data-track-index="1"
  src="talking-head.mp4"></audio>
```

`data-start="3.5"` reserves the first 3.5s for the title card. The audio and video share the same source file but live on separate tracks because HyperFrames requires `muted` videos.

## Layer 2: B-roll takeovers (the visual punch)

These are full-canvas cards that briefly replace the talking head at moments where the speaker is making a specific visual point. The audio keeps playing — the speaker's voice carries through.

**Why full canvas, not upper-half overlay:**
The reference Hana video uses upper-half overlays because her talking head is framed with face in the lower 60% (lots of empty wall space above). Most user-recorded footage has the face in the upper-third (standard "selfie" framing), which means an upper-half overlay would cover the speaker's face. Full-canvas takeovers sidestep this — they work regardless of speaker framing. If the user's footage has Hana-style "face-low" framing, switch to upper-half overlays for a more layered feel.

**Card density:**
- 30s short → 2–3 cards
- 60s short → 4–5 cards
- 90s short → 5–7 cards

Don't go denser. Each card costs about 5–7 seconds of screen time, and viewers need to land on the talking head between cards to absorb continuity.

**Card archetypes** (most short-form B-roll fits one of these five):
1. **List intro** — "TWO TYPES" / "3 WAYS" — sets up the listicle structure
2. **Numbered reveal** — big "01" with category name, fires when the speaker says "first"
3. **Checklist** — 3 lines with checkmarks, fires when the speaker enumerates traits
4. **Stat callout** — single huge number with units and label, fires at a quoted figure
5. **Geo / map / arrow** — locations or transitions, fires for "from X to Y" or "in country Z"

**Motion recipe** (same for all cards):
```js
function brollTakeover({ slotSel, cardSel, startAt, holdDuration }) {
  // Slide in from above
  tl.from(slotSel, { y: -300, opacity: 0, duration: 0.55, ease: "expo.out" }, startAt);

  // Ken Burns drift on the inner card (subtle scale + horizontal pan)
  tl.fromTo(cardSel,
    { scale: 1.00, x: 0 },
    { scale: 1.05, x: -10, duration: holdDuration, ease: "none" },
    startAt);

  // Exit pulls back up. Last 0.4s of the visible window is exit motion.
  tl.to(slotSel, { y: -300, opacity: 0, duration: 0.40, ease: "power2.in" },
    startAt + holdDuration - 0.55);
}
```

The cards have non-overlapping `data-start`/`data-duration` ranges on the same `data-track-index` so HyperFrames swaps them cleanly. Leave a 0.2–0.3s gap between cards (the talking head shows briefly between them) — back-to-back cards feel like a slideshow, not a video.

## Layer 3: Big captions

Hana's signature captions are HUGE white text in the bottom 30% of the canvas, showing 1–3 words at a time, with the current word or phrase visually emphasized (color shift, size bump, or scribble underline).

**Why big captions matter for this format:**
- 70%+ of short-form viewers watch with sound off
- Captions retain attention through pacing changes
- Highlighted words ("creative", "国际化") become memorable visual hooks

**Style:**
- Font: same family as the title (`Inter` 900 / `Noto Sans SC` 900)
- Size: 100–130px (much bigger than typical YouTube captions)
- Position: `bottom: 280px; left/right: 60px;` centered horizontally
- Color: pure white with a soft drop-shadow `0 4px 0 rgba(0,0,0,0.4), 0 8px 24px rgba(0,0,0,0.5)`
- Highlighted word: same color as the title's gold keyword, OR a scribble underline (CSS pseudo-element with a hand-drawn underline image)

**Generation:**
Use HyperFrames' `transcribe` command with `--word-level` if available (or `whisper` directly with `--word_timestamps True`) to get word-level timestamps. Then for each phrase group, create a clip with `data-start` and `data-duration` matching the speech timing. The HyperFrames captions reference (`hyperframes` skill, references/captions.md) covers the full pattern.

**Don't ship captions if you only have segment-level timestamps** — they'll desync from the speech and feel worse than no captions. Better to skip this layer in v1 and add it in v2 once word-level timing is available. If transcription with `large-v3` keeps failing on a specific environment, fall back to `medium` model + manual timing for the chosen 30–60s segment (small enough to time by hand from a transcript text file).

## Layer 4: CTA card (the close)

The final 3–8 seconds. Talking head still shows, but a full-width text bar appears at the bottom: "Comment your X" or "你觉得 Y 吗？". Hana typically ends with a direct question — "Comment what you'd build" — to drive comment volume.

Keep the CTA short (≤8 words), put it on a colored bar at the bottom (not a full takeover card), and let the speaker deliver the matching line on audio.

## Pacing rules (the rhythm that makes it feel "designed")

1. **No silent gaps in the audio.** If the speaker's source has long pauses, cut them out — every second should have either speech or a meaningful sound effect.
2. **B-roll cards land ON the speaker's emphasis word.** Time the slide-in to coincide with "the FIRST type is..." — not 0.5s before, not 0.5s after.
3. **Don't crossfade between B-roll cards.** Hard out, hold a beat on the talking head, hard in on the next card. The brief talking-head flash is the rhythm.
4. **The keyword in the title and the keyword in any pull-quote card should be the same color** (the gold). This visual rhyme makes the video feel coherent.
5. **First 3 seconds carry the entire hook.** If the title card doesn't grab attention by t=3s, the rest doesn't matter — it's the reason the format works.

## What kills this format

Watch for these and push back if the user requests them:

- **Multiple talking heads** — this template assumes one creator on camera. Cut interviews need a different format.
- **Dense captions filling the whole screen** — defeats the "1–3 words at a time" rhythm. Reduce phrasing.
- **B-roll cards that match the speaker's cadence too closely** — feels like a slideshow. Leave gaps.
- **Background music louder than -16 LUFS** — overpowers speech, kills retention.
- **Title card longer than 4s** — viewers swipe away. 3.5s is the sweet spot.
- **Aspect ratio anything other than 9:16** — square crops kill engagement on Reels/TikTok.

## Building order (when implementing)

1. Get the source talking-head video, convert to SDR if needed.
2. Decide the cut: which 30–90s segment from the source? Trim it.
3. Build the title card via the parent `broll-opener` skill.
4. Wire the trimmed talking-head into the composition as Layer 1 (video + audio).
5. Identify 3–5 emphasis moments and build B-roll cards for each (Layer 2).
6. (If word-level transcript available) build captions (Layer 3).
7. Build the CTA bar (Layer 4).
8. Lint + render. Adjust card timings based on what feels rushed or sluggish.

The whole composition's `data-duration` on the root should match `3.5 + (talking-head trim duration)`.

## Reference implementations

- Title card alone: `broll-sample/kinetic-title/`
- Title + talking head + 4 B-roll takeovers (no captions): `broll-sample/hana-cut/`
- B-roll templates (3 card archetypes, no talking head): `broll-sample/screenshot-overlay/`

These exist on the original creator's machine; if you're picking this up later or on another machine, the patterns are reproducible from this recipe alone.
