// send.mjs — 승인된 크몽 답장 발송 (DOM 실입력)
// 이미 스킬이 사용자 승인을 받은 메시지만 발송한다. 스레드로 이동 → 메시지창에 실제 키입력
// (pressSequentially; paste/fill 금지 — 한글 mojibake 방지) → 전송 버튼 클릭 → 스크린샷 검증.
//
// 사용:  node "<skill>/scripts/send.mjs" <jobs.json> [--dry-run]
//   jobs.json = [{ "url": "https://kmong.com/inboxes?inbox_group_id=..&partner_id=..", "text": "..." }, ...]
//   --dry-run : 메시지창에 입력만 하고 전송하지 않음(스크린샷만) — 검증용.
//
// 전제: Chrome :9222(chrome-cdp-profile, 크몽 로그인). 발송은 되돌릴 수 없음 → 승인된 jobs만 넘길 것.

import { chromium } from 'playwright';
import { readFileSync } from 'node:fs';
import { spawn } from 'node:child_process';
import path from 'node:path';
import os from 'node:os';

const CDP = process.env.KMONG_CDP || 'http://localhost:9222';
const args = process.argv.slice(2);
const dryRun = args.includes('--dry-run');
const jobsPath = args.find(a => !a.startsWith('--'));
if (!jobsPath) { console.error('usage: send.mjs <jobs.json> [--dry-run]'); process.exit(2); }

let jobs;
try { jobs = JSON.parse(readFileSync(jobsPath, 'utf8')); }
catch (e) { console.error('jobs.json 읽기 실패:', e.message); process.exit(2); }
if (!Array.isArray(jobs) || jobs.length === 0) { console.error('jobs 비어있음'); process.exit(2); }

// CDP 전용 Chrome(chrome-cdp-profile, 9222) 이 안 떠 있을 때 backup 으로 자동 기동한다.
// 사용자의 평소 Chrome(Default 프로파일)은 별도 --user-data-dir 라 손대지 않는다.
async function launchCdpChromeMacos() {
  const chromeBin = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  const profileDir = path.join(os.homedir(), 'chrome-cdp-profile');
  try {
    const child = spawn(chromeBin, [`--remote-debugging-port=9222`, `--user-data-dir=${profileDir}`], {
      stdio: 'ignore', detached: true,
    });
    child.unref();
  } catch (e) {
    return { ok: false, msg: `CDP Chrome 기동 실패: ${e.message}` };
  }
  for (let i = 0; i < 15; i++) {
    await new Promise(r => setTimeout(r, 1000));
    try { await (await fetch(`${CDP}/json/version`)).json(); return { ok: true, msg: 'CDP Chrome 자동 기동 성공' }; }
    catch {}
  }
  return { ok: false, msg: 'CDP Chrome 을 띄웠지만 15초 내 9222 응답 없음' };
}

let browser;
try {
  browser = await chromium.connectOverCDP(CDP);
} catch (e) {
  if (process.platform === 'darwin' && CDP === 'http://localhost:9222') {
    console.error('⏳ CDP 9222 미응답 — CDP 전용 Chrome(chrome-cdp-profile) 자동 기동 시도 중...');
    const { ok, msg } = await launchCdpChromeMacos();
    console.error((ok ? '✅ ' : '❌ ') + msg);
    if (!ok) { console.error('자동 기동 실패 — Chrome을 직접 띄워야 함'); process.exit(1); }
    try {
      browser = await chromium.connectOverCDP(CDP);
    } catch (e2) {
      console.error(`자동 기동 후에도 CDP 연결 실패 (${e2.message})`);
      process.exit(1);
    }
  } else {
    console.error(`Chrome :9222 연결 실패 (${e.message})`);
    process.exit(1);
  }
}
const ctx = browser.contexts()[0];
const shotDir = process.env.KMONG_SHOT_DIR || os.tmpdir();
const results = [];

for (const [i, job] of jobs.entries()) {
  const page = await ctx.newPage();
  const r = { url: job.url, name: '', sent: false, dryRun, shot: null, error: null };
  try {
    await page.goto(job.url, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(2000);

    const box = page.getByPlaceholder(/메시지를 입력하세요/).first();
    await box.waitFor({ state: 'visible', timeout: 10000 });
    await box.click();
    await box.pressSequentially(job.text, { delay: 8 }); // 실제 키이벤트 (Enter=줄바꿈이라 중간 전송 안 됨)
    await page.waitForTimeout(400);

    const shot = path.join(shotDir, `kmong-send-${i}-${dryRun ? 'dryrun' : 'sent'}.png`);
    await page.screenshot({ path: shot });
    r.shot = shot;

    if (!dryRun) {
      const sendBtn = page.getByRole('button', { name: '전송' }).first();
      await sendBtn.click();
      await page.waitForTimeout(1500);
      // 발송 후 입력창이 비었는지로 성공 판정
      const leftover = await box.inputValue().catch(() => '');
      r.sent = leftover.trim().length === 0;
      const shot2 = path.join(shotDir, `kmong-send-${i}-after.png`);
      await page.screenshot({ path: shot2 });
      r.shotAfter = shot2;
    }
  } catch (e) {
    r.error = e.message;
  } finally {
    await page.close();
    results.push(r);
  }
}

console.log(JSON.stringify({ ok: true, dryRun, results }, null, 1));
await browser.close();
