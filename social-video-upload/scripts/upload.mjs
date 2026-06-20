#!/usr/bin/env node
// Unified IG Reels / Threads / TikTok video uploader.
// Each (platform, account) gets its own persistent Chrome profile, so one machine
// can stay logged into several accounts per platform. Account is always explicit.
//
// Run with global playwright resolvable:
//   NODE_PATH=/opt/homebrew/lib/node_modules node upload.mjs <platform> <command> [...]
//
// Commands:
//   login   --account <name>                               one-time interactive login
//   whoami  --account <name>                               print the logged-in handle
//   post <video> "<caption>" --account <name> [--auto] [--expect <handle>]
//
// platforms: instagram | threads | tiktok
// Default for `post` is SUPERVISED (prepares the post, stops before publishing).
// Pass --auto to actually publish. Output is a single JSON line on the last line.

import fs from 'node:fs';
import { profileDir, launch, sleep } from './lib/browser.mjs';
import * as ig from './lib/instagram.mjs';
import * as th from './lib/threads.mjs';
import * as tt from './lib/tiktok.mjs';

const PLATFORMS = new Set(['instagram', 'threads', 'tiktok']);

function parse(argv) {
  const positional = [];
  const opts = { auto: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--auto') opts.auto = true;
    else if (a === '--account') opts.account = argv[++i];
    else if (a === '--expect') opts.expect = argv[++i];
    else if (a === '--privacy') opts.privacy = argv[++i];
    else positional.push(a);
  }
  return { positional, opts };
}

function emit(result, code = 0) {
  process.stdout.write('RESULT ' + JSON.stringify(result) + '\n');
  process.exit(code);
}
function fail(msg) {
  process.stdout.write('RESULT ' + JSON.stringify({ ok: false, error: msg }) + '\n');
  process.exit(1);
}

// IG/Threads login: open the site and poll the platform's real logged-in probe
// (URL alone is unreliable — logged-out IG/Threads serve a login form at the root).
async function waitLogin(ctx, homeUrl, isLoggedIn) {
  const page = ctx.pages()[0] || (await ctx.newPage());
  await page.goto(homeUrl, { waitUntil: 'domcontentloaded' });
  await sleep(2500);
  if (await isLoggedIn(page)) return true; // already logged in
  process.stdout.write('  로그인 창에서 직접 로그인하세요. 최대 5분 대기…\n');
  const deadline = Date.now() + 300000;
  while (Date.now() < deadline) {
    await sleep(3000);
    if (await isLoggedIn(page)) {
      await sleep(1500);
      return true;
    }
  }
  return isLoggedIn(page);
}

async function main() {
  const [platform, command, ...rest] = process.argv.slice(2);
  if (!PLATFORMS.has(platform)) fail(`platform must be one of: ${[...PLATFORMS].join(', ')}`);
  if (!command) fail('command required: login | whoami | post');

  const { positional, opts } = parse(rest);
  if (!opts.account) fail('--account <name> is required');

  // Validate inputs before spending a browser launch.
  let postArgs = null;
  if (command === 'post') {
    const [videoPath, caption] = positional;
    if (!videoPath || caption === undefined) fail('usage: post <video> "<caption>" --account <name>');
    if (!fs.existsSync(videoPath)) fail(`video not found: ${videoPath}`);
    postArgs = { videoPath, caption };
  } else if (command !== 'login' && command !== 'whoami') {
    fail(`unknown command: ${command}`);
  }

  const dir = profileDir(platform, opts.account);
  const ctx = await launch(dir);
  let output;
  let code = 0;
  try {
    if (command === 'login') {
      let ok;
      if (platform === 'instagram') ok = await waitLogin(ctx, 'https://www.instagram.com/', ig.isLoggedIn);
      else if (platform === 'threads') ok = await waitLogin(ctx, 'https://www.threads.com/', th.isLoggedIn);
      else ok = await tt.loginTikTok(ctx);
      output = { ok, platform, account: opts.account, note: ok ? 'login persisted' : 'login NOT detected' };
      code = ok ? 0 : 1;
    } else if (command === 'whoami') {
      const handle = platform === 'instagram' ? await ig.whoami(ctx)
        : platform === 'threads' ? await th.whoami(ctx)
        : await tt.whoami(ctx);
      output = { ok: !!handle, platform, account: opts.account, handle };
    } else {
      const { videoPath, caption } = postArgs;
      let res;
      if (platform === 'instagram') {
        res = await ig.publishReel(ctx, { videoPath, caption, expectedAccount: opts.expect || '', autoPost: opts.auto });
      } else if (platform === 'threads') {
        res = await th.postThreadsVideo(ctx, { videoPath, caption, autoPost: opts.auto });
      } else {
        res = await tt.postTikTok(ctx, { videoPath, caption, autoPost: opts.auto, privacy: opts.privacy || 'public' });
      }
      output = { ok: true, platform, account: opts.account, ...res };
    }
  } catch (e) {
    output = { ok: false, platform, account: opts.account, error: e.message };
    code = 1;
  } finally {
    // Always close the persistent context so the Chrome child exits and the
    // profile lock is released — otherwise repeated runs orphan Chrome processes.
    await ctx.close().catch(() => {});
  }
  emit(output, code);
}

main().catch((e) => fail(e.message));
