#!/usr/bin/env node
// Postiz Public API CLI helper.
//
// Env:
//   POSTIZ_API_KEY   (required)
//   POSTIZ_BASE_URL  (default: https://api.postiz.com/public/v1)
//
// Commands:
//   integrations
//     → 연결된 SNS 계정 목록 (id | provider | name).
//
//   upload <file>
//     → 이미지/영상 업로드. 반환된 {id, path} 를 post 의 --image 로 전달.
//
//   post [--now | --schedule <ISO-UTC>]
//        --integration <id>[:<__type>]   (반복 가능 — 멀티 플랫폼)
//        [--content <text>]              (단일 게시물)
//        [--thread <text> ...]           (반복 가능 — 스레드)
//        [--image <id>:<path>]           (반복 가능)
//        [--settings <json>]             (해당 호출의 모든 integration 에 적용)
//        [--type <__type>]               (--settings 안 쓸 때 짧은 형태)
//        [--short-link]
//        [--tag <tag>]                   (반복 가능)
//     → 게시물 생성. --content 와 --thread 둘 다 있으면 --content 가 thread 첫 원소.
//
//   delete <post-id>
//     → 게시물 삭제. 404 / 일부 5xx 는 "이미 삭제됨" 으로 간주, 성공 처리.
//
//   raw <method> <path> [body-json]
//     → 인증 헤더만 박아서 임의 endpoint 호출. 디버깅용.
//
// 예시:
//   POSTIZ_API_KEY=xxx node postiz.mjs integrations
//   node postiz.mjs upload ./photo.jpg
//   node postiz.mjs post --now --integration abc:x --content "hi"
//   node postiz.mjs post --schedule 2026-05-28T01:00:00Z \
//        --integration abc:x --integration def:linkedin \
//        --content "사장부 빌드로그 #3" --image img-123:https://uploads.postiz.com/p.jpg
//   node postiz.mjs post --now --integration abc:x \
//        --thread "1편" --thread "2편" --thread "3편"

import fs from 'node:fs';
import path from 'node:path';

const API_KEY = process.env.POSTIZ_API_KEY;
const BASE_URL = (process.env.POSTIZ_BASE_URL || 'https://api.postiz.com/public/v1').replace(/\/$/, '');

if (!API_KEY) {
  console.error('error: POSTIZ_API_KEY 환경변수 필요. .env 또는 export 로 설정.');
  process.exit(2);
}

function authHeaders(extra = {}) {
  return { Authorization: API_KEY, ...extra };
}

async function apiFetch(method, urlPath, { body, formData } = {}) {
  const url = `${BASE_URL}${urlPath}`;
  const opts = { method, headers: authHeaders() };
  if (formData) {
    opts.body = formData;
  } else if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = typeof body === 'string' ? body : JSON.stringify(body);
  }
  const res = await fetch(url, opts);
  const text = await res.text();
  let parsed;
  try { parsed = text ? JSON.parse(text) : null; } catch { parsed = text; }
  if (!res.ok) {
    const err = new Error(`HTTP ${res.status} ${method} ${urlPath}: ${typeof parsed === 'string' ? parsed : JSON.stringify(parsed)}`);
    err.status = res.status;
    err.body = parsed;
    throw err;
  }
  return parsed;
}

function parseArgs(argv) {
  const args = { _: [], flags: {}, multi: {} };
  const multiKeys = new Set(['integration', 'thread', 'image', 'tag']);
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      const next = argv[i + 1];
      const isBool = next === undefined || next.startsWith('--');
      const value = isBool ? true : next;
      if (!isBool) i++;
      if (multiKeys.has(key)) {
        (args.multi[key] ||= []).push(value);
      } else {
        args.flags[key] = value;
      }
    } else {
      args._.push(a);
    }
  }
  return args;
}

function parsePair(s, sep = ':') {
  const idx = s.indexOf(sep);
  if (idx < 0) return [s, undefined];
  return [s.slice(0, idx), s.slice(idx + 1)];
}

// --- commands ---

async function cmdIntegrations() {
  const list = await apiFetch('GET', '/integrations');
  if (!Array.isArray(list) || list.length === 0) {
    console.log('(연결된 integration 없음 — Postiz UI 에서 먼저 SNS 계정 연결)');
    return;
  }
  console.log('id'.padEnd(38) + ' | ' + 'provider'.padEnd(20) + ' | name');
  console.log('-'.repeat(38) + '-+-' + '-'.repeat(20) + '-+-' + '-'.repeat(30));
  for (const it of list) {
    const id = String(it.id || '').padEnd(38);
    const prov = String(it.providerIdentifier || it.provider || '').padEnd(20);
    const name = it.name || it.username || '';
    const flag = it.disabled ? ' [disabled]' : '';
    console.log(`${id} | ${prov} | ${name}${flag}`);
  }
}

