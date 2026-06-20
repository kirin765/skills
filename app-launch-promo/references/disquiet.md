# disquiet 프로덕트 + 로그 플레이북 (CDP + Playwright)

disquiet.io는 한국 메이커 커뮤니티다. 신규 앱을 **프로덕트로 등록**하고, 그 위에 **메이커 로그**를 한 개 남긴다.
두 단계다 — `disquiet.io/new-product`에서 프로덕트를 만들고, `disquiet.io/` 홈 작성창에서 로그를 쓰며
"관련 프로덕트"로 방금 만든 프로덕트를 지정한 뒤 **로그 남기기**로 제출한다.

> 셀렉터·라벨은 2026-06-17 실제 DOM 점검 기준. disquiet UI가 바뀔 수 있으니, 스크립트 짜기 전 해당 페이지를
> 한 번 열어 placeholder/버튼 텍스트가 아직 맞는지 확인하고 어긋나면 조정한다.

## 왜 CDP인가 (엔진 예외)

app-launch-promo의 다른 채널과 달리 **disquiet만 CDP+Playwright(포트 9222)**로 돈다.
이유: (a) 프로덕트 등록의 로고/스크린샷 업로드는 file chooser/`set_input_files`로 결정적으로 처리되고
(확장의 file_upload는 Claude 생성파일을 자주 거부), (b) 로그 본문이 contenteditable이라 붙여넣기 대신
`keyboard.insert_text`가 필요하며, (c) "관련 프로덕트"가 자체 드롭다운이라 코드로 다뤄야 안정적이다.

## 사전 조건

1. **CDP 살아있는지** — `curl -s http://localhost:9222/json/version`. 없으면 멈추고 사용자에게 Chrome을
   `--remote-debugging-port=9222`로 띄워달라고 요청.
2. **로그인 계정 확인** — `disquiet.io`로 가서 로그인 상태 확인. 신호는 헤더의 **"포스트 작성" + 본인 핸들**
   노출(점검 시점 관찰된 계정 = **hello765**). 페이지에 "로그인/회원가입"만 보이면 로그아웃 — 진행하지 말고
   리포트에 "계정 불일치/로그아웃 — 건너뜀". 자동 로그인 시도 금지. (계정은 환경마다 다를 수 있으니 런타임 확인.)
3. **기존 프로덕트 확인** — "관련 프로덕트" 드롭다운(아래 B-2)에 이미 같은 앱이 있으면 A를 건너뛰고 재사용한다.
   중복 등록하지 않는다.

## 입력 (스킬이 초안 생성)

사용자는 보통 **앱 이름 + 스토어/랜딩 URL**만 준다(있으면 로고·스크린샷 경로도). 나머지는 스킬이 초안으로 쓴다:

- **한 줄 소개(태그라인)** — 가장 강한 한 문장. 마케팅 과장 없이 무엇을 해결하는지.
- **설명** — 2~4문장: 왜 만들었는지 + 핵심 기능 + 누구를 위한 것인지.
- **로그 본문** — 메이커 회고체. `copy-guidelines.md`의 disquiet 톤(출시 소식 + 무엇을·왜 만들었는지 +
  기능 1~3개 + 링크). 광고 카피 아님, "막 ~를 출시했어요 🎉" 류의 1인칭 회고.

초안을 만들면 **제출 전에 전부 transcript에 출력**한다(app-launch-promo 가시성 규칙 — 블로킹 확인이 아니라
무엇이 나가는지 눈으로 보게 하는 것).

## 실행 형태 — 단발 스크립트

`/tmp/disquiet/run-<stamp>.py`에 단발 스크립트를 만들어 실행한다. 파일명에 `inspect.py` 같은
**stdlib 모듈명을 쓰지 말 것**(circular import). 모듈 구조 잡지 말고 단발로.

```python
import asyncio
from playwright.async_api import async_playwright
CDP = "http://localhost:9222"

async def main():
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(CDP)
    context = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = next((p for p in context.pages if "disquiet.io" in p.url), None) or await context.new_page()
    try:
        ...   # Phase A → Phase B
    finally:
        await pw.stop()   # browser.close() 금지 — 사용자의 평소 Chrome을 닫아버린다

asyncio.run(main())
```

## Phase A — 프로덕트 등록 (`/new-product`, **2단계 위저드**)

