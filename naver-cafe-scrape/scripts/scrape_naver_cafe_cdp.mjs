#!/usr/bin/env node
// 네이버 카페 CDP 스크랩 — node raw-CDP 폴백 (Playwright/Network 도메인 비활성 환경용).
//
// 이 환경의 chrome-cdp-profile Chrome 은 Playwright connectOverCDP 와 Network.enable/
// Page.navigate 가 행/실패한다. 안정적으로 동작하는 것만 사용:
//   - Network.getAllCookies (httpOnly 포함 전체 쿠키)
//   - Runtime.evaluate (페이지 컨텍스트, navigation 없이)
//   - /json/new 로 탭 생성 → Runtime 으로 club_id 추출
// 그 다음은 추출한 쿠키로 node 서버사이드 fetch (CORS 없음).
//
// 사용:
//   node scrape_naver_cafe_cdp.mjs --cafe soho --probe
//   node scrape_naver_cafe_cdp.mjs --cafe soho --search "쿠팡 정산" --pages 40 [--body] [--deep]
//   node scrape_naver_cafe_cdp.mjs --cafe soho --article 4064913
//   node scrape_naver_cafe_cdp.mjs --cafe soho --club 10094408 --search 정산   # club 직접 지정(resolve 생략)
//
// 검색 모드: 카페 키워드 검색 REST 가 폐기/변경되어(2026-06) archive 검색 불가.
// → ArticleListV2(전체글 최신피드) 를 --pages 만큼 페이지네이션하며 제목 grep.
//   --body: 제목 매치 글의 본문도 받아 스니펫 포함. --deep: 모든 글 본문까지 grep(느림).

const BASE = process.env.CDP_URL || 'http://localhost:9222';
const IS_DEFAULT_CDP = !process.env.CDP_URL;

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
    try { await (await fetch(`${BASE}/json/version`)).json(); return { ok: true, msg: 'CDP Chrome 자동 기동 성공' }; }
    catch {}
  }
  return { ok: false, msg: 'CDP Chrome 을 띄웠지만 15초 내 9222 응답 없음' };
}

// ---------- args ----------
const A = process.argv.slice(2);
function arg(name, def = null) { const i = A.indexOf('--' + name); if (i < 0) return def; const v = A[i + 1]; return (!v || v.startsWith('--')) ? true : v; }
const CAFE = arg('cafe');
let CLUB = arg('club');
const SEARCH = arg('search');
const ARTICLE = arg('article');
const PAGES = parseInt(arg('pages', '40'), 10);
const WANT_BODY = !!arg('body', false);
const DEEP = !!arg('deep', false);
const PROBE = !!arg('probe', false);
const OUT = arg('out', null);
if (!CAFE && !CLUB) { console.error('❌ --cafe <이름> 필수 (또는 --club <id>)'); process.exit(1); }

