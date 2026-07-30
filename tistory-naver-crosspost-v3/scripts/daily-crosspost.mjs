#!/usr/bin/env node
// daily-crosspost.mjs — 매일 아침 9시 launchd 잡 (com.brain.daily-crosspost).
// ~/.naver-queue/pending/ 에서 가장 오래된 due JSON 1건을 골라 Naver Blog 공개
// 발행까지 완료하고 (crosspost.mjs naver 모드) done/ 으로 옮긴다.
//
// Naver 대기열은 ~/.tistory-queue 와 완전히 분리다 — 티스토리 스케줄러는 이 폴더를
// 모르고, 이 잡은 티스토리 큐를 절대 건드리지 않는다. (같은 큐를 공유하면 티스토리
// hook 이 JSON 을 done 으로 옮겨 Naver 발행이 누락된다 — 그래서 분리.)
//
// 글감 등록은 v3 `queue` 모드가 양쪽 대기열(naver-queue + tistory-queue)에 같은 JSON
// 을 넣는다. Naver 실패 시 JSON 은 pending 에 그대로 → 다음날 재시도.

import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { execFileSync } from "node:child_process";

const QUEUE_DIR = path.join(os.homedir(), ".naver-queue");
const PENDING_DIR = path.join(QUEUE_DIR, "pending");
const DONE_DIR = path.join(QUEUE_DIR, "done");
const LOG_DIR = path.join(QUEUE_DIR, "logs");
const V3 = path.join(path.dirname(new URL(import.meta.url).pathname), "crosspost.mjs");

for (const d of [PENDING_DIR, DONE_DIR, LOG_DIR]) fs.mkdirSync(d, { recursive: true });
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

// 선택 규칙: 이름순 정렬, scheduledAt 미래면 skip. 하루 1건.
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
  const job = pickJob();
  if (!job) { log("naver queue empty — nothing to do"); return; }
  const tags = Array.isArray(job.data.tags) ? job.data.tags.join(",") : (job.data.tags || "");
  log(`processing [${job.file}]: "${job.data.title}"`);

  const args = [V3, "naver", "--source", job.data.source, "--title", job.data.title];
  if (job.data.hero) args.push("--hero", job.data.hero);
  if (tags) args.push("--tags", tags);
  if (job.data.naverCategory) args.push("--naver-category", job.data.naverCategory);
  if (job.data.naverTopic) args.push("--naver-topic", job.data.naverTopic);
  const r = run(process.execPath, args);
  log("--- naver output ---\n" + r.out.trim());
  const url = r.out.match(/\[naver-publish\] ✅ PUBLISHED → (\S+)/)?.[1];
  if (!url) {
    log("❌ naver publish FAILED — JSON stays in pending, retry tomorrow");
    await telegram(`⚠ *데일리 네이버 발행 실패*\n${job.data.title}\n내일 9시 재시도. 로그: ~/.naver-queue/logs/`);
    process.exit(1);
  }
  job.data.naverPublishedAt = new Date().toISOString();
  job.data.naverUrl = url;
  fs.writeFileSync(path.join(DONE_DIR, job.file), JSON.stringify(job.data, null, 2) + "\n");
  fs.unlinkSync(path.join(PENDING_DIR, job.file));
  log(`✅ naver published → ${url} — job moved to done/`);
  await telegram(`✅ *데일리 네이버 발행 완료*\n${job.data.title}\n${url}`);
})().catch(async e => {
  log("FATAL: " + (e.stack || e.message));
  await telegram(`⚠ *데일리 네이버 발행 FATAL*\n${e.message}`);
  process.exit(1);
});
