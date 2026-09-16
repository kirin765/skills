// send.mjs — 승인된 크몽 답장 발송 (DOM 실입력)
// 이미 스킬이 사용자 승인을 받은 메시지만 발송한다. 스레드로 이동 → 메시지창에 실제 키입력
// (pressSequentially; paste/fill 금지 — 한글 mojibake 방지) → 전송 버튼 클릭 → 스크린샷 검증.
//
// 사용:  node "<skill>/scripts/send.mjs" <jobs.json> [--dry-run]
//   jobs.json = [{ "url": "https://kmong.com/inboxes?inbox_group_id=..&partner_id=..", "text": "..." }, ...]
//   --dry-run : 메시지창에 입력만 하고 전송하지 않음(스크린샷만) — 검증용.
//
// 전제: Chrome :9222(chrome-cdp-profile, 크몽 로그인). 발송은 되돌릴 수 없음 → 승인된 jobs만 넘길 것.

import { readFileSync } from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { connectCdp } from './cdp.mjs';

const args = process.argv.slice(2);
const dryRun = args.includes('--dry-run');
const jobsPath = args.find(a => !a.startsWith('--'));
if (!jobsPath) { console.error('usage: send.mjs <jobs.json> [--dry-run]'); process.exit(2); }

let jobs;
try { jobs = JSON.parse(readFileSync(jobsPath, 'utf8')); }
catch (e) { console.error('jobs.json 읽기 실패:', e.message); process.exit(2); }
if (!Array.isArray(jobs) || jobs.length === 0) { console.error('jobs 비어있음'); process.exit(2); }

let browser;
try {
  browser = await connectCdp({ log: m => console.error(m) });
} catch (e) {
  console.error(e.message);
  process.exit(1);
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

    // 온보딩 안내 등 모달이 입력창을 가로막는 경우 닫기
    const closeBtn = page.locator('[data-testid="close-button"]').first();
    if (await closeBtn.isVisible().catch(() => false)) {
      await closeBtn.click().catch(() => {});
      await page.waitForTimeout(500);
    }

    const box = page.getByPlaceholder(/메시지를 입력/).first();
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
