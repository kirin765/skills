import { chromium } from 'playwright';
import os from 'node:os';
import path from 'node:path';
import fs from 'node:fs';

// One persistent Chrome profile per (platform, account). Keeping each account in
// its own --user-data-dir is what lets a single machine stay logged into several
// accounts on the same platform at once (e.g. a promo IG + a cat IG) without the
// email-verification dance that account-switching inside one profile triggers.
export const PROFILE_ROOT =
  process.env.SOCIAL_UPLOAD_PROFILES ||
  path.join(os.homedir(), '.social-upload', 'profiles');

export function profileDir(platform, account) {
  if (!account) throw new Error('--account is required (selects which login to use)');
  const safe = String(account).replace(/[^\w.@-]/g, '_');
  const dir = path.join(PROFILE_ROOT, `${platform}__${safe}`);
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

export function hasProfile(platform, account) {
  const safe = String(account).replace(/[^\w.@-]/g, '_');
  return fs.existsSync(path.join(PROFILE_ROOT, `${platform}__${safe}`, 'Default'));
}

// channel:'chrome' drives the installed Google Chrome, so no playwright browser
// download is needed. A distinct user-data-dir guarantees a separate process even
// if the user's main Chrome is open.
export async function launch(dir) {
  return chromium.launchPersistentContext(dir, {
    headless: false,
    channel: 'chrome',
    viewport: { width: 1280, height: 900 },
    args: [
      '--disable-blink-features=AutomationControlled',
      '--no-first-run',
      '--no-default-browser-check',
    ],
  });
}

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
