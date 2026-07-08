// ───────────────────────────────────────────────────────────────────
// lint_layout.js — 渲染后布局 lint（真实 DOM computed layout 检查）
//
// lint_template.sh 管"模板契约"（静态 grep）；本脚本管"这张 cue 渲出来
// 到底长什么样"——安全区、最小字号、文字宽度、居中、字号种数。
// 过去反复返工的坑（字幕太小/太细、标题不居中、文字超安全区、卡片太宽）
// 全是 computed layout 问题，只有渲染后才能抓到。
//
// ★ 工作流位置：门 2 写完每个 cue HTML 之后、生成 spec_review.html 之前，
//   对每个 cue 跑一遍。FAIL 必修再给用户看；WARN 在 spec review 里注明。
//
// 用法：
//   node recipes/lint_layout.js <cue.html>                    # 自动识别画幅
//   node recipes/lint_layout.js <cue.html> --preset 9x16      # 强制画幅
//   node recipes/lint_layout.js --all <目录>                   # 目录下全部 html
//   node recipes/lint_layout.js <cue.html> --json             # 机器可读输出
//
// 画幅预设与规则（单一事实源 = CONVENTIONS.md，改规则先改那边）：
//   9x16 (1080×1920) — CONVENTIONS §三/§五：文字 top≥192 / bottom≤1632 /
//                      左右边距≥80（文字宽≤920）/ 最小字号 22px
//   16x9 (1920×1080) — 四边 5% 边距 / 底部 12% 留进度条 / 右下 pip 区 WARN
//   3x4  (1080×1440) — slidecast 三铁律：内容顶部对齐（文字不进底部 1/3，
//                      底部留真人）/ 无页码
//
// 动画感知：cue 注册了 window.__timelines.main 时，在 progress
// 0.45 / 0.75 / 0.98 三个时间点各检一遍。位置类规则（安全区/边距/居中）
// 只在"落定"时判定——违规须出现在最终采样点、或 ≥2 个采样点（长驻错位）；
// 飞入/过冲瞬态不报。字号类规则任一采样点可见即判。没 timeline 检静态 DOM。
//
// 例外通道：确实要越界的元素（如满幅背景图）加 data-lint-ignore 属性。
//
// 退出码：0 = 全过 · 1 = 有 FAIL · 2 = 只有 WARN
// ───────────────────────────────────────────────────────────────────
const fs = require('fs');
const path = require('path');
const os = require('os');

const CHROME = process.env.CHROME_BIN || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

const PRESETS = {
  '9x16': { w: 1080, h: 1920 },
  '16x9': { w: 1920, h: 1080 },
  '3x4':  { w: 1080, h: 1440 },
};

// puppeteer 定位：先本目录 node_modules，再 npx 缓存（同 render_cue_puppeteer.js）
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
  throw new Error('找不到 puppeteer-core / puppeteer（cd recipes && npm i puppeteer-core）');
}

// ── 参数解析 ──────────────────────────────────────────────────────
const argv = process.argv.slice(2);
let targets = [], preset = null, asJson = false;
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === '--preset') preset = argv[++i];
  else if (a === '--json') asJson = true;
  else if (a === '--all') {
    const dir = argv[++i];
    targets = fs.readdirSync(dir).filter(f => f.endsWith('.html') && !f.includes('spec_review'))
      .map(f => path.join(dir, f));
  } else targets.push(a);
}
if (!targets.length) {
  console.error('用法: node lint_layout.js <cue.html> [--preset 9x16|16x9|3x4] [--json] | --all <目录>');
  process.exit(2);
}
if (preset && !PRESETS[preset]) { console.error(`未知 preset: ${preset}`); process.exit(2); }

