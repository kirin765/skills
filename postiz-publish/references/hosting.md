# Postiz 호스팅 결정 (Cloud vs Self-host)

API 호출 자체는 양쪽 동일. **인프라 비용 / 운영 부담** 트레이드오프만 다름.

## 옵션 1 — Postiz Cloud

- 가격 (2026-05 기준, https://postiz.com/pricing):
  - **Standard $29/월** — 5 channel, 400 posts/월
  - **Team $39/월** — 10 channel, unlimited posts
  - **Pro $49/월** — 30 channel, unlimited posts
  - **Ultimate $99/월** — 100 channel
- 무료 영구 tier **없음**. 7일 trial 만.
- 즉시 사용 가능. SNS 별 OAuth 앱 따로 만들 필요 없음 (Postiz 가 자기 OAuth client 사용).
- 결제 끊기면 예약 글 안 나감.

**언제 Cloud 가 정답:**
- 월 $29 가 크게 안 부담 + 인프라 안 만지고 싶음
- 1-5개 channel, 월 400건 이하

## 옵션 2 — Self-host (docker-compose)

- 비용 0 (서버 비용만). AGPL 오픈소스.
- 부담: **Postgres + Redis + Temporal** 까지 같이 떠야 함 — 한 컨테이너 앱 아님.
- OAuth client ID/secret 을 **각 SNS 마다 사용자가 직접 발급** 해서 env 에 박아야 함 (X Developer Portal, Meta App, Google Cloud Console, 등).

**최소 절차:**
```bash
git clone https://github.com/gitroomhq/postiz-docker-compose
cd postiz-docker-compose
# docker-compose.yml 안의 env 채움 (아래 표 참고)
docker compose up -d
# → http://localhost:4007 접속
```

**필수 env (최소):**

| 변수 | 예시 | 비고 |
|---|---|---|
| `MAIN_URL` | `http://localhost:4007` | 사용자가 브라우저로 접근하는 URL |
| `FRONTEND_URL` | 동일 | |
| `NEXT_PUBLIC_BACKEND_URL` | `http://localhost:4007/api` | API public URL |
| `BACKEND_INTERNAL_URL` | `http://backend:3000` | 컨테이너 내부 통신 |
| `JWT_SECRET` | 랜덤 32+ 자 | `openssl rand -hex 32` |
| `DATABASE_URL` | `postgres://...` | docker-compose 가 함께 띄움 |
| `REDIS_URL` | `redis://...` | 동일 |
| `TEMPORAL_ADDRESS` | `temporal:7233` | 워크플로우 엔진 |

> **참고:** Postiz 는 `NEXTAUTH_URL` 안 씀 (NextAuth 가 아니라 자체 JWT).

**SNS 별 OAuth credential (선택 — 쓸 채널만 발급):**

| SNS | env 쌍 | 어디서 발급 |
|---|---|---|
| X | `X_API_KEY`, `X_API_SECRET` | https://developer.twitter.com (Developer Portal) |
| Threads | `THREADS_APP_ID`, `THREADS_APP_SECRET` | https://developers.facebook.com (Meta for Developers) — Threads 는 Meta 산하 |
| Instagram | `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET` (Instagram Business 계정 연결) | 동일 (Meta) |
| YouTube | `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` | https://console.cloud.google.com (Google Cloud Console → OAuth client) |
| LinkedIn | `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET` | https://www.linkedin.com/developers |
| Reddit | `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET` | https://www.reddit.com/prefs/apps |
| TikTok | `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET` | https://developers.tiktok.com |
| Pinterest | `PINTEREST_CLIENT_ID`, `PINTEREST_CLIENT_SECRET` | https://developers.pinterest.com |

> **현실 체크:** Instagram·YouTube·TikTok OAuth 앱 발급은 시간 걸림 (Meta·Google·TikTok 의 앱 리뷰 거치는 경우 多). X 와 Threads 가 가장 빨리 됨.

**언제 self-host 가 정답:**
- 월 $29 가 부담 / 장기적으로 비용 줄이고 싶음
- 채널 수 많거나 발행 횟수 많음
- 도커·env 만지는 거 OK
- API key 노출 등 데이터 통제 원함

**언제 self-host 가 안 맞음:**
- SNS 마다 OAuth 앱 발급하는 시간이 더 아까움
- Postgres + Redis + Temporal 운영 부담 싫음

## 옵션 3 — Vercel 배포?

Postiz 는 **Vercel 만으로 안 됨**. Temporal worker (장기 실행) 와 Redis 큐가 필수라서 Next.js 만 있는 게 아님. Railway / Render / Fly.io / 일반 VPS (Hetzner, DigitalOcean) 추천.

## 결정 후 SKILL.md 로 돌아가서:

- Cloud → `POSTIZ_BASE_URL` 안 줘도 됨 (기본 `https://api.postiz.com/public/v1`)
- Self-host → `POSTIZ_BASE_URL=https://<your-host>/public/v1` 명시
- API key 발급: 어느 쪽이든 **Postiz UI → Settings → Developers → Public API → Reveal** 동일

## 출처

- Pricing: https://postiz.com/pricing
- Self-host: https://docs.postiz.com/installation/docker-compose
- Channel = Integration 용어: https://docs.postiz.com/public-api/introduction
