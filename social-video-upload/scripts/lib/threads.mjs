const log = (m) => process.stdout.write(`  [threads-video] ${m}\n`);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function activeHandle(page) {
  // Threads profile link is /@handle; grab the nav avatar link.
  return page.evaluate(() => {
    const a = [...document.querySelectorAll('a[role="link"]')].find(
      (x) => x.querySelector('img') && /^\/@[\w.]+$/.test(x.getAttribute('href') || ''),
    );
    return a ? a.getAttribute('href').replace(/^\/@?/, '') : null;
  });
}

// Same caveat as IG — logged-out Threads shows a login form at root. Probe state.
export async function isLoggedIn(page) {
  if (/\/login/.test(page.url())) return false;
  if (await page.$('input[autocomplete="username"], input[name="username"]').catch(() => null)) return false;
  return !!(await activeHandle(page));
}

export async function whoami(ctx) {
  const page = await ctx.newPage();
  try {
    await page.goto('https://www.threads.com/', { waitUntil: 'domcontentloaded' });
    await sleep(2500);
    if (/\/login/.test(page.url())) return null;
    return await activeHandle(page);
  } finally {
    await page.close().catch(() => {});
  }
}

// Tuned for the docked Threads composer (not the old role="dialog" modal).
export async function postThreadsVideo(ctx, { videoPath, caption, autoPost = false }) {
  for (const p of ctx.pages()) {
    if (/threads\.(net|com)/.test(p.url())) await p.close().catch(() => null);
  }
  const page = await ctx.newPage();
  await page.goto('https://www.threads.com/', { waitUntil: 'domcontentloaded' });
  await Promise.race([page.bringToFront(), sleep(2000)]);
  await sleep(2500);
  if (/\/login/.test(page.url())) throw new Error('threads not logged in — run: login');

  // Open composer (bilingual; docked popup or modal)
  let opened = false;
  for (const sel of [
    'div[role="button"]:has-text("New thread")',
    'div[role="button"]:has-text("만들기")',
    'div[role="button"]:has-text("Create")',
    'div[role="button"]:has-text("What\'s new?")',
    'div[role="button"]:has-text("새로운 소식이 있나요?")',
  ]) {
    const el = await page.$(sel).catch(() => null);
    if (el) {
      await el.click().catch(() => null);
      opened = true;
      break;
    }
  }
  if (!opened) throw new Error('composer trigger not found');
  log('composer opened');

  // Caption editable — last visible contenteditable textbox
  const editSel = '[contenteditable="true"]';
  await page.waitForSelector(editSel, { timeout: 15000, state: 'visible' });
  const editables = await page.$$(editSel);
  const editable = editables[editables.length - 1];
  await editable.click();
  await page.keyboard.insertText(caption);
  log('caption inserted');
  await sleep(800);

  // Upload video — hidden file input within composer
  const fileInput = await page.$('input[type="file"]');
  if (!fileInput) throw new Error('file input not found');
  await fileInput.setInputFiles(videoPath);
  log('video uploaded — waiting for processing…');
  await sleep(8000);

  if (!autoPost) {
    return { posted: false, url: page.url(), note: 'composer prepared — click Post manually 또는 --auto로 재실행' };
  }

  // Click the composer Post button (enabled once media is ready). Try a few times.
  let posted = false;
  for (let i = 0; i < 6 && !posted; i++) {
    const candidates = await page.$$(
      'div[role="button"]:has-text("Post"), div[role="button"]:has-text("게시"), button:has-text("Post"), button:has-text("게시")',
    );
    for (const c of candidates.reverse()) {
      const txt = (await c.innerText().catch(() => '')).trim();
      if (/^(Post|게시)$/.test(txt)) {
        const disabled = await c.getAttribute('aria-disabled').catch(() => null);
        if (disabled === 'true') continue;
        await c.click().catch(() => null);
        posted = true;
        break;
      }
    }
    if (!posted) await sleep(2500);
  }
  if (!posted) throw new Error('Post button not found/enabled');
  await sleep(6000);
  return { posted: true, url: page.url() };
}
