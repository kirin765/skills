// triage.mjs — Kmong 인박스 트리아지 (읽기 전용)
// Chrome :9222(chrome-cdp-profile, 크몽 로그인 상태)에 connectOverCDP로 붙어
// 내부 API GET만으로 스레드 목록 + 메시지를 읽어 구조화 JSON을 stdout에 출력한다.
// 클릭·읽음처리(PUT read) 없음 → 순수 read. 분류·초안은 스킬(Claude)이 이 JSON을 받아 수행.
//
// 실행: 세션 cwd(brain)에서  node "<skill>/scripts/triage.mjs"
// 전제: Chrome이 --remote-debugging-port=9222 --user-data-dir=~/chrome-cdp-profile 로 떠 있고 크몽 로그인 상태.

import { chromium } from 'playwright';

const CDP = process.env.KMONG_CDP || 'http://localhost:9222';
const API = 'https://kmong.com/api/v5/inbox-groups';

function fail(code, msg) {
  console.log(JSON.stringify({ ok: false, error: code, hint: msg }));
  process.exit(1);
}

// CDP 전용 Chrome(chrome-cdp-profile, 9222) 이 안 떠 있을 때 backup 으로 자동 기동한다.
// 사용자의 평소 Chrome(Default 프로파일)은 별도 --user-data-dir 라 손대지 않는다.
async function launchCdpChromeMacos() {
  const os = await import('node:os');
  const { spawn } = await import('node:child_process');
  const path = await import('node:path');
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
    if (ok) {
      try {
        browser = await chromium.connectOverCDP(CDP);
      } catch (e2) {
        fail('no-cdp', `자동 기동 후에도 Chrome :9222 연결 실패 (${e2.message})`);
      }
    } else {
      fail('no-cdp', `자동 기동 실패 — 디버그포트로 Chrome을 직접 띄워야 함 (${e.message})`);
    }
  } else {
    fail('no-cdp', `Chrome :9222 연결 실패 — 디버그포트로 Chrome이 떠 있는지 확인 (${e.message})`);
  }
}

const ctx = browser.contexts()[0];
if (!ctx) fail('no-context', 'CDP 컨텍스트 없음 — Chrome 창이 있는지 확인');
const req = ctx.request;

// 1) 스레드 목록 (페이지네이션 전부)
let groups = [];
for (let page = 1; page <= 10; page++) {
  const res = await req.get(`${API}?page=${page}`);
  if (!res.ok()) fail('api-list', `inbox-groups ${res.status()} — 로그인 만료 가능`);
  const j = await res.json();
  const arr = j.inbox_groups || [];
  groups.push(...arr);
  if (!j.next_page_link || arr.length === 0) break;
}

if (groups.length === 0) fail('empty-or-logged-out', '스레드 0건 — 크몽 로그인 상태 확인 필요');

// 2) 각 스레드의 메시지 로드 → 구조화
const threads = [];
for (const g of groups) {
  const gid = g.inbox_group_id;
  const partnerId = g.partner?.USERID;
  let messages = [];
  let gig = null;
  try {
    const mres = await req.get(`${API}/${gid}/messages?page=1`);
    if (mres.ok()) {
      const mj = await mres.json();
      const raw = mj.messages || [];
      messages = raw.map(m => ({
        mine: !!m.is_mine,
        date: m.sent_at_date || null,
        time: m.sent_at_time || null,
        text: (m.message || '').trim(),
        action: m.action || null,
      }));
      // 문의 서비스(gig) 정보 — 첫 메시지 extra_data
      const ex = raw.find(m => m.extra_data && m.extra_data.title)?.extra_data;
      if (ex) gig = {
        title: ex.title,
        price: ex.price ?? null,
        category: ex.category_info?.sub_category_name || ex.category_info?.root_category_name || null,
      };
    }
  } catch { /* 개별 스레드 실패는 스킵, 전체 중단 안 함 */ }

  threads.push({
    name: g.partner?.username || '(unknown)',
    inbox_group_id: gid,
    partner_id: partnerId,
    url: `https://kmong.com/inboxes?inbox_group_id=${gid}&partner_id=${partnerId}`,
    gig,                              // 문의 서비스 {title, price, category} — 유흥 필터·초안 컨텍스트
    last_message_mine: !!g.is_mine,   // true = 내가 마지막 발화(팔로업 후보), false = 고객 대기 = needs_reply
    unread: !!g.is_unread,
    sent_at_rel: g.sent_at || null,   // "44분 전" 등
    group_started_at: g.group_started_at || null,
    preview: (g.message || '').trim().slice(0, 120),
    messages,
  });
}

console.log(JSON.stringify({ ok: true, count: threads.length, threads }, null, 1));
await browser.close();
