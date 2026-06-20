import fs from 'node:fs';

const log = (m) => process.stdout.write(`  [ig-reels] ${m}\n`);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Diagnostic bundle: screenshot + DOM html + url. The path is announced so a flow
// break can be root-caused after the fact.
async function dumpFailure(page, tag = 'fail') {
  const dir = `/tmp/ig-fail-${tag}-${Date.now()}`;
  try {
    fs.mkdirSync(dir, { recursive: true });
    await page.screenshot({ path: `${dir}/screen.png`, fullPage: false }).catch(() => {});
    fs.writeFileSync(`${dir}/dom.html`, await page.content().catch(() => ''));
    fs.writeFileSync(`${dir}/url.txt`, page.url());
    log(`DIAG saved → ${dir}`);
  } catch (e) {
    log(`DIAG dump failed: ${e.message}`);
  }
  return dir;
}

// IG interrupts with interstitial modals (save login info, notifications, terms)
// that steal the overlay and stop the composer's file input from resolving.
async function dismissInterstitials(page) {
  const labels = [
    'Not Now', '나중에 하기', '나중에', 'Dismiss', '닫기', 'Cancel', '취소',
    'Save Info', 'Turn On', 'OK', '확인',
  ];
  for (const label of labels) {
    const btn = page.getByRole('button', { name: label, exact: true }).first();
    if (await btn.count().catch(() => 0)) {
      await btn.click({ timeout: 1500 }).catch(() => {});
      await sleep(500);
    }
  }
}

