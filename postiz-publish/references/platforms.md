# Postiz 플랫폼 레퍼런스

각 플랫폼의 `settings.__type` 값과 자주 쓰는 추가 settings 키. `__type` 은 `GET /integrations` 응답의 `providerIdentifier` 와 동일.

> **출처 주의:** 이 표는 2026-05 기준 공식 docs + repo 소스 (`libraries/nestjs-libraries/src/integrations/social/`) 를 추린 것. 시점에 따라 새 플랫폼/옵션 추가될 수 있음. 비표준 settings 가 필요하면 위 디렉토리의 해당 `.ts` 파일에서 `__type` 으로 grep.

## 소셜 (대형)

| `__type` | 플랫폼 | 자주 쓰는 settings 키 |
|---|---|---|
| `x` | X (Twitter) | `who_can_reply_post`: `everyone` \| `following` \| `mentionedUsers` |
| `linkedin` | LinkedIn 개인 | (없음 — content 만) |
| `linkedin-page` | LinkedIn 회사 페이지 | `page_id` (자동) |
| `facebook` | Facebook 페이지 | `post_type`: `post` \| `reel` \| `story` |
| `instagram` | Instagram (비즈) | `post_type`: `post` \| `reel` \| `story`, `collaborators[]` |
| `instagram-standalone` | Instagram 단독 (no FB) | 위와 동일 |
| `threads` | Threads | (없음) |
| `bluesky` | Bluesky | `replyToUrl` (옵션) |
| `mastodon` | Mastodon | `instance` (자동, integration 에 묶임) |
| `telegram` | Telegram 채널/그룹 | `chat_id` (자동) |

## 영상

| `__type` | 플랫폼 | settings |
|---|---|---|
| `youtube` | YouTube | `title` (필수), `description`, `tags[]`, `privacy`: `public`\|`unlisted`\|`private`, `category` |
| `tiktok` | TikTok | `privacy`: `PUBLIC_TO_EVERYONE`\|`MUTUAL_FOLLOW_FRIENDS`\|`SELF_ONLY`, `disable_duet`, `disable_stitch`, `disable_comment` |

영상 플랫폼은 `value[].image[]` 대신 동영상 파일을 업로드한 결과를 넣는다 (`/upload` 가 type 자동 판별).

## 커뮤니티

| `__type` | 플랫폼 | settings |
|---|---|---|
| `reddit` | Reddit | `subreddit` (필수), `title` (필수), `flair_id`, `nsfw`, `spoiler` |
| `lemmy` | Lemmy | `community_id`, `title` |
| `discord` | Discord webhook | `channel_id` (자동) |
| `slack` | Slack | `channel_id` (자동) |
| `skool` | Skool | `community_id`, `category_id` |
| `whop` | Whop | `experience_id` |

Reddit 은 `title` 이 별도 필드 — body 의 `content` 와 다름. subreddit 이름은 `r/` prefix 빼고.

## 비주얼 / 디자인

| `__type` | 플랫폼 | settings |
|---|---|---|
| `pinterest` | Pinterest | `board_id` (필수), `title`, `link` (외부 URL) |
| `dribbble` | Dribbble | `title`, `tags[]` |

## 블로깅

| `__type` | 플랫폼 | settings |
|---|---|---|
| `medium` | Medium | `title` (필수), `tags[]`, `canonical_url`, `publish_status`: `public`\|`draft`\|`unlisted` |
| `devto` | Dev.to | `title`, `tags[]`, `canonical_url`, `series` |
| `hashnode` | Hashnode | `title`, `publication_id`, `tags[]`, `cover_image` |
| `wordpress` | WordPress | `title`, `categories[]`, `tags[]`, `status`: `publish`\|`draft` |

블로그 플랫폼은 본문이 길어서 보통 `content` 에 markdown 통째로 넣는다. Postiz 가 자동 변환.

## 기타

| `__type` | 플랫폼 | 설명 |
|---|---|---|
| `warpcast` | Farcaster (Warpcast) | content + image, `channel` 옵션 |
| `nostr` | Nostr | relays 자동 |
| `vk` | VK | 러시아 SNS |
| `kick` | Kick | 라이브스트리밍 |
| `twitch` | Twitch | 클립 등 |
| `gmb` | Google My Business | `cta_button`, `cta_url` |
| `listmonk` | Listmonk (뉴스레터) | `subject`, `list_ids[]` |

## 스레드 지원 매트릭스

`posts[].value[]` 배열 길이 > 1 일 때:

| 플랫폼 | 스레드 동작 |
|---|---|
| `x` | 트윗 → 답글 체인 |
| `bluesky` | Skeet → 답글 체인 |
| `mastodon` | Toot → 답글 체인 |
| `threads` | Threads 체인 (Meta API) |
| `linkedin`, `facebook`, `instagram`, `reddit` | **스레드 미지원** — `value[0]` 만 발행, 나머지 무시되거나 에러 가능 |
| `medium`, `devto`, `hashnode`, `wordpress` | **스레드 무의미** — `value[0].content` 만 사용 |

스레드가 의미있는 플랫폼끼리만 같은 글로 묶을 것. 불가능 플랫폼은 별도 호출로.

## settings 오버라이드 패턴

`scripts/postiz.mjs` 의 `--settings` 인자로 통째로 JSON 넘기면 됨:

```bash
node scripts/postiz.mjs post --now \
  --integration reddit-id \
  --settings '{"__type":"reddit","subreddit":"smallbusiness","title":"How I automated...","flair_id":""}' \
  --content "본문 markdown..."
```

`--type x` 같은 짧은 형태는 `__type` 만 박힌 기본 settings 를 만든다. 플랫폼별 필수 키 (Reddit `subreddit`/`title`, YouTube `title`, Pinterest `board_id`, Medium `title` 등) 가 있으면 `--settings` 로 정확히 넘겨야 함.
