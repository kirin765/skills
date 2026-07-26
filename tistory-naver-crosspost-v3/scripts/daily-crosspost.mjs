#!/usr/bin/env node
// daily-crosspost.mjs — 매일 아침 9시 launchd 잡 (com.brain.daily-crosspost).
// ~/.tistory-queue/pending/ 에서 가장 오래된 due JSON 1건을 골라:
//   1. Naver Blog 공개 발행까지 완료 (crosspost.mjs naver 모드)
//   2. Tistory 초안(임시저장) 생성 — hook 없이 tistory-scheduler run 을 동기 실행
// 큐가 비어 있으면 아무것도 하지 않는다. 글감 등록은 v3 `tistory-queue --no-hook` 모드
// (또는 agent-queue-guide.md 스펙의 JSON을 pending/ 에 직접 저장)로 한다.
//
// Naver 이중 발행 방지: 발행 성공 시 JSON에 naverPublishedAt/naverUrl 을 stamp 한다.
// 티스토리 단계가 실패해 JSON이 pending/failed 에 남아도 다음 실행이 Naver 를 다시
// 발행하지 않는다. Naver 실패 시 JSON은 pending 에 그대로 → 다음날 재시도.

import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { execFileSync } from "node:child_process";

const QUEUE_DIR = path.join(os.homedir(), ".tistory-queue");
const PENDING_DIR = path.join(QUEUE_DIR, "pending");
const DONE_DIR = path.join(QUEUE_DIR, "done");
const LOG_DIR = path.join(QUEUE_DIR, "logs");
const V3 = path.join(path.dirname(new URL(import.meta.url).pathname), "crosspost.mjs");
const SCHEDULER = path.join(os.homedir(), ".gemini/config/skills/tistory-post/scripts/tistory-scheduler.mjs");

fs.mkdirSync(LOG_DIR, { recursive: true });
function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}`;
  console.log(line);
  fs.appendFileSync(path.join(LOG_DIR, `daily-${new Date().toISOString().slice(0, 10)}.log`), line + "\n");
}

function telegram(text) {
  try {
    const env = fs.readFileSync(path.join(os.homedir(), "niche-finder/.env"), "utf8");
    const token = env.match(/^TELEGRAM_BOT_TOKEN=(.+)$/m)?.[1]?.trim();
    const chat = env.match(/^TELEGRAM_CHAT_ID=(.+)$/m)?.[1]?.trim();
    if (!token || !chat) return;
    return fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chat, text, parse_mode: "Markdown" }),
    }).catch(() => {});
  } catch {}
}

// tistory-scheduler.mjs runOnce 와 같은 선택 규칙: 이름순 정렬, scheduledAt 미래면 skip.
function pickJob() {
  const files = fs.readdirSync(PENDING_DIR).filter(f => f.endsWith(".json")).sort();
  const now = new Date();
  for (const file of files) {
    try {
      const data = JSON.parse(fs.readFileSync(path.join(PENDING_DIR, file), "utf8"));
      if (data.scheduledAt && new Date(data.scheduledAt) > now) continue;
      return { file, data };
    } catch (e) {
      log(`invalid JSON skipped: ${file} (${e.message})`);
    }
  }
  return null;
}

function run(cmd, args) {
  try {
    return { ok: true, out: execFileSync(cmd, args, { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }) };
  } catch (e) {
    return { ok: false, out: (e.stdout || "") + (e.stderr || "") + (e.message || "") };
  }
}

(async () => {
  if (!fs.existsSync(PENDING_DIR)) { log("pending dir missing — nothing to do"); return; }
  const job = pickJob();
  if (!job) { log("queue empty — nothing to do"); return; }
  const jsonPath = path.join(PENDING_DIR, job.file);
  const tags = Array.isArray(job.data.tags) ? job.data.tags.join(",") : (job.data.tags || "");
  log(`processing [${job.file}]: "${job.data.title}"`);

  // 1. Naver 공개 발행 (이미 발행된 job이면 skip — 티스토리 단계만 재시도하는 경우)
  if (job.data.naverPublishedAt) {
    log(`naver already published at ${job.data.naverPublishedAt} — skipping naver`);
  } else {
    const args = [V3, "naver", "--source", job.data.source, "--title", job.data.title];
    if (job.data.hero) args.push("--hero", job.data.hero);
    if (tags) args.push("--tags", tags);
    const r = run(process.execPath, args);
    log("--- naver output ---\n" + r.out.trim());
    const url = r.out.match(/\[naver-publish\] ✅ PUBLISHED → (\S+)/)?.[1];
    if (!url) {
      log("❌ naver publish FAILED — JSON stays in pending, retry tomorrow");
      await telegram(`⚠ *데일리 크로스포스트 실패*\nNaver 발행 실패: ${job.data.title}\n내일 9시 재시도. 로그: ~/.tistory-queue/logs/`);
      process.exit(1);
    }
    job.data.naverPublishedAt = new Date().toISOString();
    job.data.naverUrl = url;
    fs.writeFileSync(jsonPath, JSON.stringify(job.data, null, 2) + "\n");
    log(`✅ naver published → ${url}`);
  }

  // 2. Tistory 초안 — hook 없이 scheduler run 동기 실행 (같은 정렬 규칙이라 같은 job을 집는다)
  const t = run(process.execPath, [SCHEDULER, "run"]);
  log("--- tistory output ---\n" + t.out.trim());
  const doneOk = fs.existsSync(path.join(DONE_DIR, job.file));
  if (doneOk) {
    log("✅ tistory draft saved — job moved to done/");
    await telegram(`✅ *데일리 크로스포스트 완료*\n${job.data.title}\nNaver 발행: ${job.data.naverUrl}\nTistory: 임시저장 완료 (발행은 수동)`);
  } else {
    log("❌ tistory draft step did not move job to done/ — check failed/ and logs");
    await telegram(`⚠ *데일리 크로스포스트 부분 실패*\n${job.data.title}\nNaver는 발행됨: ${job.data.naverUrl}\nTistory 초안 실패 — ~/.tistory-queue/failed/ 확인`);
    process.exit(1);
  }
})().catch(async e => {
  log("FATAL: " + (e.stack || e.message));
  await telegram(`⚠ *데일리 크로스포스트 FATAL*\n${e.message}`);
  process.exit(1);
});
