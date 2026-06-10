# Postiz Public API Reference

Base URLs:
- Cloud: `https://api.postiz.com/public/v1`
- Self-host: `https://<your-postiz-host>/public/v1`

Auth header: `Authorization: <api-key>` (no `Bearer`).

## GET /integrations

연결된 소셜 계정 목록.

응답 (배열):
```json
[
  {
    "id": "abc-x-id",
    "providerIdentifier": "x",
    "name": "@sajangbu_kr",
    "picture": "https://...",
    "disabled": false
  }
]
```

`providerIdentifier` 가 곧 `settings.__type` 값.

## POST /upload

이미지/영상 업로드. `multipart/form-data`.

요청:
```
POST /upload
Authorization: <key>
Content-Type: multipart/form-data

file=@photo.jpg
```

응답:
```json
{
  "id": "img-123",
  "path": "https://uploads.postiz.com/photo.jpg",
  "type": "image",
  "createdAt": "..."
}
```

50MB 초과 시 413.

## POST /posts

게시물 생성 (즉시 / 예약).

요청 body 전체 스키마:
```json
{
  "type": "schedule",
  "date": "2026-05-28T10:00:00.000Z",
  "shortLink": false,
  "tags": [],
  "posts": [
    {
      "integration": { "id": "abc-x-id" },
      "value": [
        {
          "content": "본문 텍스트",
          "image": [
            { "id": "img-123", "path": "https://uploads.postiz.com/photo.jpg" }
          ]
        }
      ],
      "settings": { "__type": "x", "who_can_reply_post": "everyone" }
    }
  ]
}
```

필드 설명:

| 필드 | 타입 | 설명 |
|---|---|---|
| `type` | `"schedule"` \| `"now"` | 예약 vs 즉시. `"now"` 여도 `date` 는 필수. |
| `date` | ISO 8601 UTC | `Z` 로 끝나는 UTC. 로컬 타임 X. |
| `shortLink` | bool | URL 단축 여부. 기본 false. |
| `tags` | string[] | Postiz UI 내부 분류용. 비워도 됨. |
| `posts[]` | array | 각 원소 = 한 SNS 계정에 대한 발행. |
| `posts[].integration.id` | string | `/integrations` 의 `id`. |
| `posts[].value[]` | array | 원소 1개 = 단일 게시물. 원소 2+ = 스레드. |
| `posts[].value[].content` | string | 본문. |
| `posts[].value[].image[]` | array | `{id, path}` 객체 배열. 업로드 결과 그대로. |
| `posts[].settings.__type` | string | 플랫폼 식별자 (`x`, `linkedin`, `threads`, ...). |
| `posts[].settings.*` | 플랫폼별 | `platforms.md` 참고. |

응답 (성공):
```json
{ "id": "post-id-xxx", ... }
```

## GET /posts

게시물 목록. 정확한 쿼리 파라미터는 공식 docs 의 endpoint 상세 페이지를 확인 (시점에 따라 변경 가능).

용도:
- 예약 글 상태 확인 (webhook 없으므로 폴링용)
- 특정 글 ID 조회

## DELETE /posts/:id

게시물 삭제.

- `200/204` → 삭제 성공
- `404` → 이미 삭제됨 / 존재 안 함 (무시 OK)
- 일부 `5xx` 도 "이미 처리됨" 의미일 수 있음 — DELETE 한정으로만 관대하게.

## 에러 코드 요약

| 코드 | 의미 | 대응 |
|---|---|---|
| `400` | 페이로드 malformed | 스키마 다시 확인 |
| `401` | API 키 누락/잘못됨 | 키 확인, Bearer prefix 붙이지 말 것 |
| `403` | 리소스 소유자 X | integration ID 가 본인 계정 것인지 확인 |
| `404` | 리소스 없음 | DELETE 면 무시, 그 외엔 ID 재확인 |
| `413` | 본문 50MB 초과 | 이미지를 `/upload` 통해 미리 올리기 |
| `429` | 레이트 리미트 | 지수 백오프 후 재시도. Cloud 100/hr, self-host 기본 90/hr |
| `5xx` | 서버 에러 | 1-2분 백오프 후 재시도 |

## OAuth2 (3rd-party 앱용)

Postiz 사용자 대신 행동하는 외부 앱은 OAuth2 토큰 사용. 토큰은 `pos_` 로 시작. 헤더 형식은 API 키와 동일. 자세한 건 https://docs.postiz.com/public-api/oauth.

이 스킬은 기본적으로 **본인 API 키** 사용 시나리오를 가정한다. OAuth 가 필요한 상황 (예: 다른 사용자 대신 발행) 이면 사용자에게 명시적으로 확인 후 위 docs 참고.
