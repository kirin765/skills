#!/usr/bin/env node
// Google Tasks CLI — 공식 Tasks REST API (OAuth 데스크톱 플로우, loopback 자동 수신).
//
// 사용법:
//   node google_tasks.mjs create --title "제목" [--notes "메모"] [--due 2026-09-04] [--list @default]
//   node google_tasks.mjs list [--limit 10]
//   node google_tasks.mjs lists
//
// 최초 실행: 콘솔에 찍힌 URL을 브라우저에서 열어 동의 → 코드가 localhost:8599 로 자동 복귀.
// 자격증명: ~/.config/rb-gtasks/client.json (OAuth 데스크톱 클라이언트 JSON) 또는
//          GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET 환경변수.
// 토큰 캐시: ~/.config/rb-gtasks/token.json (offline access + prompt=consent → refresh 토큰 보장, 자동 갱신).
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { createServer } from "node:http";
import { homedir } from "node:os";
import { join } from "node:path";

const SCOPES = "https://www.googleapis.com/auth/tasks";
const REDIRECT_PORT = 8599;
const REDIRECT_URI = `http://localhost:${REDIRECT_PORT}`;
const TOKEN_DIR = join(homedir(), ".config", "rb-gtasks");

// ---------- 자격증명 로드 ----------
function loadCredentials() {
  if (process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET) {
    return { client_id: process.env.GOOGLE_CLIENT_ID, client_secret: process.env.GOOGLE_CLIENT_SECRET };
  }
  const p = join(TOKEN_DIR, "client.json");
  if (!existsSync(p)) {
    console.error(
      "자격증명 없음. 아래 중 하나를 준비하세요:\n" +
        `  1) ${p} 에 OAuth 데스크톱 클라이언트 JSON 저장 (Google Cloud Console → Google Tasks API 사용 → OAuth 클라이언트 ID(데스크톱 앱) 생성 → JSON 다운로드)\n` +
        "  2) GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET 환경변수 설정"
    );
    process.exit(1);
  }
  const j = JSON.parse(readFileSync(p, "utf8"));
  const installed = j.installed ?? j.web ?? j;
  if (!installed.client_id || !installed.client_secret) {
    console.error("client.json 형식이 올바르지 않습니다 (client_id/client_secret 누락).");
    process.exit(1);
  }
  return { client_id: installed.client_id, client_secret: installed.client_secret };
}

// ---------- 토큰 저장/로드 ----------
function loadToken() {
  try {
    const t = JSON.parse(readFileSync(join(TOKEN_DIR, "token.json"), "utf8"));
    if (t.access_token && t.refresh_token) return t;
  } catch {}
  return null;
}
function saveToken(t) {
  mkdirSync(TOKEN_DIR, { recursive: true });
  writeFileSync(join(TOKEN_DIR, "token.json"), JSON.stringify(t, null, 2));
}

// ---------- OAuth ----------
async function exchangeCode(code) {
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code,
      client_id: creds.client_id,
      client_secret: creds.client_secret,
      redirect_uri: REDIRECT_URI,
      grant_type: "authorization_code",
    }),
  });
  const j = await r.json();
  if (!r.ok || !j.access_token) throw new Error(`token exchange 실패: ${r.status} ${JSON.stringify(j)}`);
  return j;
}

async function refreshToken(t) {
  const r = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      refresh_token: t.refresh_token,
      client_id: creds.client_id,
      client_secret: creds.client_secret,
      grant_type: "refresh_token",
    }),
  });
  const j = await r.json();
  if (!r.ok || !j.access_token) throw new Error(`refresh 실패: ${r.status} ${JSON.stringify(j)}`);
  return { ...t, access_token: j.access_token, expires_at: Date.now() + (j.expires_in ?? 3600) * 1000 };
}