// ---------- raw CDP ----------
function cdp(ws) { let id = 0; const p = new Map(); ws.addEventListener('message', e => { const m = JSON.parse(e.data); if (m.id && p.has(m.id)) { p.get(m.id)(m); p.delete(m.id); } }); return (method, params = {}) => new Promise(res => { const _id = ++id; p.set(_id, res); ws.send(JSON.stringify({ id: _id, method, params })); }); }
function connect(u) { return new Promise((res, rej) => { const ws = new WebSocket(u); ws.addEventListener('open', () => res(ws)); ws.addEventListener('error', () => rej(new Error('ws 연결 실패'))); setTimeout(() => rej(new Error('ws timeout')), 8000); }); }
async function evalPage(send, expr) { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.result && r.result.exceptionDetails) return null; return r.result && r.result.result ? r.result.result.value : null; }
async function newTab(url) { let r = await fetch(`${BASE}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' }); if (!r.ok) r = await fetch(`${BASE}/json/new?${encodeURIComponent(url)}`, { method: 'GET' }); return r.json(); }
async function closeTab(id) { try { await fetch(`${BASE}/json/close/${id}`); } catch {} }

async function getProbe() {
  // CDP 살아있는지 + 쿠키 추출 + (필요시) club_id resolve
  let list;
  try { list = await (await fetch(`${BASE}/json`)).json(); }
  catch (e) {
    if (IS_DEFAULT_CDP && process.platform === 'darwin') {
      console.error('⏳ CDP 9222 미응답 — CDP 전용 Chrome(chrome-cdp-profile) 자동 기동 시도 중...');
      const { ok, msg } = await launchCdpChromeMacos();
      console.error((ok ? '✅ ' : '❌ ') + msg);
      if (ok) {
        try { list = await (await fetch(`${BASE}/json`)).json(); }
        catch (e2) { console.error(`❌ 자동 기동 후에도 CDP ${BASE} 미응답: ${e2.message}`); process.exit(1); }
      } else {
        console.error(`Chrome 을 --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-cdp-profile" 로 직접 띄우고 네이버 로그인하세요.`);
        process.exit(1);
      }
    } else {
      console.error(`❌ CDP ${BASE} 미응답. Chrome 을 --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-cdp-profile" 로 띄우고 네이버 로그인하세요.`);
      process.exit(1);
    }
  }

  let page = list.find(t => t.type === 'page');
  let tempTab = null;
  if (!CLUB) {
    // club_id 추출용 탭 (없으면 생성)
    if (!page) { tempTab = await newTab(`https://cafe.naver.com/${CAFE}`); page = tempTab; await new Promise(r => setTimeout(r, 2800)); }
  }
  const ws = await connect(page.webSocketDebuggerUrl);
  const send = cdp(ws);
  const ck = await send('Network.getAllCookies');
  const cookies = (ck.result && ck.result.cookies || []).filter(c => /naver/.test(c.domain));
  const cookieHeader = cookies.map(c => `${c.name}=${c.value}`).join('; ');
  const hasNID = /NID_AUT/.test(cookieHeader);

  if (!CLUB) {
    // 현재 페이지가 해당 카페면 거기서, 아니면 새 탭 열어 resolve
    let cid = null;
    const onCafe = await evalPage(send, `/cafe\\.naver\\.com\\/${CAFE}(\\b|\\/)/.test(location.href)`);
    if (onCafe) cid = await evalPage(send, `document.documentElement.innerHTML.match(/clubid["']?\\s*[:=]\\s*["']?(\\d{6,})/i)?.[1]||null`);
    if (!cid) {
      const t = await newTab(`https://cafe.naver.com/${CAFE}`);
      await new Promise(r => setTimeout(r, 2800));
      const ws2 = await connect(t.webSocketDebuggerUrl); const send2 = cdp(ws2);
      cid = await evalPage(send2, `document.documentElement.innerHTML.match(/clubid["']?\\s*[:=]\\s*["']?(\\d{6,})/i)?.[1]||null`);
      ws2.close(); await closeTab(t.id);
    }
    CLUB = cid;
  }
  ws.close();
  if (tempTab) await closeTab(tempTab.id);
  return { cookieHeader, hasNID, cookieCount: cookies.length };
}