// ── 页面内检查逻辑（在浏览器里执行）──────────────────────────────
// 返回该采样点所有可见文字元素的度量；判定逻辑放 node 侧，方便维护
function collectTextMetrics() {
  const out = [];
  const walk = (el) => {
    for (const child of el.children) walk(child);
    if (el.hasAttribute('data-lint-ignore')) return;
    // 只看"自己直接持有文字"的元素，避免容器重复计
    const ownText = Array.from(el.childNodes)
      .filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
    if (!ownText) return;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return;
    // 沿祖先链算有效 opacity（GSAP 常把 opacity 打在容器上）
    let op = 1, node = el;
    while (node && node !== document.documentElement) {
      op *= parseFloat(getComputedStyle(node).opacity || '1');
      node = node.parentElement;
    }
    if (op < 0.05) return;
    // 横向量文字真实墨迹（Range）——满宽容器 + 居中文字不算贴边；
    // 纵向量元素行框——CJK 字体 bbox 预留的拉丁音标空间会让 Range 纵向虚高 ~0.2em
    const er = el.getBoundingClientRect();
    let rr = null;
    try {
      const range = document.createRange();
      const textNodes = Array.from(el.childNodes).filter(n => n.nodeType === 3 && n.textContent.trim());
      range.setStartBefore(textNodes[0]);
      range.setEndAfter(textNodes[textNodes.length - 1]);
      rr = range.getBoundingClientRect();
    } catch (e) {}
    if (!rr || rr.width === 0) rr = er;
    if (rr.width === 0 || er.height === 0) return;
    // 纯 emoji / 符号（无中英文字母数字）= 装饰元素，贴边是设计，跳过
    if (!/[A-Za-z0-9一-龥]/.test(ownText)) return;
    out.push({
      text: ownText.slice(0, 30),
      tag: el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).join('.') : ''),
      top: er.top, bottom: er.bottom, left: rr.left, right: rr.right,
      cx: rr.left + rr.width / 2,
      fontSize: parseFloat(cs.fontSize),
      textAlign: cs.textAlign,
      parentW: el.parentElement ? el.parentElement.getBoundingClientRect().width : 0,
    });
  };
  walk(document.body);
  return {
    metrics: out,
    scrollW: document.documentElement.scrollWidth,
    scrollH: document.documentElement.scrollHeight,
  };
}

// ── 判定规则（node 侧）────────────────────────────────────────────
// positional=true 的规则只在落定状态判定（见文件头注释）
function judge(presetKey, sample, issues, sampleIdx) {
  const { w: W, h: H } = PRESETS[presetKey];
  const add = (level, rule, m, detail, positional = true, mag = 999) =>
    issues.push({ level, rule, el: m ? m.tag : '', text: m ? m.text : '', detail, positional, sampleIdx, mag });

  if (sample.scrollW > W + 1 || sample.scrollH > H + 1)
    add('FAIL', 'canvas 溢出', null, `scroll ${sample.scrollW}×${sample.scrollH} > 画布 ${W}×${H}（会出滚动条/裁切）`);

  for (const m of sample.metrics) {
    if (presetKey === '9x16') {
      if (m.top < 192) add('FAIL', '顶部安全区', m, `文字 top=${m.top.toFixed(0)} < 192（刘海/状态栏切）`, true, 192 - m.top);
      if (m.bottom > 1632) add('FAIL', '底部安全区', m, `文字 bottom=${m.bottom.toFixed(0)} > 1632（自动字幕/商品卡盖）`, true, m.bottom - 1632);
      if (m.left < 78) add('FAIL', '左边距', m, `left=${m.left.toFixed(0)} < 80（全模板统一 80px 边距）`, true, 80 - m.left);
      if (m.right > W - 78) add('FAIL', '右边距', m, `right=${m.right.toFixed(0)} > ${W - 80}（文字宽应 ≤920）`, true, m.right - (W - 80));
      if (m.fontSize < 22) add('FAIL', '最小字号', m, `${m.fontSize}px < 22px（手机上不可读，CONVENTIONS §五）`, false);
      if (m.textAlign === 'center' && m.parentW >= W - 4 && Math.abs(m.cx - W / 2) > 10)
        add('WARN', '居中偏移', m, `声明居中但中心 x=${m.cx.toFixed(0)}，偏离画布中线 ${Math.abs(m.cx - W / 2).toFixed(0)}px`);
    }
    if (presetKey === '16x9') {
      const mx = W * 0.05, myTop = H * 0.05, myBottom = H * 0.88;
      if (m.top < myTop) add('WARN', '顶部边距', m, `top=${m.top.toFixed(0)} < 5%（${myTop.toFixed(0)}）`);
      if (m.bottom > myBottom) add('FAIL', '底部安全区', m, `bottom=${m.bottom.toFixed(0)} > 88%（进度条/平台字幕区）`, true, m.bottom - myBottom);
      if (m.left < mx || m.right > W - mx) add('WARN', '左右边距', m, `贴边（四边留 ~5%）`);
      if (m.right > W - 64 - 500 + 40 && m.bottom > H - 64 - 500 + 40 && m.right > W * 0.72 && m.bottom > H * 0.55)
        add('WARN', 'pip 小窗区', m, `文字落在右下 person-pip 默认区（CONVENTIONS §九），确认这个 cue 不缩小窗`);
      if (m.fontSize < 20) add('FAIL', '最小字号', m, `${m.fontSize}px < 20px`, false);
    }
    if (presetKey === '3x4') {
      if (m.bottom > H * (2 / 3)) add('FAIL', '底部留真人', m, `文字 bottom=${m.bottom.toFixed(0)} 进了底部 1/3（slidecast 三铁律：内容全顶部对齐）`, true, m.bottom - H * (2 / 3));
      if (m.fontSize < 22) add('FAIL', '最小字号', m, `${m.fontSize}px < 22px`, false);
      if (/^\d+\s*[\/·]\s*\d+$/.test(m.text) || /^(P|p|第)?\s*\d{1,2}\s*(页|\/)?$/.test(m.text) && m.top > H * 0.8)
        add('FAIL', '无页码', m, `疑似页码「${m.text}」（slidecast 三铁律：无页码）`, false);
    }
  }

  // 字号种数（同画面字号 > 6 种基本是层级失控）
  const sizes = [...new Set(sample.metrics.map(m => Math.round(m.fontSize)))].sort((a, b) => a - b);
  if (sizes.length > 6)
    add('WARN', '字号种数', null, `本画面出现 ${sizes.length} 种字号：${sizes.join('/')}px（层级失控，收敛到 token 阶梯）`, false);
}

