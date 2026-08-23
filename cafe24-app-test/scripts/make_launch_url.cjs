#!/usr/bin/env node
// 카페24 앱 launch URL 생성 (S2 검증용 — 테스트 설치 한도 소모 안 함)
// 사용: node make_launch_url.mjs <mall_id> <app_url> <client_secret> [user_name]
const crypto = require('crypto');

const [mall, appUrl, secret, userName] = process.argv.slice(2);
if (!mall || !appUrl || !secret) {
  console.error('사용: node make_launch_url.mjs <mall_id> <app_url> <client_secret> [user_name]');
  process.exit(1);
}

const ts = Math.floor(Date.now() / 1000);
const params = [
  ['lang', 'ko_KR'],
  ['mall_id', mall],
  ['nation', 'KR'],
  ['shop_no', '1'],
  ['timestamp', String(ts)],
  ['user_id', mall],
  ['user_name', userName || '대표 관리자'],
  ['user_type', 'P'],
];
// 알파벳순 정렬 + encodeURIComponent 재조립 (공백 %20, '+' 아님 — 실측 함정 #2)
const qs = params
  .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
  .join('&');
const hmac = crypto.createHmac('sha256', secret).update(qs).digest('base64');
const url = `${appUrl}?${qs}&hmac=${encodeURIComponent(hmac)}`;
console.log(url);
