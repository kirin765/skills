# Play Developer API — 읽기 전용 조회

Play Console의 현재 상태를 브라우저 없이 API로 읽는다. 서비스 계정·venv는 이 스킬과 공유.

- **키**: `~/.config/play-publisher/sa.json`
- **실행**: `~/.config/play-publisher/venv/bin/python ~/.claude/skills/android-app-builder/scripts/play_read.py <cmd> [--package PKG]`
- **기본 앱**: `com.kiwan.quicktodo` (다른 앱은 `--package`로). 그 앱에 서비스 계정 읽기 권한 필요(없으면 403 → Play Console 사용자/권한에서 부여).

읽기 전용 설계: 모든 조회는 edit을 열어 읽고 **즉시 abandon**한다. commit·업로드·수정 절대 없음.

## 요청 → 명령 매핑

| 사용자가 원하는 것 | 명령 |
|---|---|
| 한눈에 전체 현황 | `summary` (details+tracks+bundles+언어) |
| 리뷰·별점 보기 | `reviews [--max N] [--lang en]` |
| 출시 트랙·버전·rollout % | `tracks` |
| 올라간 AAB versionCode 목록 | `bundles` |
| 언어별 제목/설명 현황 | `listings` |
| 스크린샷·아이콘·피처그래픽(이미지 URL) | `images [--lang ko-KR]` |
| 기본언어·연락 이메일/웹 | `details` |

애매하면 `summary`부터 돌려 전체를 보여주고, 사용자가 좁히면 해당 명령으로 깊이 판다.

## 출력 처리

스크립트는 구조화 JSON을 stdout으로 낸다. 그대로 덤프하지 말고 **사용자 질문에 답하는 형태로 요약**한다. 예: "프로덕션에 versionCode 3 (1.0.1) 100% 출시 완료. 업로드된 AAB는 v2·v3." 리뷰가 `count:0`이면 "현재 API가 반환하는 리뷰 없음"이라고 솔직히.

## 한계 (솔직히 알릴 것)

- **집계 평점(평균 별점)·설치수·크래시·매출 통계는 이 API에 없다.** Play **리포팅 API**(또는 BigQuery export, Pub/Sub) 소관. "평점 추세/설치수" 물으면 androidpublisher로는 못 준다고 말하고 개별 리뷰(`reviews`)만 제공.
- `reviews.list`는 전체 아카이브 아님 — 비교적 최근·댓글 포함 위주. 페이지네이션 `--token`(출력의 `nextToken`).
- **스크린샷·아이콘은 *언어별 등록정보*에 붙는다 — 버전별 아님.** `images`는 현재 등록 언어 기준 반환(`--lang`).
- 권한 없는 앱이면 403 — 그 앱에 서비스 계정을 Play Console에서 초대.
