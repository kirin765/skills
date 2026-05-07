# 네이버 Open API (블로그 검색) 설정 가이드

네이버 검색 API 의 블로그 카테고리를 사용하려면 Client ID/Secret 발급이 필요하다.
공식 문서: https://developers.naver.com/docs/serviceapi/search/blog/blog.md

## 1. 키 발급 (이미 있으면 건너뛰기)

1. https://developers.naver.com/apps/#/register 접속 (네이버 로그인 필요)
2. "애플리케이션 등록" → "사용 API" 에서 **검색** 체크
3. 비로그인 오픈 API 서비스 환경 → "WEB 설정" → 사용 URL 입력 (`http://localhost` 면 충분)
4. 등록 완료 후 Client ID + Client Secret 확인

쿼터: 일 25,000건 (블로그 검색 기준).

## 2. 키 저장 — 두 가지 방법 중 택 1

### 방법 A. 환경변수 (권장)

쉘 설정 파일 (`~/.zshrc`, `~/.bashrc` 등) 에 추가:

```bash
export NAVER_OPEN_API_CLIENT_ID="발급받은_client_id"
export NAVER_OPEN_API_CLIENT_SECRET="발급받은_client_secret"
```

새 터미널 세션부터 적용. 즉시 적용은 `source ~/.zshrc`.

### 방법 B. 자격 정보 파일

`~/.naver_api_credentials` 파일 생성 (홈 디렉토리, 파일 이름 정확히):

```
NAVER_OPEN_API_CLIENT_ID=발급받은_client_id
NAVER_OPEN_API_CLIENT_SECRET=발급받은_client_secret
```

그 후 권한 제한:

```bash
chmod 600 ~/.naver_api_credentials
```

## 3. 동작 확인

```bash
python scripts/scrape_naver_blog.py --queries "엑셀" --days 7 --output-dir /tmp/test_nb --max-per-query 5
```

처음에 `[mode] open_api` 가 찍히면 키 적용 성공. `[mode] html` 이면 키를 못 읽은 것 — 환경변수 또는 파일 위치·이름·권한 다시 확인.

## 4. 키 없이 쓰는 경우

키가 없으면 자동으로 `search.naver.com` HTML 파싱으로 fallback. 단점:

- 응답 안정성 ↓ (네이버 마크업이 자주 바뀜)
- 결과 메타가 빈약 (제목·링크·발췌만, 정확한 발행일 추출 어려움)
- rate limit 쪽이 더 빡빡함

가능하면 Open API 키를 발급받아 쓰는 쪽이 안정적.

## 5. 보안 주의사항

- Client ID/Secret 을 git 커밋·공유 문서에 절대 포함 금지
- skill 스크립트 안에 하드코딩 금지 (이 skill 의 스크립트는 환경변수 → 자격 정보 파일 순으로 읽어옴 — 하드코딩 안 함)
- 키가 노출됐으면 즉시 https://developers.naver.com/apps/ 에서 재발급