페이지 제목은 "프로덕트 공유하기". 하단에 단계 인디케이터 `1` `2`가 있는 **2-스텝 폼**이다.
텍스트 필드엔 **label/name/data-testid가 없고 placeholder만 있다** → `get_by_placeholder`로 잡는다.

### Step 1 — 기본 정보

```python
await page.goto("https://disquiet.io/new-product", wait_until="domcontentloaded", timeout=25000)
await page.wait_for_timeout(2500)
await page.get_by_placeholder("예시 - 디스콰이엇").fill(app_name)                       # 프로덕트 이름
await page.get_by_placeholder("예시 - 메이커를 위한 소셜 네트워크").fill(tagline)         # 한 줄 소개
await page.get_by_placeholder("예시 - https://disquiet.io").fill(website_url)           # 웹사이트 링크
await page.get_by_placeholder("예시 - https://apps.apple.com/kr/app/disquiet").fill(app_store_url)  # 있을 때만
await page.get_by_placeholder("예시 - https://play.google.com/store/apps/disquiet").fill(play_url)  # 있을 때만
await page.locator("textarea").first.fill(description)    # "프로덕트에 대한 자세한 설명*" (필수)
```

- **토픽\* (필수, 최대 3개)** — chip/드롭다운(▼) 셀렉터. 드롭다운을 열어 앱 성격에 맞는 토픽 1~3개를 고르면
  `💰 금융 ×` 같은 칩으로 붙는다. 필수라 최소 1개 선택해야 다음으로 넘어간다. (placeholder는 "프로덕트
  토픽을 선택해주세요.")
- **썸네일 이미지\* (필수)** — Step 2의 갤러리와 **별개**인 단일 대표 이미지(추천 240×240, JPG/PNG/GIF ≤10MB).
  "이미지 업로드하기" 링크 클릭 → file chooser. 없으면 등록 불가하니 app-launch-promo가 넘긴 아이콘/썸네일을 쓴다.
  ```python
  async with page.expect_file_chooser() as fc:
      await page.get_by_text("이미지 업로드하기").click()   # Step 1에서는 이 텍스트 = 썸네일 업로더
  await (await fc.value).set_files("/path/thumb.png")
  ```
- **다음 단계로** — Step 1 하단의 **"추가 정보"** 버튼을 눌러 Step 2로 간다.
  ```python
  await page.get_by_text("추가 정보", exact=False).last.click()
  ```

### Step 2 — 갤러리 이미지 · 영상 · 메이커 정보

확인된 필수/선택 필드:

- **갤러리 이미지\* (필수)** — 추천 1200×900, **최대 5개**. "이미지 업로드하기" 영역. 정적 `input[type=file]`이
  없어 영역 클릭 → file chooser로 넣는다. **필수라 최소 1장 없으면 등록이 막힌다** — app-launch-promo가
  넘긴 스크린샷/썸네일을 쓴다. 이미지가 하나도 없으면 등록을 진행하지 말고 사용자에게 요청한다.
  ```python
  async with page.expect_file_chooser() as fc:
      await page.get_by_text("이미지 업로드하기").click()   # Step 2에서는 이 텍스트 = 갤러리 업로더
  await (await fc.value).set_files(["/path/shot1.png", "/path/shot2.png"])   # ≤5장
  ```
- **YouTube 소개 영상 (선택)** — placeholder `예시 - https://youtu.be/...`. app-launch-promo의 YouTube
  업로드 단계에서 받은 watch URL이 있으면 넣는다.
  ```python
  await page.get_by_placeholder("예시 - https://youtu.be/SYvmPcODEZo").fill(youtube_url)  # 있으면
  ```
- **메이커 정보\* (필수)** — 라디오 2개: `제가 / 우리 팀이 만들었어요` vs `좋아서 공유해요`. 본인 앱이므로
  **"제가 / 우리 팀이 만들었어요"**를 선택한다.
  ```python
  await page.get_by_text("제가 / 우리 팀이 만들었어요").click()
  ```
- **등록 제출** — 최종 CTA는 **"프로덕트 공유하기"**. 누르기 전에 채운 필드(이름·태그라인·링크·이미지 수·
  메이커 정보)를 transcript에 출력한다(비가역).
  ```python
  await page.get_by_text("프로덕트 공유하기", exact=False).last.click()
  ```
- 등록 후 **프로덕트 이름·URL을 캡처**. B-2에서 이 이름으로 드롭다운에서 고른다.

## Phase B — 메이커 로그 작성 (`disquiet.io/` 홈)

로그 컴포저는 홈 피드 상단에 **인라인**으로 있다(별도 모달 아님). 버튼 텍스트(점검 확인): `새 로그`(탭),
`관련 프로덕트`, `로그 남기기`(← **띄어쓰기 있음**, "로그남기기" 아님).

1. **본문 입력** — 본문은 contenteditable. 클릭해 포커스 후 `insert_text`(붙여넣기 X):
   ```python
   await page.goto("https://disquiet.io/", wait_until="domcontentloaded", timeout=25000)
   await page.wait_for_timeout(2500)
   ce = page.locator('[contenteditable="true"]').first
   await ce.click()
   await page.keyboard.insert_text(log_body)
   ```
2. **관련 프로덕트 = 방금 만든 프로덕트** — `관련 프로덕트` 버튼을 누르면 **내 프로덕트 목록 드롭다운**이
   뜬다(로고+이름 행들, 검색창 없음). 그 안에서 방금 만든 프로덕트 **이름 행을 클릭**한다.
   ```python
   await page.get_by_role("button", name="관련 프로덕트").first.click()
   await page.wait_for_timeout(1200)                       # 드롭다운 로드
   await page.get_by_text(app_name, exact=True).first.click()   # 정확 일치 행 선택
   ```
   드롭다운에 그 프로덕트가 안 보이면(방금 등록이 아직 반영 안 됨) 잠깐 기다렸다 다시 열거나, 홈을 새로고침한 뒤
   재시도. **엉뚱한 프로덕트 선택 금지** — 부분일치 주의, 정확 이름으로.
3. **연결 확인** — 선택 후 컴포저에 그 프로덕트 칩/이름이 붙었는지 확인. 안 붙었으면 **로그 남기기를 누르지 말고**
   멈춰 사용자에게 보고(엉뚱한 프로덕트로 로그가 나가는 것보다 멈추는 게 낫다).
4. **제출** — 본문 + 연결된 프로덕트명을 한 번 출력(가시성)한 뒤, 한 번만 누른다(비가역, 중복 클릭 금지):
   ```python
   await page.get_by_role("button", name="로그 남기기").click()
   ```
5. 게시 후 **로그 URL을 캡처**해 리포트에 싣는다.

## 실패·안전 규칙

- **disquiet 에러 = 무시하고 전진(재시도 금지)** → disquiet은 발행/수정/삭제 요청이 실제로는 처리됐는데도
  거의 항상 에러 토스트/응답을 띄운다(고질). CDP·Claude in Chrome 어느 엔진이든 **제출 액션을 한 번 보냈으면
  에러가 떠도 그 동작은 성공한 것으로 간주하고 다음 단계로 넘어간다.** 절대 같은 제출을 재시도하지 않는다 —
  재시도는 **중복 프로덕트/중복 로그**를 만든다. 결과는 에러 메시지가 아니라 **URL 캡처 / `page.reload()` 후
  목록·드롭다운에 반영됐는지**로만 확인한다. (단, 액션을 *보내기도 전*에 난 에러 — 셀렉터 못 찾음, 로그인 만료 —
  는 진짜 실패이므로 이 규칙 밖이다.)
- **계정 불일치/로그아웃** → 등록·로그 모두 건너뛰고 기록. 비번 자동입력·자동 로그인 금지.
- **중복 방지** → "관련 프로덕트" 드롭다운에 이미 있으면 새로 만들지 않고 그걸 재사용. 로그 남기기는 한 번만.
- **관련 프로덕트 미연결** → 칩이 안 보이면 제출 보류하고 사용자에게 알린다.
- **이미지 업로드 영역 못 찾음** → 이미지 단계만 건너뛰고 텍스트 등록은 계속. 리포트에 "이미지 수동 첨부 필요"로 표시.
- **점검 시 draft 남김 주의** → 본문을 테스트로 입력했으면 게시하지 말고 `page.reload()`로 폐기.
- `browser.close()` 절대 금지(사용자 Chrome 종료). 종료는 `pw.stop()`만.
