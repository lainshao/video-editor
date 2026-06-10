// ───────────────────────────────────────────────────────────────────
// render_cue_puppeteer.js — Node 25 下渲 animator/opener cue 的逐帧方案
//
// 为什么不用 timecut：timecut 在 Node 25 会挂死（卡在帧捕获协议）。
// 本脚本用 puppeteer-core 直驱系统 Chrome，逐帧 seek GSAP timeline.main
// 再 omitBackground 截透明 PNG —— 又快又确定，不挂。
//
// cue HTML 约定（opener / chyron / scene_listicle / 自定义卡 都遵守）：
//   - window.__timelines.main = 暂停的 GSAP timeline
//   - window.__hyperframes_runtime 置位时不自动播放（本脚本靠它阻止自动播放，改逐帧 seek）
//
// 用法：
//   逐帧序列： node render_cue_puppeteer.js <htmlPath> <durationSec> <framesDir>
//   单帧静图： node render_cue_puppeteer.js <htmlPath> --t <sec> <outPng>
//
// 帧序列 → ProRes 4444 透明 mov：
//   ffmpeg -framerate 30 -i <framesDir>/f%04d.png \
//     -c:v prores_ks -profile:v 4 -pix_fmt yuva444p10le -r 30 cue.mov
// 合一条透明轨：见 recipes/compose_dual.sh.template 的 Output 2（默认透明 gap + cue concat）。
// ⚠ zsh 坑：lavfi 串里 duration=$DUR:rate 的 :r 会被当成修饰符把 93.7 啃成 93 → 写 ${DUR}。
// ───────────────────────────────────────────────────────────────────
const fs = require('fs');
const path = require('path');
const os = require('os');

const FPS = 30;
const CHROME = process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

// puppeteer 自动定位：先正常 require，再翻 npx 缓存（timecut/HyperFrames 会拉一份）
function loadPuppeteer() {
  for (const name of ['puppeteer-core', 'puppeteer']) {
    try { return require(name); } catch (e) {}
  }
  const base = path.join(os.homedir(), '.npm', '_npx');
  if (fs.existsSync(base)) {
    for (const d of fs.readdirSync(base)) {
      for (const name of ['puppeteer-core', 'puppeteer']) {
        const p = path.join(base, d, 'node_modules', name);
        if (fs.existsSync(p)) { try { return require(p); } catch (e) {} }
      }
    }
  }
  throw new Error('找不到 puppeteer-core / puppeteer（装一个或先跑一次 timecut/hyperframes 让 npx 拉缓存）');
}

const argv = process.argv.slice(2);
const htmlPath = argv[0];
let singleT = null, durSec = null, outTarget = null;
if (argv[1] === '--t') { singleT = parseFloat(argv[2]); outTarget = argv[3]; }
else { durSec = parseFloat(argv[1]); outTarget = argv[2]; }

if (!htmlPath || !outTarget || (singleT === null && !(durSec > 0))) {
  console.error('用法: node render_cue_puppeteer.js <html> <durationSec> <framesDir>');
  console.error('  或: node render_cue_puppeteer.js <html> --t <sec> <outPng>');
  process.exit(2);
}

(async () => {
  const puppeteer = loadPuppeteer();
  const browser = await puppeteer.launch({
    executablePath: CHROME, headless: 'new',
    args: ['--no-sandbox', '--hide-scrollbars', '--force-device-scale-factor=1', '--disable-lcd-text'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });
  // 阻止自动播放，改由我们逐帧 seek
  await page.evaluateOnNewDocument(() => { window.__hyperframes_runtime = true; });
  // ⚠ 用 domcontentloaded，别用 networkidle0（headless + Google Fonts 下永不 idle，会干等超时）
  await page.goto('file://' + path.resolve(htmlPath), { waitUntil: 'domcontentloaded', timeout: 60000 });
  // ⚠ 手动轮询，别用 page.waitForFunction（本组合 puppeteer-core 24 + Node 25 下有兼容 bug）
  let ready = false;
  for (let k = 0; k < 100; k++) {
    ready = await page.evaluate(() => !!(window.__timelines && window.__timelines.main));
    if (ready) break;
    await new Promise(r => setTimeout(r, 100));
  }
  if (!ready) throw new Error('timeline.main 一直没出现（检查 cue HTML 是否设了 window.__timelines.main）');
  await page.evaluate(async () => {
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
    window.__timelines.main.pause();
  });
  await new Promise(r => setTimeout(r, 400)); // 字体/布局稳定

  if (singleT !== null) {
    await page.evaluate(t => { window.__timelines.main.time(t); }, singleT);
    await page.screenshot({ path: outTarget, omitBackground: true, type: 'png' });
    console.log('OK 单帧 t=' + singleT + ' -> ' + outTarget);
  } else {
    fs.mkdirSync(outTarget, { recursive: true });
    const N = Math.round(durSec * FPS);
    for (let i = 0; i < N; i++) {
      await page.evaluate(t => { window.__timelines.main.time(t); }, i / FPS);
      await page.screenshot({ path: path.join(outTarget, 'f' + String(i).padStart(4, '0') + '.png'), omitBackground: true, type: 'png' });
    }
    console.log('OK ' + N + ' 帧 -> ' + outTarget);
  }
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