// ── 主流程 ────────────────────────────────────────────────────────
(async () => {
  const puppeteer = loadPuppeteer();
  const browser = await puppeteer.launch({
    executablePath: CHROME, headless: 'new',
    args: ['--no-sandbox', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1'],
  });

  let anyFail = false, anyWarn = false;
  const report = [];

  for (const file of targets) {
    const abs = path.resolve(file);
    if (!fs.existsSync(abs)) { console.error(`✗ 文件不存在: ${file}`); anyFail = true; continue; }

    const page = await browser.newPage();
    // 阻止自动播放，走逐点 seek（同渲染脚本的约定）
    await page.evaluateOnNewDocument(() => { window.__hyperframes_runtime = true; });

    // 画幅：显式 > html 内声明推断
    let pk = preset;
    if (!pk) {
      const src = fs.readFileSync(abs, 'utf8');
      if (/width=1920/.test(src) || /width:\s*1920px/.test(src)) pk = '16x9';
      else if (/height=1440/.test(src) || /height:\s*1440px/.test(src)) pk = '3x4';
      else pk = '9x16';
    }
    const { w, h } = PRESETS[pk];
    await page.setViewport({ width: w, height: h });
    await page.goto('file://' + abs, { waitUntil: 'networkidle0', timeout: 30000 });
    await page.evaluate(() => document.fonts ? document.fonts.ready : null);

    const hasTl = await page.evaluate(() => !!(window.__timelines && window.__timelines.main));
    const samples = hasTl ? [0.45, 0.75, 0.98] : [null];
    const issues = [];
    for (let si = 0; si < samples.length; si++) {
      const prog = samples[si];
      if (prog !== null) {
        await page.evaluate(p => { const tl = window.__timelines.main; tl.pause(); tl.progress(p); }, prog);
        await new Promise(r => setTimeout(r, 120));
      }
      const sample = await page.evaluate(collectTextMetrics);
      judge(pk, sample, issues, si);
    }
    await page.close();

    // 聚合：同一 (rule, el, text) 跨采样点归一条。
    // positional 规则只在"落定"算数：出现在最终采样点、或 ≥2 个采样点；
    // 非 positional（字号/页码）任一采样点出现即报。
    const lastIdx = samples.length - 1;
    const groups = new Map();
    for (const i of issues) {
      const k = i.rule + '|' + i.el + '|' + i.text;
      if (!groups.has(k)) groups.set(k, { ...i, hits: new Set(), maxMag: 0 });
      const g = groups.get(k);
      g.hits.add(i.sampleIdx);
      g.maxMag = Math.max(g.maxMag, i.mag);
    }
    const uniq = [...groups.values()].filter(g =>
      !g.positional || g.hits.has(lastIdx) || (g.hits.size >= 2 && g.maxMag > 12));

    const fails = uniq.filter(i => i.level === 'FAIL');
    const warns = uniq.filter(i => i.level === 'WARN');
    if (fails.length) anyFail = true;
    if (warns.length) anyWarn = true;
    report.push({ file, preset: pk, hasTimeline: hasTl, fails, warns });

    if (!asJson) {
      console.log(`\n────────────────────────────────────────`);
      console.log(`  ${path.basename(file)}  [${pk}${hasTl ? ' · timeline 3 采样点' : ' · 静态'}]`);
      console.log(`────────────────────────────────────────`);
      if (!uniq.length) console.log('  ✅ ALL PASS');
      for (const i of fails) console.log(`  ✗ [${i.rule}] ${i.el} 「${i.text}」\n      ${i.detail}`);
      for (const i of warns) console.log(`  ⚠ [${i.rule}] ${i.el} 「${i.text}」\n      ${i.detail}`);
      if (fails.length) console.log(`  ❌ FAIL ${fails.length} 项（必修再进 spec review）`);
      else if (warns.length) console.log(`  ⚠ WARN ${warns.length} 项（spec review 里注明）`);
    }
  }

  await browser.close();
  if (asJson) console.log(JSON.stringify(report, null, 2));
  process.exit(anyFail ? 1 : anyWarn ? 2 : 0);
})().catch(e => { console.error('lint_layout 崩了:', e.message); process.exit(1); });
