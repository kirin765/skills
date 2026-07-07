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

// Expand the collapsed "Show more" settings panel if present (AI-label &
// visibility controls sometimes live behind it). Best-effort; no-op if absent.
async function expandMoreSettings(page, log) {
  const triggers = [
    'text=/^\\s*(더 보기|더보기|Show more)\\s*$/',
    'button:has-text("더 보기")',
    'button:has-text("Show more")',
  ]
  for (const sel of triggers) {
    const loc = page.locator(sel).first()
    if (await loc.count().catch(() => 0) && (await loc.isVisible().catch(() => false))) {
      await loc.click().catch(() => {})
      log('expanded more-settings panel')
      await page.waitForTimeout(800)
      return
    }
  }
}

// Turn ON the "AI-generated content" disclosure. Idempotent — reads the switch
// state and only clicks when it's off. Selectors are text-anchored with
// aria-fallbacks because TikTok's class names are build hashes.
async function enableAiLabel(page, log) {
  await expandMoreSettings(page, log)
  const labelText = page
    .locator('text=/AI(-| )?생성 콘텐츠|AI-generated content|AI generated content/i')
    .first()
  if (!(await labelText.count().catch(() => 0))) {
    throw new Error('AI-label control not found — verify selectors with --dry-run')
  }
  // The switch is a sibling/nearby role=switch within the same setting row.
  const row = labelText.locator('xpath=ancestor-or-self::*[.//*[@role="switch"]][1]')
  const sw = (await row.count().catch(() => 0))
    ? row.locator('[role="switch"]').first()
    : page.locator('[role="switch"]').first()
  await sw.waitFor({ state: 'visible', timeout: 10000 })
  const checked = await sw.getAttribute('aria-checked').catch(() => null)
  if (checked === 'true') {
    log('AI-label already ON')
    return
  }
  await sw.click()
  await page.waitForTimeout(600)
  const after = await sw.getAttribute('aria-checked').catch(() => null)
  if (after !== 'true') throw new Error('AI-label toggle did not switch ON')
  log('AI-label set ON')
}

// Select who can watch. TikTok uses a custom dropdown, not a native <select>.
const VISIBILITY_LABELS = {
  public: ['모두', 'Everyone', 'Public'],
  friends: ['친구', 'Friends'],
  private: ['나만', 'Only you', 'Private'],
}

async function setVisibility(page, visibility, log) {
  const labels = VISIBILITY_LABELS[visibility]
  if (!labels) throw new Error(`unknown visibility: ${visibility}`)
  await expandMoreSettings(page, log)
  const opener = page
    .locator('text=/이 동영상을 볼 수 있는 사람|Who can watch this video/i')
    .first()
  if (!(await opener.count().catch(() => 0))) {
    throw new Error('visibility control not found — verify selectors with --dry-run')
  }
  // Open the dropdown: click the control row's combobox/button.
  const control = opener.locator(
    'xpath=ancestor-or-self::*[.//*[@role="combobox" or @role="button"] or self::button][1]'
  )
  const clickTarget = (await control.count().catch(() => 0)) ? control.first() : opener
  await clickTarget.click().catch(() => opener.click())
  await page.waitForTimeout(600)
  for (const text of labels) {
    const opt = page.locator(`[role="option"]:has-text("${text}"), li:has-text("${text}")`).first()
    if (await opt.count().catch(() => 0) && (await opt.isVisible().catch(() => false))) {
      await opt.click()
      await page.waitForTimeout(400)
      log(`visibility set: ${visibility}`)
      return
    }
  }
  throw new Error(`visibility option not found for ${visibility} — verify with --dry-run`)
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
      await editor.click()
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
  } finally {
    await page.waitForTimeout(500)
    await page.close().catch(() => {})
  }
}