// The active account is the profile nav link wrapping the avatar <img>.
function activeHandle(page) {
  return page.evaluate(() => {
    const a = [...document.querySelectorAll('a[role="link"]')].find(
      (x) => x.querySelector('img') && /^\/[\w.]+\/$/.test(x.getAttribute('href') || ''),
    );
    return a ? a.getAttribute('href').replace(/\//g, '') : null;
  });
}

async function assertAccount(page, handle) {
  const active = await activeHandle(page);
  if (active === handle) {
    log(`account verified: @${handle}`);
    return;
  }
  throw new Error(
    `IG account mismatch — expected @${handle}, got @${active || '(none)'}. ` +
      `This profile is logged into the wrong account.`,
  );
}

// Logged-out IG serves a login form at the root URL (no /accounts/login redirect),
// so URL alone can't tell login state — probe for the form / the profile nav link.
export async function isLoggedIn(page) {
  if (/\/accounts\/login/.test(page.url())) return false;
  if (await page.$('input[name="username"]').catch(() => null)) return false;
  return !!(await activeHandle(page));
}

export async function whoami(ctx) {
  const page = await ctx.newPage();
  try {
    await page.goto('https://www.instagram.com/', { waitUntil: 'domcontentloaded' });
    await sleep(2500);
    if (/\/accounts\/login/.test(page.url())) return null;
    return await activeHandle(page);
  } finally {
    await page.close().catch(() => {});
  }
}

export async function publishReel(ctx, { videoPath, caption, expectedAccount = '', autoPost = false }) {
  for (const p of ctx.pages()) {
    if (/^https:\/\/www\.instagram\.com\/(?!static_)/.test(p.url())) await p.close().catch(() => null);
  }
  const page = await ctx.newPage();
  await page.goto('https://www.instagram.com/', { waitUntil: 'domcontentloaded' });
  await Promise.race([page.bringToFront(), sleep(2000)]);
  await sleep(2500);
  if (/\/accounts\/login/.test(page.url())) throw new Error('instagram not logged in — run: login');

  if (expectedAccount) await assertAccount(page, expectedAccount);

  // Open composer and reach the file input. IG flakes here (interstitial modals,
  // slow composer load), so retry the whole open→file-input sequence before failing.
  const FILE_SEL =
    'div[role="dialog"] input[type="file"], input[type="file"][accept*="video"], input[type="file"][accept*="image"]';
  let fileInput = null;
  for (let attempt = 1; attempt <= 3 && !fileInput; attempt++) {
    await dismissInterstitials(page);

    log(`clicking Create / 새로운 게시물 (attempt ${attempt})`);
    const createSvg = await page.$(
      'svg[aria-label="새로운 게시물"], svg[aria-label="New post"], svg[aria-label="Create"], svg[aria-label="만들기"]',
    );
    if (!createSvg) {
      if (attempt === 3) {
        const dir = await dumpFailure(page, 'no-create-svg');
        throw new Error(`Create SVG not found (diag: ${dir})`);
      }
      await sleep(2000);
      continue;
    }
    await createSvg.evaluate((s) => (s.closest('a,div[role="button"],button') || s).click());

    // Create menu may show a submenu (Post / Live | 게시물 / 라이브 방송). Pick Post.
    await sleep(1500);
    for (const label of ['Post', '게시물']) {
      const item = page.getByText(label, { exact: true }).first();
      if (await item.count().catch(() => 0)) {
        log(`submenu present — choosing ${label}`);
        await item.click().catch(() => {});
        await sleep(1200);
        break;
      }
    }

    fileInput = await page
      .waitForSelector(FILE_SEL, { timeout: 15000, state: 'attached' })
      .catch(() => null);

    if (!fileInput) {
      const dir = await dumpFailure(page, `attempt${attempt}`);
      log(`file input not found — recovering (diag: ${dir})`);
      await page.keyboard.press('Escape').catch(() => {});
      await sleep(1500);
    }
  }

  if (!fileInput) {
    const dir = await dumpFailure(page, 'final');
    throw new Error(`composer file input never appeared after 3 attempts (diag: ${dir})`);
  }

  log('uploading video…');
  await fileInput.setInputFiles(videoPath);

  // A video may pop a "동영상이 릴스로 공유됩니다" notice with 확인/OK.
  await sleep(2500);
  const okNotice = await page
    .$('div[role="dialog"] button:has-text("확인"), div[role="dialog"] [role="button"]:has-text("확인"), div[role="dialog"] button:has-text("OK")')
    .catch(() => null);
  if (okNotice) {
    log('dismissing reel notice (확인)');
    await okNotice.click().catch(() => {});
    await sleep(1500);
  }

  // Adaptive: click 다음/Next until the caption editable appears (video needs processing time).
  const captionSel = 'div[role="dialog"] [contenteditable="true"]';
  let captionEl = null;
  for (let i = 0; i < 8; i++) {
    captionEl = await page.$(captionSel);
    if (captionEl) break;
    const nextBtn = await page
      .$('div[role="dialog"] [role="button"]:has-text("다음"), div[role="dialog"] button:has-text("다음"), div[role="dialog"] [role="button"]:has-text("Next"), div[role="dialog"] button:has-text("Next")')
      .catch(() => null);
    if (nextBtn) {
      log(`step ${i + 1}: 다음`);
      await nextBtn.click().catch(() => {});
      await sleep(2500);
    } else {
      log(`step ${i + 1}: waiting for processing / next…`);
      await sleep(3000);
    }
  }
  if (!captionEl) throw new Error('caption editable never appeared — video composer flow changed');

  log('inserting caption…');
  await captionEl.click();
  await page.keyboard.insertText(caption);
  await sleep(1200);

  if (!autoPost) {
    return { posted: false, url: page.url(), note: '공유 직전 — Chrome에서 직접 [공유] 클릭하거나 --auto로 재실행' };
  }

  log('clicking 공유…');
  const shareBtn = await page
    .$('div[role="dialog"] [role="button"]:has-text("공유"), div[role="dialog"] button:has-text("공유"), div[role="dialog"] [role="button"]:has-text("Share")')
    .catch(() => null);
  if (!shareBtn) throw new Error('공유 button not found');
  await shareBtn.click();
  await sleep(12000);
  return { posted: true, url: page.url() };
}
