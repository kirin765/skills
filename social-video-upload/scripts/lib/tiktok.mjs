import path from 'node:path';
import os from 'node:os';

const SHOTS = process.env.SOCIAL_UPLOAD_SHOTS || path.join(os.homedir(), '.social-upload', 'shots');
const UPLOAD_URL = 'https://www.tiktok.com/tiktokstudio/upload';
const log = (m) => process.stdout.write(`  [tiktok] ${m}\n`);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function shot(page, name) {
  try {
    const fs = await import('node:fs');
    fs.mkdirSync(SHOTS, { recursive: true });
    await page.screenshot({ path: path.join(SHOTS, `tiktok_${name}.png`) });
  } catch {}
}

export async function isLoggedIn(page) {
  await page.goto('https://www.tiktok.com/tiktokstudio', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(3000);
  return !/\/login/.test(page.url());
}

export async function whoami(ctx) {
  const page = ctx.pages()[0] || (await ctx.newPage());
  await page.goto('https://www.tiktok.com/profile', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(4000);
  let handle = '';
  try {
    handle = await page
      .locator('[data-e2e="user-subtitle"], [data-e2e="user-title"]')
      .first()
      .innerText({ timeout: 8000 });
  } catch {}
  return (handle || '').trim() || null;
}

// First-run TikTok Studio shows a react-joyride tour whose overlay intercepts all
// clicks. Close it (skip) or rip the portal out of the DOM.
async function dismissTours(page) {
  for (let i = 0; i < 4; i++) {
    const portal = await page.locator('#react-joyride-portal').count();
    if (!portal) return;
    const skip = page
      .locator(
        '.react-joyride__tooltip button:has-text("Skip"), ' +
          '.react-joyride__tooltip button:has-text("Got it"), ' +
          '[data-test-id="button-skip"], [aria-label="Close"]',
      )
      .first();
    if (await skip.count()) {
      try {
        await skip.click({ timeout: 2000 });
      } catch {}
    }
    await page.evaluate(() => {
      document
        .querySelectorAll('#react-joyride-portal, .react-joyride__overlay')
        .forEach((el) => el.remove());
    });
    await page.waitForTimeout(600);
  }
}

async function setCaption(page, caption) {
  // TikTok caption is a Draft.js contenteditable. Focus, clear, insert.
  const editor = page.locator('div[contenteditable="true"]').first();
  await editor.waitFor({ state: 'visible', timeout: 60000 });
  await editor.click();
  await page.keyboard.press('Control+A');
  await page.keyboard.press('Backspace');
  await page.keyboard.insertText(caption);
  await page.waitForTimeout(1500);
}

export async function postTikTok(ctx, { videoPath, caption, autoPost = false, privacy = 'public' }) {
  const page = ctx.pages()[0] || (await ctx.newPage());
  if (!(await isLoggedIn(page))) throw new Error('tiktok not logged in — run: login');

  await page.goto(UPLOAD_URL, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(4000);

  const fileInput = page.locator('input[type="file"]').first();
  await fileInput.waitFor({ state: 'attached', timeout: 60000 });
  await fileInput.setInputFiles(videoPath);
  log('file attached, waiting for processing…');
  await shot(page, '1_attached');

  // Editor appearing means the video finished its first processing pass.
  await page.locator('div[contenteditable="true"]').first().waitFor({ state: 'visible', timeout: 120000 });
  await page.waitForTimeout(2000);
  await dismissTours(page);

  await setCaption(page, caption);
  await shot(page, '2_caption');
  // privacy: TikTok defaults to Everyone/Public for most accounts; only 'public' supported.

  if (!autoPost) {
    return { posted: false, url: page.url(), note: 'caption set — click Post manually 또는 --auto로 재실행' };
  }

  const postBtn = page.getByRole('button', { name: /^Post$/ }).first();
  await postBtn.waitFor({ state: 'visible', timeout: 180000 });
  for (let i = 0; i < 60; i++) {
    if (await postBtn.isEnabled()) break;
    await page.waitForTimeout(3000);
  }
  // Wait for music + content checks BEFORE posting. Posting mid-check forces the
  // video to "Only me / under review" and may never flip public; waiting lets the
  // chosen privacy stick. Own content passes, but content-check-lite can take ~10 min.
  log('waiting for copyright/content checks to finish…');
  for (let i = 0; i < 156; i++) {
    const checking = await page.locator('text=/Checking in progress/i').count();
    if (!checking) break;
    await page.waitForTimeout(5000);
  }
  await dismissTours(page);
  await shot(page, '3_ready');
  await postBtn.click();
  log('clicked Post…');

  // Fallback: a "Continue to post? check incomplete" modal may still appear.
  const postNow = page.getByRole('button', { name: /^Post now$/ }).first();
  try {
    await postNow.waitFor({ state: 'visible', timeout: 6000 });
    await postNow.click();
    log('checks not done — confirmed "Post now" (may post as under-review)');
  } catch {}
  await page.waitForTimeout(1000);
  await shot(page, '4_confirm');

  // Real success = redirect to content manager OR explicit success toast.
  let ok = false;
  for (let i = 0; i < 40; i++) {
    await page.waitForTimeout(2000);
    if (/\/tiktokstudio\/content/i.test(page.url())) {
      ok = true;
      break;
    }
    const toast = await page
      .locator('text=/successfully|Manage your posts|게시되었|been posted|View profile/i')
      .count();
    if (toast > 0) {
      ok = true;
      break;
    }
  }
  await shot(page, '5_after');
  return { posted: ok, url: page.url(), note: ok ? '' : `POST UNCONFIRMED — check ${SHOTS}/tiktok_5_after.png` };
}

// TikTok login waits until the page leaves /login and the studio loads.
export async function loginTikTok(ctx) {
  const page = ctx.pages()[0] || (await ctx.newPage());
  await page.goto('https://www.tiktok.com/login', { waitUntil: 'domcontentloaded' });
  log('Log into TikTok in the opened window. Waiting up to 5 min…');
  const deadline = Date.now() + 300000;
  while (Date.now() < deadline) {
    await page.waitForTimeout(4000);
    if (!/\/login/.test(page.url())) {
      await page.waitForTimeout(3000);
      if (await isLoggedIn(page)) break;
    }
  }
  return isLoggedIn(page);
}
