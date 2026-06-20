# Play Developer Publishing API — 무인 업로드 (Chrome 파일피커 우회)

Chrome(Claude in Chrome)로는 AAB·이미지 업로드가 안전계층에 의해 영구 차단된다(`references/play-submit.md` "업로드 자동화 시도 금지 목록"). 우회는 **브라우저를 안 쓰는** Google Play Developer Publishing API(`androidpublisher` v3) — 서비스 계정으로 REST 호출만 한다.

## 무엇이 자동화되나 / 무엇이 안 되나

| 동작 | API | 비고 |
|------|-----|------|
| 앱 **최초 생성** | ❌ 수동(콘솔) | 패키지명·기본언어·앱/게임·무료 선언은 콘솔에서만. 생성 직후 Play App Signing은 자동 활성됨 |
| **맨 처음 AAB** | ✅ `edits.bundles.upload` + **`releaseStatus: "draft"`** | 미게시(draft) 앱은 릴리스 status가 `completed`면 validate가 `Only releases with status draft may be created on draft app`로 실패 — `"releaseStatus": "draft"`를 주면 통과 (2026-06 norebang에서 실증) |
| 이후 **새 버전 AAB** | ✅ `edits.bundles.upload` | 게시된 앱은 `completed` 기본값 그대로 |
| 아이콘·피처그래픽·스크린샷 | ✅ `edits.images.upload` | imageType: `icon`,`featureGraphic`,`phoneScreenshots` 등 |
| 등록정보 제목/간단/자세한 설명(언어별) | ✅ `edits.listings.update` | ko-KR, en-US 각각 |
| **프로모션 동영상**(YouTube URL, 언어별) | ✅ `edits.listings.update`의 `video` | config `listings.<lang>.video`. 생략 시 기존 동영상이 지워짐(update는 전체 교체) |
| 트랙 배정·출시 | ✅ `edits.tracks.update` | production 등 |
| **출시노트**(언어별) | ✅ `edits.tracks.update`의 `releases[].releaseNotes` | config `releaseNotes`(ko/en)로. AAB 올릴 때 함께 |
| **검토 제출(커밋)** | ✅ `edits.commit` | **제출=API.** 비가역 — 사용자 "출시까지" 명시 때만 |

**결론:** 콘솔(CDP) 수동은 **API에 엔드포인트가 없는 신규-앱 셋업 3가지뿐 — ① 앱 최초 생성 ② 콘텐츠 선언 10개 ③ 카테고리.** 그 외 **업로드·이미지·등록정보·트랙·출시노트·검토 제출은 전부 이 API로** 무인 처리한다(첫 AAB는 `releaseStatus: "draft"` 필수). 특히 **검토 제출(=제출)은 `edits.commit`으로 API에서 끝난다 — 콘솔로 가지 말 것.** 앱 *업데이트*는 100% 무인. 수동/콘솔 폴백은 API가 실제로 실패(403 등)할 때만.

## 셋업 상태 (이 머신, 확정값)

- **서비스 계정 키**: `~/.config/play-publisher/sa.json` (chmod 600, git 커밋 금지)
- **서비스 계정 이메일**: `play-publisher@claude-for-android.iam.gserviceaccount.com`
- **GCP 프로젝트**: `claude-for-android` (dev 계정 happylife2080100@gmail.com, authuser=1)
- **실행 venv**: `~/.config/play-publisher/venv/bin/python` (google-api-python-client + google-auth 설치됨)
- **인증**: 키로 androidpublisher 토큰 발급
- **셋업 절차**: API 활성화·서비스 계정·키·Play Console 연결은 `references/google-cloud-setup.md` 참조(Claude in Chrome 1회).

### 사용자/콘솔이 필요한 1회 액션 (접근권한 — Claude in Chrome로 수행, 상세는 google-cloud-setup.md)

