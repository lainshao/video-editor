#!/usr/bin/env python3
"""稳健逐帧渲染 opener 透明帧（Node 25 下 timecut 会挂，用这个替代）。

用法:
  python3 render-opener-frames.py <opener.html> <out_frames_dir> [duration_s] [fps]

原理: 仿 doc-to-slides/render.py —— 每帧 Popen 启 headless chrome 截图 + 轮询 PNG
稳定 + 主动 kill（headless chrome 截完常不退出，必须 kill，否则阻塞）。
opener.html 必须支持 ?t=<秒> 同步 seek（template-anthropic.html 已内置）。

渲染完接着跑:
  ffmpeg -y -framerate <fps> -i <out_dir>/frame_%04d.png \\
    -c:v prores_ks -profile:v 4 -pix_fmt yuva444p10le opener.mov
叠到 talking head:
  ffmpeg -y -i talkinghead.mov -i opener.mov \\
    -filter_complex "[0:v][1:v]overlay=0:0:eof_action=pass" \\
    -c:a copy -c:v libx264 -pix_fmt yuv420p -crf 18 preview.mp4
（中文文件名用 find 拿真实路径喂给 ffmpeg，避开 macOS NFC/NFD 编码坑）
"""
import subprocess, time, tempfile, sys
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    html = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    dur = float(sys.argv[3]) if len(sys.argv) > 3 else 4.5
    fps = int(sys.argv[4]) if len(sys.argv) > 4 else 30
    n = int(round(dur * fps))
    profile = str(Path(tempfile.gettempdir()) / "opener-render-profile")

    for i in range(n):
        t = i / fps
        png = out / f"frame_{i:04d}.png"
        if png.exists(): png.unlink()
        url = f"file://{html}?t={t:.4f}"
        cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
               f"--user-data-dir={profile}", "--no-first-run", "--no-default-browser-check",
               "--disable-extensions", "--disable-background-networking", "--disable-sync",
               "--window-size=1080,1920", f"--screenshot={png}",
               "--default-background-color=00000000", "--hide-scrollbars",
               "--force-device-scale-factor=1", "--virtual-time-budget=2500", url]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        waited, stable, last = 0.0, 0, -1
        while waited < 20:
            time.sleep(0.25); waited += 0.25
            if png.exists():
                sz = png.stat().st_size
                if sz >= 2000 and sz == last:
                    stable += 1
                    if stable >= 2: break
                else:
                    last = sz; stable = 0
            if proc.poll() is not None: break
        proc.terminate()
        try: proc.wait(timeout=2)
        except subprocess.TimeoutExpired: proc.kill()
        if (i + 1) % 30 == 0:
            print(f"  ...{i+1}/{n}", flush=True)

    done = len(list(out.glob("frame_*.png")))
    print(f"FRAMES_DONE {done}/{n}")
    sys.exit(0 if done >= n else 1)

if __name__ == "__main__":
    main()