async function getAccessToken() {
  let t = loadToken();
  if (t && t.expires_at && t.expires_at > Date.now() + 60_000) return t.access_token;
  if (t?.refresh_token) {
    const fresh = await refreshToken(t);
    saveToken(fresh);
    return fresh.access_token;
  }
  // 최초 인증 — loopback 서버 띄우고 콘솔 URL 출력, 동의 완료 시 코드 자동 수신
  const { authUrl, code, srv } = await new Promise((resolve) => {
    let authUrl = "";
    const srv = createServer((req, res2) => {
      const url = new URL(req.url, REDIRECT_URI);
      const code = url.searchParams.get("code");
      const err = url.searchParams.get("error");
      res2.writeHead(200, { "content-type": "text/html; charset=utf-8" });
      res2.end(code ? "<h2>인증 완료. 이 탭은 닫아도 됩니다.</h2>" : `<h2>인증 실패: ${err ?? "no code"}</h2>`);
      srv.close(); // 프로세스가 떠 있지 않게 반드시 닫는다
      resolve({ authUrl, code, srv });
    });
    srv.listen(REDIRECT_PORT, "127.0.0.1", () => {
      authUrl =
        "https://accounts.google.com/o/oauth2/v2/auth?" +
        new URLSearchParams({
          client_id: creds.client_id,
          redirect_uri: REDIRECT_URI,
          response_type: "code",
          scope: SCOPES,
          access_type: "offline",
          prompt: "consent",
        });
      console.log("\n아래 URL을 브라우저에서 열어 동의해 주세요 (코드 자동 수신):\n\n" + authUrl + "\n");
    });
  });
  if (!code) throw new Error("인증 코드를 받지 못했습니다.");
  const j = await exchangeCode(code);
  const tok = { ...j, expires_at: Date.now() + (j.expires_in ?? 3600) * 1000 };
  saveToken(tok);
  return tok.access_token;
}

// ---------- Tasks API ----------
async function api(accessToken, path, method = "GET", body) {
  const r = await fetch("https://tasks.googleapis.com/tasks/v1" + path, {
    method,
    headers: {
      authorization: `Bearer ${accessToken}`,
      ...(body ? { "content-type": "application/json" } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(`HTTP ${r.status} ${JSON.stringify(j)}`);
  return j;
}

/** 기한 정규화 — RFC3339 `due` 필드용. GOTCHA: Tasks API는 보낸 타임스탬프의
 *  UTC 날짜로 하루를 결정하므로, 원하는 날짜의 **UTC 자정**(`T00:00:00.000Z`)으로
 *  보내야 날짜가 밀리지 않는다. (dueDate 필드는 API에 없음 — 쓰면 조용히 무시된다.) */
function normalizeDue(raw) {
  if (!raw) return undefined;
  let dateStr = raw;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
    const d = new Date(raw);
    if (Number.isNaN(d.getTime())) throw new Error(`due 형식 오류: ${raw} — 예: 2026-09-04 또는 2026-09-04T09:00:00+09:00`);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    dateStr = `${y}-${m}-${dd}`;
  }
  return `${dateStr}T00:00:00.000Z`;
}

// ---------- CLI ----------
const [, , cmd, ...rest] = process.argv;
function arg(name, def) {
  const i = rest.indexOf(`--${name}`);
  return i >= 0 && rest[i + 1] !== undefined ? rest[i + 1] : def;
}

try {
  const token = await getAccessToken();

  if (cmd === "create") {
    const title = arg("title");
    if (!title) throw new Error("--title 필수");
    const body = {
      title,
      notes: arg("notes"),
      due: normalizeDue(arg("due")),
    };
    const created = await api(token, `/lists/${encodeURIComponent(arg("list", "@default"))}/tasks`, "POST", body);
    console.log("\n✅ Google Tasks 생성 완료:");
    console.log(`   제목 : ${created.title}`);
    console.log(`   기한 : ${created.due ?? "(없음)"}`);
    console.log(`   id   : ${created.id}`);
    console.log("   확인 : https://tasks.google.com/\n");
  } else if (cmd === "list") {
    const items = await api(token, `/lists/${encodeURIComponent(arg("list", "@default"))}/tasks?maxResults=${arg("limit", "10")}`);
    const rows = items.items ?? [];
    console.log(`최근 태스크 ${rows.length}건 (${arg("list", "@default")}):`);
    for (const t of rows) {
      const done = t.status === "completed" ? "[x]" : "[ ]";
      const due = t.due ? ` (기한 ${t.due.slice(0,10)})` : "";
      console.log(`${done} ${t.title}${due}  id=${t.id}`);
    }
    if (!rows.length) console.log("(없음)");
  } else if (cmd === "lists") {
    const items = await api(token, "/users/@me/lists");
    for (const l of items.items ?? []) console.log(`${l.id}  ${l.title}`);
  } else {
    console.log("사용법:");
    console.log("  node google_tasks.mjs create --title \"제목\" [--notes \"메모\"] [--due 2026-09-04] [--list @default]");
    console.log("  node google_tasks.mjs list [--limit 10]");
    console.log("  node google_tasks.mjs lists");
  }
} catch (e) {
  console.error("\n실패:", String(e));
  console.error("힌트: 403 Forbidden → Cloud 프로젝트에서 'Google Tasks API'를 사용(Enable)했는지 확인. invalid_grant → 동의 코드는 1회용, 처음부터 다시.");
  process.exit(1);
}