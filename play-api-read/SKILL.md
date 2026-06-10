---
name: play-api-read
description: Google Play Developer API(androidpublisher v3)로 Play Console 데이터를 **읽기 전용**으로 조회한다. 사용자가 "플레이스토어 리뷰 가져와줘", "내 앱 평점/리뷰 봐줘", "프로덕션 트랙 상태 어때", "지금 출시된 versionCode 뭐야", "스토어 등록정보 언어 현황", "Play API로 ~~ 조회", "앱 등록정보/연락처 확인" 같이 *Play Console의 현재 상태·리뷰를 API로 확인*하려 할 때 발동. 브라우저(Claude in Chrome)·콘솔 클릭 없이 서비스 계정 REST로 응답. 리뷰+별점, 트랙/릴리스(versionCode·rollout %), 업로드된 AAB 목록, 언어별 등록정보, 앱 details(기본언어·연락처)를 구조화로 반환. 쓰기·업로드·출시는 하지 않는다 — 그건 `android-app-builder`(빌드+업로드)나 `play-store-submit`(콘솔 작업). 등록정보 카피 최적화는 `aso-audit`. 집계 평점·설치수·크래시 통계는 이 API가 아닌 Play 리포팅 API 소관이라 다룰 수 없다.
---

# Play Developer API — 읽기 전용 조회

Play Console의 현재 상태를 브라우저 없이 API로 읽는다. 서비스 계정·venv는 이미 셋업돼 있다(`android-app-builder`와 공유).

- **키**: `~/.config/play-publisher/sa.json`
- **실행**: `~/.config/play-publisher/venv/bin/python ~/.claude/skills/play-api-read/scripts/play_read.py <cmd> [--package PKG]`
- **기본 앱**: `com.kiwan.quicktodo` (다른 앱은 `--package`로). 그 앱에 서비스 계정 읽기 권한이 있어야 함(없으면 403 → Play Console 사용자/권한에서 부여).

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

스크립트는 구조화 JSON을 stdout으로 낸다. 그대로 덤프하지 말고 **사용자 질문에 답하는 형태로 요약**한다. 예:
- "프로덕션에 versionCode 3 (1.0.1)이 100% 출시 완료(rollout 진행중 아님). 업로드된 AAB는 v2·v3 두 개."
- 리뷰가 `count:0`이면 "현재 API가 반환하는 리뷰 없음"이라고 솔직히. (reviews API는 보통 최근/댓글 있는 리뷰만, 앱에 리뷰가 적으면 비어 있음.)

## 한계 (솔직히 알릴 것)

- **집계 평점(평균 별점)·설치수·크래시·매출 통계는 이 API에 없다.** 그건 Play Console **리포팅 API**(또는 BigQuery export, Pub/Sub) 소관. 사용자가 "평점 추세/설치수" 물으면 androidpublisher로는 못 준다고 말하고, 개별 리뷰(`reviews`)만 제공.
- `reviews.list`는 전체 리뷰 아카이브가 아니라 비교적 최근·댓글 포함 위주. 페이지네이션은 `--token`(출력의 `nextToken`).
- **스크린샷·아이콘은 *언어별 등록정보*에 붙는다 — *앱 버전(versionCode)별*이 아니다.** "버전별 스크린샷"이라는 개념은 Play에 없으니, `images`는 현재 등록된 언어 기준으로 반환한다(`--lang`로 언어 지정). `images`의 `url`은 직접 열어 보거나 다운로드 가능.
- 권한 없는 앱이면 403 — 그 앱에 서비스 계정을 Play Console에서 초대해야 함.

## 쓰기가 필요해지면

이 스킬은 읽기만 한다. 업로드·출시·등록정보 수정은:
- AAB·이미지·등록정보 API 업로드 → `android-app-builder`의 `play_upload.py`
- 콘솔 GUI 작업(앱 최초 생성 등) → `play-store-submit`
