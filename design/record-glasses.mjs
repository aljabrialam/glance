// Captures the Meta Display glasses concept from design/glance-product-film.html for the README:
//   design/glance-glasses-concept.gif          the glasses scenes (see → find → quote → block → confirm → paid), sped up
//   design/thumbs/glasses/NN-<scene>.png        one still per scene, 2x
// Setup (outside the repo, shared with record-pitch.mjs):  mkdir -p /tmp/glance-rec && cd /tmp/glance-rec && npm init -y && npm i playwright@1.50.1
// Run:  node design/record-glasses.mjs        (needs Google Chrome and ffmpeg on PATH)
import { chromium } from '/tmp/glance-rec/node_modules/playwright/index.mjs';
import { execSync } from 'node:child_process';
import { mkdir, rename, rm } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const film = 'file://' + path.join(here, 'glance-product-film.html');
const tmp = '/tmp/glance-rec/glasses';
const gif = path.join(here, 'glance-glasses-concept.gif');
const stillsDir = path.join(here, 'thumbs', 'glasses');
// Only the 16:9 stage: hide the page chrome so the stage fills the viewport exactly.
const STAGE_ONLY = '.wrap{max-width:none;padding:0;gap:0}h1,.note,.bar,.scenes{display:none!important}.stage{border:0;border-radius:0}';
const FROM = 5, TO = 56;                 // film seconds: glasses scenes start at "See it, say it", end after "Paid"
const SPEED = 1.5, FPS = 10, WIDTH = 800; // GIF pacing and size
const STILLS = [                          // film time chosen inside each scene's "late" state, when the HUD has fully revealed
  ['01-see', 10.5, 'Look at it, say the most you will pay'],
  ['02-find', 24.5, 'The agent searches merchants via Reap'],
  ['03-quote', 31.5, 'The real total, checked against your limit'],
  ['04-block', 39.5, 'Over the limit: checkout blocked, nothing opened'],
  ['05-confirm', 47, 'Pinch to send it to your phone; approve on Reap\u2019s page'],
  ['06-paid', 54.5, 'Paid: the amount actually charged, from the USDC vault'],
];

await rm(tmp, { recursive: true, force: true }); await mkdir(tmp, { recursive: true }); await mkdir(stillsDir, { recursive: true });
const browser = await chromium.launch({ channel: 'chrome', headless: true });

// 1. stills, deterministic: ?t=<s>&pause, wait for fonts and the reveal transitions, element screenshot at 2x
const sctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2 });
const sp = await sctx.newPage();
for (const [name, t, caption] of STILLS) {
  await sp.goto(`${film}?t=${t}&pause`, { waitUntil: 'load' });
  await sp.addStyleTag({ content: STAGE_ONLY });
  await sp.evaluate(() => document.fonts.ready);
  await sp.waitForTimeout(1600);
  await sp.locator('#stage').screenshot({ path: path.join(stillsDir, `${name}.png`) });
  console.log(`still ${name} @${t}s — ${caption}`);
}
await sctx.close();

// 2. video of the glasses scenes playing in real time, then GIF
const vctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, recordVideo: { dir: tmp, size: { width: 1280, height: 720 } } });
const vp = await vctx.newPage();
await vp.goto(`${film}?t=${FROM}&pause`, { waitUntil: 'load' });
await vp.addStyleTag({ content: STAGE_ONLY });
await vp.evaluate(() => document.fonts.ready);
await vp.waitForTimeout(1200);
const wall0 = Date.now();
await vp.evaluate(() => document.getElementById('play').click());             // starts at FROM
await vp.waitForFunction((to) => +document.getElementById('seek').value >= to, TO, { timeout: (TO - FROM + 20) * 1000, polling: 100 });
const wall = (Date.now() - wall0) / 1000;                                       // seconds of wall clock for (TO - FROM) film seconds
await vp.evaluate(() => document.getElementById('play').click());             // pause
await vp.waitForTimeout(400);
const video = vp.video(); await vctx.close(); const raw = await video.path(); await browser.close();
await rename(raw, tmp + '/raw.webm');

// The recording started ~1.2 s + load before play was clicked; find the exact start by the first frame change is overkill —
// trim with the measured offsets instead: everything before the click is the paused FROM frame, which is also the GIF's first frame.
const dur = +execSync(`ffprobe -v error -show_entries format=duration -of csv=p=0 ${tmp}/raw.webm`).toString().trim();
const lead = Math.max(0, dur - wall - 0.4);                                     // recording time before the click
const filmSpan = TO - FROM, playback = wall;                                    // headless rAF may not run at real time; normalise to film time
const pts = (filmSpan / playback) / SPEED;                                      // setpts factor: real → film time, then speed up
console.log(`raw ${dur.toFixed(1)}s, lead ${lead.toFixed(1)}s, ${filmSpan}s of film took ${playback.toFixed(1)}s → setpts ${pts.toFixed(4)}`);
const vf = `setpts=PTS*${pts.toFixed(5)},fps=${FPS},scale=${WIDTH}:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=160:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle`;
execSync(`ffmpeg -hide_banner -loglevel error -y -ss ${lead.toFixed(2)} -t ${playback.toFixed(2)} -i ${tmp}/raw.webm -filter_complex "${vf}" -loop 0 "${gif}"`);
console.log('wrote', gif, execSync(`du -h "${gif}" | cut -f1`).toString().trim());
