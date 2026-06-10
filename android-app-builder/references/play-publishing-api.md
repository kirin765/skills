# Play Developer Publishing API — 무인 업로드 (Chrome 파일피커 우회)

Chrome(Claude in Chrome)로는 AAB·이미지 업로드가 안전계층에 의해 영구 차단된다(play-store-submit "업로드 자동화 시도 금지 목록"). 우회는 **브라우저를 안 쓰는** Google Play Developer Publishing API(`androidpublisher` v3) — 서비스 계정으로 REST 호출만 한다.

## 무엇이 자동화되나 / 무엇이 안 되나

| 동작 | API | 비고 |
|------|-----|------|
| 앱 **최초 생성** + **맨 처음 AAB 1개** | ❌ 수동 | 패키지 존재 + Play App Signing 설정이 이때만 콘솔에서 잡힘([확인됨](https://developers.google.com/android-publisher/api-ref/rest/v3/edits.bundles/upload)) |
| 이후 **새 버전 AAB** | ✅ `edits.bundles.upload` | |
| 아이콘·피처그래픽·스크린샷 | ✅ `edits.images.upload` | imageType: `icon`,`featureGraphic`,`phoneScreenshots` 등 |
| 등록정보 제목/간단/자세한 설명(언어별) | ✅ `edits.listings.update` | ko-KR, en-US 각각 |
| 트랙 배정·출시 | ✅ `edits.tracks.update` | production 등 |
| 검토 제출(커밋) | ✅ `edits.commit` | 비가역 — 사용자 "출시까지" 명시 때만 |

**결론:** 신규 앱은 *맨 처음 AAB 한 개*만 콘솔 수동(이때 play-store-submit의 핸드오프 사용), 그 외 이미지·등록정보·이후 버전은 전부 이 API로 무인 처리. 앱 *업데이트*는 100% 무인.

## 셋업 상태 (이 머신, 확정값)

- **서비스 계정 키**: `~/.config/play-publisher/sa.json` (chmod 600, git 커밋 금지)
- **서비스 계정 이메일**: `claude-google-play@claude-android-upload.iam.gserviceaccount.com`
- **GCP 프로젝트**: `claude-android-upload`
- **실행 venv**: `~/.config/play-publisher/venv/bin/python` (google-api-python-client + google-auth 설치됨)
- **인증**: 키로 androidpublisher 토큰 발급 ✅ 검증됨
- **Play Console 연결/권한**: ⛔ **아직 미완료** (`edits.insert` → HTTP 403). 아래 사용자 액션 필요.

### 사용자가 직접 해야 하는 1회 액션 (접근권한 변경 — Claude 불가)

1. **Play Console → 설정 → API 액세스**: GCP 프로젝트 `claude-android-upload`를 **연결**(link). 처음이면 "기존 프로젝트 연결".
2. **사용자 및 권한 → 새 사용자 초대**: `claude-google-play@claude-android-upload.iam.gserviceaccount.com` 초대 → 앱별(또는 계정 전체) **"릴리스 관리/프로덕션 출시·스토어 등록정보 편집"** 권한 부여.
3. 완료되면 `edits.insert`가 200으로 바뀐다(아래 스크립트가 자동 확인).

이게 끝나기 전엔 모든 업로드가 403이므로, 그때까진 첫 AAB뿐 아니라 전부 `play-store-submit` 수동 핸드오프로 폴백.

## 업로더 스크립트 (작성 완료)

`scripts/play_upload.py` — edit 하나로 AAB·이미지·등록정보·트랙을 묶어 올린다. 설정은 `scripts/app-config.example.json` 형식의 JSON.

```bash
# dry run (검증 후 edit 폐기 — 아무것도 반영 안 됨)
~/.config/play-publisher/venv/bin/python \
  ~/.claude/skills/android-app-builder/scripts/play_upload.py --config <app>.json
# 실제 반영 + 검토 제출 (비가역, "출시까지" 명시 때만)
… --config <app>.json --commit
```

설정 JSON: `packageName`, `aab`(새 버전일 때만), `images`(icon/featureGraphic/phoneScreenshots), `listings`(ko-KR/en-US, aso-audit 카피), `track`. 이미지는 imageType별로 전량 교체(deleteall→upload).

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
edits.tracks.update(editId, track="production", releases=[{versionCodes,status:"completed"}])
edits.commit(editId)        # ← 검토 제출(비가역). "출시까지" 아니면 여기서 멈추고 사용자 확인
```

`phoneScreenshots`는 같은 imageType으로 여러 번 upload(2~8장). 교체 시 `edits.images.deleteall` 후 재업로드.

## 구현 메모

- 언어: 아무 거나. Node면 `googleapis`(`google.androidpublisher('v3')`), Python이면 `google-api-python-client`. 인증은 서비스 계정 JSON으로 `google.auth`.
- 입력 에셋은 2단계 산출(`~/Downloads/<app>-store-assets/` 또는 `framed/`)을 그대로 쓴다.
- 등록정보 텍스트는 `aso-audit` 결과(ko/en)를 그대로 넣는다.
- commit 전에 `edits.validate`로 점검 가능.
- 이 경로를 쓰면 play-store-submit의 Chrome 클릭 워크플로우 대부분이 불필요해진다. 단 **최초 앱 생성 + 첫 AAB**는 여전히 콘솔에서 사용자 수동 → 그 부분만 play-store-submit 핸드오프를 쓰고, 나머지(이미지·등록정보·이후 버전)는 API로 넘긴다.
