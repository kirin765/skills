---
name: postiz-publish
description: Postiz Public API로 X·LinkedIn·Threads·Instagram·Reddit·Mastodon·Bluesky 등 32개 SNS 플랫폼에 글을 즉시 발행하거나 스케줄링하는 자동화 스킬. 사용자가 "Postiz로 발행", "Postiz API", "SNS 일괄 발행", "멀티 플랫폼 스케줄링", "X랑 LinkedIn 동시에 올려줘", "Threads 스레드 예약", "publish via Postiz", "schedule a post to multiple platforms" 같은 표현을 쓸 때 반드시 사용한다. 단순히 한 플랫폼에 글 쓰는 게 아니라 *예약·다중 플랫폼·스레드·미디어 업로드*가 필요한 모든 SNS 발행 작업에 발동. Postiz Cloud 와 self-hosted 인스턴스 양쪽 모두 지원.
---

# Postiz Publish

Postiz Public API (`/public/v1`) 를 통해 SNS 게시물을 만들고, 예약하고, 멀티 플랫폼에 동시에 뿌리는 워크플로우.

핵심 원칙: **API 호출은 거의 항상 `scripts/postiz.mjs` 를 통해서 한다.** 직접 curl/fetch 를 짜지 않는다. 헤더·페이로드 형태가 까다로워서 매번 새로 작성하면 실수난다. 스킬 안의 클라이언트가 그걸 흡수한다.

## 사전 조건

다음이 모두 있어야 함:

### 0. Postiz 가 어디서 돌아가는지 확정

이 스킬은 API **사용** 만 다룬다. Postiz 자체가 떠 있어야 호출할 곳이 있다.