async function cmdUpload(file) {
  if (!file) throw new Error('upload: 파일 경로 필요');
  const abs = path.resolve(file);
  if (!fs.existsSync(abs)) throw new Error(`upload: 파일 없음 — ${abs}`);
  const buf = fs.readFileSync(abs);
  const blob = new Blob([buf]);
  const fd = new FormData();
  fd.append('file', blob, path.basename(abs));
  const out = await apiFetch('POST', '/upload', { formData: fd });
  console.log(JSON.stringify(out, null, 2));
  if (out?.id && out?.path) {
    console.log(`\n→ post 호출 시:  --image ${out.id}:${out.path}`);
  }
}

function buildValueArray({ content, thread, image }) {
  const texts = thread.length > 0 ? thread.slice() : [];
  if (content) texts.unshift(content);
  if (texts.length === 0) {
    throw new Error('post: --content 또는 --thread 중 최소 하나 필요');
  }
  const images = image.map((s) => {
    const [id, p] = parsePair(s);
    if (!id || !p) throw new Error(`--image 형식 오류: "${s}" — "id:path" 형태로`);
    return { id, path: p };
  });
  return texts.map((text, idx) => ({
    content: text,
    image: idx === 0 ? images : [],
  }));
}

async function cmdPost(args) {
  const isNow = !!args.flags.now;
  const schedule = args.flags.schedule;
  if (!isNow && !schedule) throw new Error('post: --now 또는 --schedule <ISO-UTC> 중 하나 필요');
  if (!isNow && !/Z$/.test(String(schedule))) {
    throw new Error(`post: --schedule 은 UTC ISO 8601 (Z로 끝남) 만 허용. 받은 값: "${schedule}"`);
  }

  const integrations = (args.multi.integration || []).map((s) => {
    const [id, typ] = parsePair(s);
    if (!id) throw new Error(`--integration 형식 오류: "${s}"`);
    return { id, type: typ };
  });
  if (integrations.length === 0) throw new Error('post: --integration <id>[:<__type>] 최소 1개 필요');

  const content = args.flags.content || null;
  const thread = args.multi.thread || [];
  const image = args.multi.image || [];
  const tags = args.multi.tag || [];

  let settingsBase = null;
  if (args.flags.settings) {
    try { settingsBase = JSON.parse(args.flags.settings); }
    catch (e) { throw new Error(`--settings JSON 파싱 실패: ${e.message}`); }
  }
  const defaultType = args.flags.type || null;

  const value = buildValueArray({ content, thread, image });

  const posts = integrations.map(({ id, type }) => {
    const __type = type || defaultType || settingsBase?.__type;
    if (!__type) {
      throw new Error(`integration ${id} 에 __type 미지정. --integration <id>:<__type> 또는 --type / --settings 사용`);
    }
    const settings = { ...(settingsBase || {}), __type };
    return { integration: { id }, value, settings };
  });

  const body = {
    type: isNow ? 'now' : 'schedule',
    date: isNow ? new Date().toISOString() : schedule,
    shortLink: !!args.flags['short-link'],
    tags,
    posts,
  };

  if (args.flags['dry-run']) {
    console.log(JSON.stringify(body, null, 2));
    return;
  }

  const out = await apiFetch('POST', '/posts', { body });
  console.log(JSON.stringify(out, null, 2));
}

async function cmdDelete(id) {
  if (!id) throw new Error('delete: post id 필요');
  try {
    const out = await apiFetch('DELETE', `/posts/${encodeURIComponent(id)}`);
    console.log(out ?? '(ok)');
  } catch (e) {
    if (e.status === 404 || (e.status >= 500 && e.status < 600)) {
      console.log(`(${e.status}) 이미 삭제됨 / 처리됨 — 무시.`);
      return;
    }
    throw e;
  }
}

async function cmdRaw(method, urlPath, bodyJson) {
  if (!method || !urlPath) throw new Error('raw: <method> <path> [body-json]');
  const body = bodyJson ? JSON.parse(bodyJson) : undefined;
  const out = await apiFetch(method.toUpperCase(), urlPath.startsWith('/') ? urlPath : `/${urlPath}`, { body });
  console.log(JSON.stringify(out, null, 2));
}

// --- main ---

async function main() {
  const [cmd, ...rest] = process.argv.slice(2);
  const args = parseArgs(rest);

  if (!cmd || cmd === '--help' || cmd === '-h') {
    console.log(fs.readFileSync(new URL(import.meta.url).pathname, 'utf8').split('\n').slice(1, 45).join('\n').replace(/^\/\/ ?/gm, ''));
    return;
  }

  try {
    switch (cmd) {
      case 'integrations': return await cmdIntegrations();
      case 'upload':       return await cmdUpload(args._[0]);
      case 'post':         return await cmdPost(args);
      case 'delete':       return await cmdDelete(args._[0]);
      case 'raw':          return await cmdRaw(args._[0], args._[1], args._[2]);
      default:
        console.error(`unknown command: ${cmd}`);
        process.exit(2);
    }
  } catch (e) {
    console.error(`error: ${e.message}`);
    process.exit(1);
  }
}

main();
