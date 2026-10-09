// Records the 62 s auto-pitch of design/glance-app-mockup.html to design/glance-pitch-62s.mp4.
// One-off setup (outside the repo):  mkdir -p /tmp/glance-rec && cd /tmp/glance-rec && npm init -y && npm i playwright@1.50.1
// Run:  node /path/to/repo/design/record-pitch.mjs        (needs Google Chrome and ffmpeg on PATH)
// The page's ?rec=1 mode hides the toolbar and shows black before the pitch starts and after it ends;
// those black segments are used to trim and to correct headless capture speed so cues match design/pitch-voiceover.md.
import { chromium } from '/tmp/glance-rec/node_modules/playwright/index.mjs';
import { execSync } from 'node:child_process';
import { rename, rm, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const here = path.dirname(fileURLToPath(import.meta.url));
const url = 'file://' + path.join(here, 'glance-app-mockup.html') + '?rec=1';
const out = path.join(here, 'glance-pitch-62s.mp4'), tmp = '/tmp/glance-rec/out', PITCH = 62;
await rm(tmp, { recursive: true, force: true }); await mkdir(tmp, { recursive: true });
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, recordVideo: { dir: tmp, size: { width: 1920, height: 1080 } } });
const page = await ctx.newPage();
await page.goto(url, { waitUntil: 'load' });
await page.evaluate(() => document.fonts.ready);
await page.waitForTimeout(1500);
await page.evaluate(() => document.getElementById('play').click());
await page.waitForTimeout((PITCH + 3) * 1000);
const video = page.video(); await ctx.close(); const raw = await video.path(); await browser.close();
await rename(raw, tmp + '/raw.webm');
const log = execSync(`ffmpeg -hide_banner -i ${tmp}/raw.webm -vf blackdetect=d=0.3:pix_th=0.10 -an -f null - 2>&1`).toString();
const segs = [...log.matchAll(/black_start:([\d.]+) black_end:([\d.]+)/g)].map(m => [+m[1], +m[2]]);
const start = segs[0][1], end = segs[segs.length - 1][0], span = end - start;
console.log(`pitch captured from ${start}s to ${end}s (${span.toFixed(2)}s for ${PITCH}s) -> speed factor ${(PITCH / span).toFixed(4)}`);
execSync(`ffmpeg -hide_banner -loglevel error -y -ss ${start} -t ${span} -i ${tmp}/raw.webm -vf "setpts=PTS*${PITCH / span},fps=25,format=yuv420p" -c:v libx264 -preset slow -crf 18 -movflags +faststart "${out}"`);
console.log('wrote', out);