- **Postiz Cloud** (`https://api.postiz.com`) — 가입 즉시 사용 가능. **무료 영구 tier 없음**, 7일 trial 후 Standard $29/월. (https://postiz.com/pricing)
- **Self-host** — 도커로 띄우면 무료. 단 Postgres + Redis + Temporal 까지 같이 떠야 하고, SNS 마다 OAuth client 직접 발급 필요. 1인 메이커가 비용 아끼려고 self-host 하면 OAuth 발급에 반나절 갈 수 있음.

사용자가 어느 쪽인지 모르면 거기서 멈추고 물어볼 것. 호스팅 결정·self-host 절차·SNS 별 OAuth 어디서 발급하는지는 `references/hosting.md` 참고.

### 1. `POSTIZ_API_KEY`
Postiz UI → **Settings → Developers → Public API → Reveal** 에서 발급. Cloud / self-host 동일 경로. `.env` 에 저장. **절대 로그·커밋에 노출 X**.

### 2. `POSTIZ_BASE_URL`
- Cloud → 생략 가능 (기본값 `https://api.postiz.com/public/v1`)
- Self-host → `https://<your-postiz-host>/public/v1` 명시

### 3. Integration ID = "Channel"
**중요한 용어 혼동:** Postiz UI 는 "Channel" 이라 부르고, API 는 "Integration" 이라 부른다. 같은 것이다.

- **무엇인가:** Postiz 에 SNS 계정 (X, Instagram 등) 을 OAuth 로 연결하면 Postiz 가 그 연결마다 내부 ID 를 부여한 레코드. 이 레코드 ID 가 곧 Integration ID.
- **어떻게 만드나:** Postiz UI → **Launches → Add Channel → 원하는 SNS 선택 → OAuth 로그인** → 끝. 발행하려는 모든 SNS 계정에 대해 미리 해놔야 함.
- **ID 어디서 보나:** **UI 에는 안 보인다.** 오직 `GET /integrations` (즉, `postiz.mjs integrations`) 호출로만 알 수 있다. 그래서 첫 워크플로우가 항상 ID 조회로 시작함.

키·base URL 이 없으면 거기서 멈춰서 사용자에게 받기 전에 진행하지 말 것.

## 워크플로우 (항상 이 순서)

### 1. Integration ID 확보

발행 전에 한 번은 무조건:

```bash
node scripts/postiz.mjs integrations
```

출력 예:
```
id                                   | provider  | name
abc-x-id                             | x         | @sajangbu_kr
ghi-th-id                            | threads   | sajangbu_kr
jkl-ig-id                            | instagram | sajangbu_kr
mno-yt-id                            | youtube   | 사장부 채널
```

여기서 나오는 `id` 를 다음 단계에서 그대로 쓴다. 사용자가 "X에 올려줘" 라고 하면 너는 X integration ID 가 뭔지 알아내야 하지, ID 자체를 추측하면 안 된다.

### 2. (있으면) 미디어 업로드

이미지/영상이 포함된 글이면 **본문 POST 전에** 업로드부터:

```bash
node scripts/postiz.mjs upload ./path/to/photo.jpg
# → { "id": "img-123", "path": "https://uploads.postiz.com/photo.jpg" }
```

반환된 `id` 와 `path` 를 둘 다 다음 단계 페이로드에 넘긴다.

50MB 이상이면 413 떨어진다. base64 인라인 X — 무조건 업로드 엔드포인트 통하기.

### 3. 게시물 생성

세 가지 패턴:

**단일 플랫폼 · 즉시 발행**
```bash
node scripts/postiz.mjs post --now \
  --integration abc-x-id \
  --type x \
  --content "테스트 발행입니다"
```

**멀티 플랫폼 · 예약** (X + Threads + Instagram 동시)
```bash
node scripts/postiz.mjs post \
  --schedule "2026-05-28T01:00:00Z" \
  --integration abc-x-id:x \
  --integration ghi-th-id:threads \
  --integration jkl-ig-id:instagram \
  --settings '{"__type":"instagram","post_type":"post"}' \
  --content "사장부 빌드로그 #3 공개" \
  --image img-123:https://uploads.postiz.com/photo.jpg
```

> **참고:** `--settings` 는 모든 integration 에 일괄 적용 + 각 `--integration` 의 `:타입` 으로 `__type` 만 덮어쓴다. Instagram 처럼 추가 필수 키 (`post_type`) 가 있는 플랫폼은 `--settings` 로 명시. 자세한 플랫폼별 키는 `references/platforms.md`.

**스레드 (X / Bluesky / Mastodon)**
```bash
node scripts/postiz.mjs post --now \
  --integration abc-x-id:x \
  --thread "1편: 정산 분리 자동화 왜 만들었나" \
  --thread "2편: 쿠팡 API 한계 — Marketplace vs Growth 엔드포인트 분리" \
  --thread "3편: 실제 사용 화면 → sajangbu.com"
```

스레드는 같은 integration 안에서 `value[]` 배열의 원소가 늘어나는 구조다. 멀티 플랫폼과 스레드를 동시에 하려면 `--integration` 을 여러 번 + 각 integration 별로 `--thread` 가 같은 텍스트로 적용된다 (스크립트가 처리).

### 4. (필요 시) 삭제

예약 글 취소:
```bash
node scripts/postiz.mjs delete <post-id>
```

`404` 나 일부 `5xx` 는 "이미 지워짐" 의미이므로 무시 OK.

## 시간 처리

- `--schedule` 인자는 **ISO 8601 UTC** (`Z` 로 끝남) 만 받는다. 사용자가 "내일 오전 10시" 라고 하면:
  1. 현재 시각과 사용자 타임존 (대개 한국 = KST = UTC+9) 을 확인
  2. KST 기준 시각을 UTC 로 변환
  3. `2026-05-28T01:00:00Z` 처럼 변환된 값을 전달
- `--now` 와 `--schedule` 은 같은 엔드포인트인데 스크립트가 `type` 필드만 토글한다.

## 플랫폼별 settings

각 플랫폼마다 `settings.__type` 외에 추가 옵션이 있다. 단순 텍스트 글은 `__type` 만 박아도 되지만, 아래는 필수 옵션이 있는 플랫폼들:

- **YouTube** → `title` 필수, `description`, `tags[]`, `privacy: public|unlisted|private` (영상 업로드 후 필요)
- **Instagram** → `post_type: post|reel|story`
- **Reddit** → `subreddit`, `title` 필수
- **Pinterest** → `board_id` 필수
- **TikTok** → `privacy` 필수

`--settings '{"__type":"reddit","subreddit":"smallbusiness","title":"..."}'` 처럼 JSON 통째로 오버라이드 가능. 전체 32개 플랫폼 매핑 + 키 목록은 `references/platforms.md`.

## 레이트 리미트

- Cloud: **100 req/hour** (POST `/posts` 에만 적용)
- Self-host 기본: **90 req/hour**, `API_LIMIT` env 로 조정 가능

큰 캠페인 (50+ 글 한번에) 이면 사용자에게 미리 알리고 배치 분할 제안.

## Webhooks · 업데이트

- Postiz 는 공식 webhook 이벤트가 (현재 기준) **없다**. 발행 결과 확인은 `GET /posts` 폴링.
- 예약 글 수정 엔드포인트도 공식 문서에 없음 — **delete 후 재생성** 패턴으로 처리.

## 더 깊이 들어갈 때

- 모든 엔드포인트 · 정확한 페이로드 스키마 → `references/api.md`
- 32개 플랫폼 `__type` 표 · 플랫폼별 settings 키 → `references/platforms.md`
- 스크립트 사용법 자세히 → `scripts/postiz.mjs --help`

## 자주 하는 실수

- `Authorization: Bearer ...` ❌ — Postiz 는 prefix 없이 `Authorization: <key>` 만 받음
- `date` 를 로컬 시간으로 보냄 ❌ — 반드시 UTC ISO + `Z`
- 이미지를 base64 로 인라인 ❌ — 413 떨어짐, 업로드 엔드포인트 통하기
- Integration ID 추측 ❌ — 무조건 `integrations` 먼저
- API 키를 코드/로그에 인쇄 ❌ — 키는 항상 env 에서만 읽기
