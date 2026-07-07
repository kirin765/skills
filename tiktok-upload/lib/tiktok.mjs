import { homedir } from 'node:os'
import { join } from 'node:path'
import { mkdirSync } from 'node:fs'
import { chromium } from 'playwright'

const UPLOAD_URL = 'https://www.tiktok.com/tiktokstudio/upload'

// Per-account persistent Chromium profile. Log in ONCE (login.mjs), then
// upload.mjs drives the same profile unattended. No dependency on the user's
// own Chrome or port 9222.
export function profileDir(account) {
  if (!account) throw new Error('account required')
  return join(homedir(), '.tiktok-upload', account)
}

export async function openContext(account, { headless = false } = {}) {
  const dir = profileDir(account)
  mkdirSync(dir, { recursive: true })
  return chromium.launchPersistentContext(dir, {
    headless,
    viewport: { width: 1280, height: 900 },
    args: ['--disable-blink-features=AutomationControlled'],
  })
}

export async function isLoggedIn(context) {
  const cookies = await context.cookies('https://www.tiktok.com')
  return cookies.some((c) => c.name === 'sessionid' && c.value)
}

const CAPTION_SELECTORS = [
  'div[contenteditable="true"]',
  '.public-DraftEditor-content',
  '.notranslate[contenteditable="true"]',
]
const POST_SELECTORS = [
  'button[data-e2e="post_video_button"]',
  'button:has-text("게시")',
  'button:has-text("Post")',
]

async function firstVisible(page, selectors, timeout = 45000) {
  const deadline = Date.now() + timeout
  while (Date.now() < deadline) {
    for (const sel of selectors) {
      const loc = page.locator(sel).first()
      if (await loc.count().catch(() => 0)) {
        if (await loc.isVisible().catch(() => false)) return loc
      }
    }
    await page.waitForTimeout(500)
  }
  throw new Error(`none visible: ${selectors.join(' | ')}`)
}

// A fresh profile triggers TikTok's react-joyride onboarding tour, whose
// overlay intercepts pointer events and blocks every click. Skip it (proper
// React teardown) then strip any residual overlay/spotlight nodes.
async function dismissTour(page, log) {
  if (!(await page.locator('#react-joyride-portal').count().catch(() => 0))) return
  const skipButtons = [
    '[data-test-id="button-skip"]',
    '[data-test-id="button-close"]',
    '#react-joyride-portal button[aria-label="Skip"]',
    '#react-joyride-portal button:has-text("Skip")',
    '#react-joyride-portal button:has-text("건너뛰기")',
    '#react-joyride-portal button:has-text("닫기")',
  ]
  for (const sel of skipButtons) {
    const b = page.locator(sel).first()
    if ((await b.count().catch(() => 0)) && (await b.isVisible().catch(() => false))) {
      await b.click().catch(() => {})
      await page.waitForTimeout(400)
      break
    }
  }
  await page
    .evaluate(() => {
      document
        .querySelectorAll('#react-joyride-portal, .react-joyride__overlay, .react-joyride__spotlight')
        .forEach((el) => el.remove())
    })
    .catch(() => {})
  log('dismissed onboarding tour')
}

// Click the caption editor resiliently — onboarding overlays (joyride, spotlight)
// intermittently intercept the click on fresh profiles. Retry with a hard strip
// + force-click before giving up.
async function focusEditor(page, editor) {
  try {
    await editor.click({ timeout: 8000 })
    return
  } catch {
    await dismissTour(page, () => {})
    await page
      .evaluate(() =>
        document
          .querySelectorAll(
            '#react-joyride-portal, .react-joyride__overlay, .react-joyride__spotlight, [data-test-id="overlay"]'
          )
          .forEach((el) => el.remove())
      )
      .catch(() => {})
    await editor.click({ force: true })
  }
}

// Separate coachmark tooltips ("Got it" / 확인) can also overlay controls.
async function dismissCoachmarks(page) {
  for (const sel of ['button:has-text("Got it")', 'button:has-text("확인")']) {
    const b = page.locator(sel).first()
    if ((await b.count().catch(() => 0)) && (await b.isVisible().catch(() => false))) {
      await b.click().catch(() => {})
      await page.waitForTimeout(300)
    }
  }
}

// AI-label & visibility controls live behind a collapsed "Show more" panel that
// renders with variable timing. Poll until the wanted control appears, clicking
// "Show more" whenever it's visible. Returns true once the target is visible.
async function revealControl(page, target, timeout = 15000) {
  const deadline = Date.now() + timeout
  while (Date.now() < deadline) {
    if (
      (await target.count().catch(() => 0)) &&
      (await target.first().isVisible().catch(() => false))
    ) {
      return true
    }
    for (const sel of ['button:has-text("Show more")', 'button:has-text("더 보기")']) {
      const b = page.locator(sel).first()
      if ((await b.count().catch(() => 0)) && (await b.isVisible().catch(() => false))) {
        await b.click().catch(() => {})
        await page.waitForTimeout(700)
        break
      }
    }
    await page.waitForTimeout(600)
  }
  return false
}