1. **Play Console → 설정 → API 액세스**: GCP 프로젝트 `claude-for-android`를 **연결**(link). "기존 프로젝트 연결".
2. **사용자 및 권한 → 새 사용자 초대**: `play-publisher@claude-for-android.iam.gserviceaccount.com` 초대 → 앱별(또는 계정 전체) **"릴리스 관리/프로덕션 출시·스토어 등록정보 편집"** 권한 부여.
3. 완료되면 `edits.insert`가 200으로 바뀐다(아래 스크립트가 자동 확인).

이게 끝나기 전엔 모든 업로드가 403이므로, 그때까진 첫 AAB뿐 아니라 전부 `references/play-submit.md`의 수동 핸드오프로 폴백.

## 업로더 스크립트 (작성 완료)

`scripts/play_upload.py` — edit 하나로 AAB·이미지·등록정보·트랙을 묶어 올린다. 설정은 `scripts/app-config.example.json` 형식의 JSON.

```bash
# dry run (검증 후 edit 폐기 — 아무것도 반영 안 됨)
~/.config/play-publisher/venv/bin/python \
  ~/.claude/skills/android-app-builder/scripts/play_upload.py --config <app>.json
# 실제 반영 + 검토 제출 (비가역, "출시까지" 명시 때만)
… --config <app>.json --commit
```

설정 JSON: `packageName`, `aab`(버전 올릴 때), `images`(icon/featureGraphic/phoneScreenshots), `listings`(ko-KR/en-US, aso-audit 카피), `track`, `releaseStatus`(**신규 미게시 앱의 첫 AAB면 반드시 `"draft"`**; 생략 시 `completed`). 이미지는 imageType별로 전량 교체(deleteall→upload).

## 업로드 흐름 (edits 트랜잭션)

모든 변경은 edit 하나로 묶어 마지막에 commit:

```
edit = androidpublisher.edits.insert(packageName)        # editId 발급
edits.bundles.upload(editId, app-release.aab)            # 새 버전이면
edits.images.upload(editId, imageType="icon", icon.png)
edits.images.upload(editId, imageType="featureGraphic", feature.png)
edits.images.upload(editId, imageType="phoneScreenshots", framed/01.png … 08.png)  # 반복
edits.listings.update(editId, lang="ko-KR", title/shortDescription/fullDescription)
edits.listings.update(editId, lang="en-US", …)
edits.tracks.update(editId, track="production", releases=[{versionCodes,status:"completed"}])  # 미게시 앱 첫 AAB는 status:"draft"
edits.commit(editId)        # ← 검토 제출(비가역). "출시까지" 아니면 여기서 멈추고 사용자 확인
```

`phoneScreenshots`는 같은 imageType으로 여러 번 upload(2~8장). 교체 시 `edits.images.deleteall` 후 재업로드.

## 구현 메모

- 언어: 아무 거나. Node면 `googleapis`(`google.androidpublisher('v3')`), Python이면 `google-api-python-client`. 인증은 서비스 계정 JSON으로 `google.auth`.
- 입력 에셋은 2단계 산출(`~/Downloads/<app>-store-assets/` 또는 `framed/`)을 그대로 쓴다.
- 등록정보 텍스트는 `aso-audit` 결과(ko/en)를 그대로 넣는다.
- commit 전에 `edits.validate`로 점검 가능.
- 이 경로를 쓰면 `references/play-submit.md`의 Chrome 클릭 워크플로우 대부분이 불필요해진다. 콘솔이 꼭 필요한 건 **API에 엔드포인트가 없는 3가지 — 앱 최초 생성·콘텐츠 선언 10개·카테고리뿐**이고, 첫 AAB·출시노트·검토 제출을 포함한 모든 업로드/제출은 API로 한다(신규 앱은 `releaseStatus: "draft"`). draft 릴리스에 출시노트(`releaseNotes`)를 붙이고 검토로 보내는 것까지 `play_upload.py … --commit` 한 방으로 끝낸다 — 콘솔의 "게시 개요 → 전송" 단계로 가지 말 것.
- **국가/지역**: `edits.tracks.update`의 `countryTargeting`으로 API 시도 가능. 신규 앱 첫 게시에서 API가 막히면 그때만 콘솔에서 추가.
