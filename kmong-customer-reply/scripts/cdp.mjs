// cdp.mjs — 크몽 CDP(9222) 공용 연결/기동 헬퍼.
//
// Linux(Omarchy/Hyprland) 에선 CDP 창이 사용자 포커스를 뺏지 않도록 **반드시**
// `--class=cdpchrome` 로 띄운다. hyprland.lua 의 아래 규칙과 짝을 이룬다:
//   o.window("^cdpchrome$", { no_initial_focus = true, suppress_event = "activatefocus",
//                             float = false, workspace = "3 silent" })
// 클래스 플래그를 빠뜨리면 Wayland app_id 가 'chromium-browser' 가 되어 규칙이
// 안 걸리고 포커스를 뺏는다. cdp-anywhere/probe.py 와 동일한 방식.

import { chromium } from 'playwright';
import os from 'node:os';
import path from 'node:path';
import fs from 'node:fs';
import { spawn, execSync } from 'node:child_process';

export const CDP = process.env.KMONG_CDP || 'http://localhost:9222';

function findBrowserBin() {
  if (process.platform === 'darwin') {
    return '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  }
  for (const name of ['chromium', 'chromium-browser', 'google-chrome-stable', 'google-chrome']) {
    try {
      const p = execSync(`command -v ${name}`, { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim();
      if (p) return p;
    } catch { /* not found */ }
  }
  return 'chromium';
}

// 에이전트 셸엔 세션 env(Wayland display 등)가 없는 경우가 많아 보강한다.
function ensureSessionEnv() {
  const uid = typeof process.getuid === 'function' ? process.getuid() : '';
  if (!process.env.XDG_RUNTIME_DIR) process.env.XDG_RUNTIME_DIR = `/run/user/${uid}`;
  if (!process.env.WAYLAND_DISPLAY) {
    try {
      const sock = fs.readdirSync(process.env.XDG_RUNTIME_DIR)
        .find(d => d.startsWith('wayland-') && !d.endsWith('.lock'));
      if (sock) process.env.WAYLAND_DISPLAY = sock;
    } catch { /* ignore */ }
  }
}

// CDP 전용 브라우저(chrome-cdp-profile, 9222)를 백그라운드로 띄운다.
// 사용자의 평소 브라우저(다른 프로파일)는 건드리지 않는다.
export async function launchCdpChrome() {
  const profileDir = path.join(os.homedir(), 'chrome-cdp-profile');
  const bin = findBrowserBin();
  const args = [`--remote-debugging-port=9222`, `--user-data-dir=${profileDir}`];
  if (process.platform !== 'darwin') {
    args.push('--class=cdpchrome', '--no-first-run', '--no-default-browser-check');
    ensureSessionEnv();
  }
  try {
    const child = spawn(bin, args, { stdio: 'ignore', detached: true });
    child.unref();
  } catch (e) {
    return { ok: false, msg: `CDP 브라우저 기동 실패: ${e.message}` };
  }
  for (let i = 0; i < 15; i++) {
    await new Promise(r => setTimeout(r, 1000));
    try { await (await fetch(`${CDP}/json/version`)).json(); return { ok: true, msg: 'CDP 브라우저 자동 기동 성공' }; }
    catch { /* keep polling */ }
  }
  return { ok: false, msg: 'CDP 브라우저를 띄웠지만 15초 내 9222 응답 없음' };
}

// 9222 연결. 미응답이고 기본 로컬 주소면 CDP 전용 브라우저를 자동 기동해 재시도한다.
export async function connectCdp({ log = () => {} } = {}) {
  try {
    return await chromium.connectOverCDP(CDP);
  } catch (e) {
    if (CDP !== 'http://localhost:9222') throw e;
    log('⏳ CDP 9222 미응답 — CDP 전용 브라우저(chrome-cdp-profile) 자동 기동 시도 중...');
    const { ok, msg } = await launchCdpChrome();
    log((ok ? '✅ ' : '❌ ') + msg);
    if (!ok) throw new Error(`자동 기동 실패 — 디버그포트로 브라우저를 직접 띄워야 함 (${msg})`);
    return await chromium.connectOverCDP(CDP);
  }
}