// Turn ON the "AI-generated content" disclosure. Idempotent — the switch state
// lives on a child [aria-checked] div (the <input role=switch> is aria-hidden),
// so we read that and only click when it's off.
async function enableAiLabel(page, log) {
  await dismissCoachmarks(page)
  const container = page.locator('[data-e2e="aigc_container"]').first()
  if (!(await revealControl(page, container))) {
    throw new Error('AI-label control not found — verify selectors with --dry-run')
  }
  const readState = () =>
    container.locator('[aria-checked]').first().getAttribute('aria-checked').catch(() => null)
  if ((await readState()) === 'true') {
    log('AI-label already ON')
    return
  }
  const sw = container.locator('.Switch__root, [data-layout="switch-root"]').first()
  await sw.click()
  await page.waitForTimeout(600)
  if ((await readState()) !== 'true') throw new Error('AI-label toggle did not switch ON')
  log('AI-label set ON')
}

// Select who can watch. The trigger is a role=combobox button whose inner text
// is the current value (Everyone/Friends/Only you) — there is no separate label.
const VISIBILITY_OPTION = {
  public: 'Everyone',
  friends: 'Friends',
  private: 'Only you',
}

async function setVisibility(page, visibility, log) {
  const target = VISIBILITY_OPTION[visibility]
  if (!target) throw new Error(`unknown visibility: ${visibility}`)
  await dismissCoachmarks(page)
  const opener = page
    .locator('[role="combobox"]')
    .filter({ hasText: /Everyone|Friends|Only you|Followers/i })
    .first()
  if (!(await revealControl(page, opener))) {
    throw new Error('visibility control not found — verify selectors with --dry-run')
  }
  await opener.click()
  await page.waitForTimeout(700)
  // Options live in a popup dialog/listbox; role=option excludes the trigger.
  const opt = page
    .locator('[role="option"], [role="menuitemradio"], [role="menuitem"]')
    .filter({ hasText: new RegExp(target, 'i') })
    .first()
  if ((await opt.count().catch(() => 0)) && (await opt.isVisible().catch(() => false))) {
    await opt.click()
  } else {
    // fallback: click the label text inside any open dialog/listbox
    const alt = page
      .locator('[role="dialog"], [role="listbox"]')
      .locator(`text=/${target}/i`)
      .first()
    await alt.click()
  }
  await page.waitForTimeout(400)
  log(`visibility set: ${visibility}`)
}

// Upload one clip. dryRun stops just before the final Post click and screenshots.
export async function uploadClip(
  context,
  { video, caption, aiLabel = false, visibility = null, dryRun = false, log = console.log } = {}
) {
  if (!video) throw new Error('video path required')
  const page = await context.newPage()
  try {
    log('open upload page')
    await page.goto(UPLOAD_URL, { waitUntil: 'domcontentloaded', timeout: 60000 })
    await page.waitForTimeout(3000)

    log('set file')
    const input = page.locator('input[type=file]').first()
    await input.waitFor({ state: 'attached', timeout: 30000 })
    await input.setInputFiles(video)

    log('wait for caption editor (video processing)')
    const editor = await firstVisible(page, CAPTION_SELECTORS, 90000)
    await page.waitForTimeout(1500)
    await dismissTour(page, log)

    if (caption) {
      log('write caption')
      await focusEditor(page, editor)
      await page.keyboard.press('ControlOrMeta+A')
      await page.keyboard.press('Backspace')
      for (const line of caption.split('\n')) {
        await page.keyboard.type(line, { delay: 12 })
        await page.keyboard.press('Enter')
        await page.keyboard.press('Escape')
      }
      await page.waitForTimeout(1500)
    }

    if (visibility || aiLabel) await dismissTour(page, log)
    if (visibility) await setVisibility(page, visibility, log)
    if (aiLabel) await enableAiLabel(page, log)

    const postBtn = await firstVisible(page, POST_SELECTORS, 30000)
    // wait until enabled (upload finished)
    for (let i = 0; i < 60; i++) {
      const disabled = await postBtn.getAttribute('disabled').catch(() => null)
      const aria = await postBtn.getAttribute('aria-disabled').catch(() => null)
      if (disabled === null && aria !== 'true') break
      await page.waitForTimeout(1000)
    }

    if (dryRun) {
      const shot = `/tmp/tiktok-dryrun-${Date.now()}.png`
      await page.screenshot({ path: shot, fullPage: true }).catch(() => {})
      log(`DRY RUN — reached enabled Post button, not clicking. screenshot: ${shot}`)
      return { ok: true, dryRun: true, screenshot: shot }
    }

    log('click Post')
    await postBtn.click()
    await page.waitForTimeout(8000)
    log('posted (post-click settle done)')
    return { ok: true, url: page.url() }
  } catch (err) {
    const shot = `/tmp/tiktok-error-${Date.now()}.png`
    await page.screenshot({ path: shot, fullPage: true }).catch(() => {})
    log(`ERROR screenshot: ${shot}`)
    throw err
  } finally {
    await page.waitForTimeout(500)
    await page.close().catch(() => {})
  }
}