function headers(cookieHeader) {
  return { Referer: `https://cafe.naver.com/f-e/cafes/${CLUB}/menus/0?viewType=L`, Origin: 'https://cafe.naver.com', 'x-cafe-product': 'pc', Accept: '*/*', 'User-Agent': 'Mozilla/5.0', Cookie: cookieHeader };
}
function strip(h) { return (h || '').replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&').replace(/\s+/g, ' ').trim(); }

async function fetchArticle(H, id) {
  const u = `https://article.cafe.naver.com/gw/v4/cafes/${CLUB}/articles/${id}?query=&useCafeId=true&requestFrom=A`;
  const r = await fetch(u, { headers: H });
  if (r.status !== 200) return null;
  const j = await r.json();
  return j.result && j.result.article;
}

async function listPage(H, pg) {
  const u = `https://apis.naver.com/cafe-web/cafe2/ArticleListV2?search.clubid=${CLUB}&search.queryType=lastArticle&search.page=${pg}&search.perPage=50`;
  const r = await fetch(u, { headers: H });
  if (r.status !== 200) throw new Error(`list http ${r.status}`);
  const j = await r.json();
  const res = j.message && j.message.result;
  return (res && res.articleList) || [];
}

function buildRe(q) {
  if (q === true) return /./;
  const terms = String(q).split(/\s+/).filter(Boolean).map(t => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  return new RegExp(terms.join('|'), 'i');
}

// ---------- main ----------
const info = await getProbe();
if (!CLUB) { console.error('❌ club_id 추출 실패 — --club 으로 직접 지정하세요.'); process.exit(1); }
console.log(`cafe=${CAFE || '(by club)'} club_id=${CLUB} cookies=${info.cookieCount} NID=${info.hasNID}`);
if (!info.hasNID) console.error('⚠️ NID_AUT 쿠키 없음 — 로그인 안 됐을 수 있음(권한 글은 실패).');
const H = headers(info.cookieHeader);

if (PROBE) {
  // 게시판 list 1페이지 동작 확인
  try { const a = await listPage(H, 1); console.log(`✅ ArticleListV2 OK (${a.length}건). 검색: --search "<키워드>"`); }
  catch (e) { console.log(`❌ list 실패: ${e.message}`); }
  process.exit(0);
}

if (ARTICLE) {
  const a = await fetchArticle(H, ARTICLE);
  if (!a) { console.log('본문 fetch 실패'); process.exit(1); }
  const rec = { id: ARTICLE, subject: a.subject, writer: (a.writer && a.writer.nick) || '', body: strip(a.contentHtml || a.content) };
  if (OUT) { (await import('fs')).writeFileSync(OUT, JSON.stringify(rec, null, 1)); console.log('→', OUT); }
  console.log('#' + ARTICLE, a.subject, '\n', rec.body.slice(0, 1500));
  process.exit(0);
}

if (SEARCH != null) {
  const re = buildRe(SEARCH);
  const matches = []; let scanned = 0;
  for (let pg = 1; pg <= PAGES; pg++) {
    let arts; try { arts = await listPage(H, pg); } catch (e) { console.error(`page ${pg}: ${e.message}`); break; }
    if (!arts.length) break;
    for (const a of arts) {
      const it = a.item || a; scanned++;
      const subj = strip(it.subject || it.subjectHtml || '');
      let hit = re.test(subj), bodySnip = null;
      if (!hit && DEEP) { const art = await fetchArticle(H, it.articleId || it.articleid); const bt = strip(art && (art.contentHtml || art.content)); if (bt && re.test(bt)) { hit = true; bodySnip = bt.slice(0, 400); } }
      if (hit) {
        const rec = { id: it.articleId || it.articleid, subject: subj, writer: (it.writerInfo && it.writerInfo.nickName) || it.writerNickname || '', date: it.writeDate, read: it.readCount, cmt: it.commentCount };
        if (bodySnip) rec.bodySnippet = bodySnip;
        else if (WANT_BODY) { const art = await fetchArticle(H, rec.id); rec.bodySnippet = strip(art && (art.contentHtml || art.content)).slice(0, 600); }
        matches.push(rec);
      }
    }
    await new Promise(r => setTimeout(r, 250));
  }
  const result = { cafe: CAFE, club_id: CLUB, query: SEARCH, scanned, matchCount: matches.length, matches };
  const outFile = OUT || `cafe_${CAFE || CLUB}_search.json`;
  (await import('fs')).writeFileSync(outFile, JSON.stringify(result, null, 1));
  console.log(`scanned=${scanned} matches=${matches.length} → ${outFile}`);
  matches.slice(0, 50).forEach(m => console.log(' ', m.id, '|', (m.subject || '').slice(0, 55), '| 조회', m.read, '댓', m.cmt));
  process.exit(0);
}

console.log('동작 지정 필요: --probe | --search "<키워드>" | --article <id>');
