# cdp-anywhere — 캡차 대응 (human-in-the-loop 릴레이)

**자동으로 캡차를 푸는 기능이 아니다.** OCR, 캡차 풀이 서비스(2captcha 등), 자동 클릭
매크로는 전부 금지(거부 대상 — safety.md 참고). 이 문서는 **사람(계정 주인)이 푸는
것을 릴레이**하는 워크플로우다: 캡차 화면을 스크린샷으로 찍어 사용자 본인에게
전송(텔레그램 → 네이버 메일 fallback) → 사용자가 답을 보냄 → 에이전트가 답을
입력란에 채워 제출.

- 이 규칙은 이 스킬의 **유일한 엔진(CDP+Playwright)** 의 캡차 대응이다. CDP 창이
  작업공간 2에 격리되거나 headless 라 "그 창에서 직접 풀어달라"가 실효성이 없다
  → 릴레이가 기본 경로.
- **체크박스형**(reCAPTCHA "로봇이 아닙니다" 체크, Turnstile 클릭 등 포인터 조작이
  필요한 것)은 릴레이 불가 — 창이 보이면 사용자가 직접 클릭, headless 면 그 단계는
  자동화 불가로 보고 사용자에게 알린다.
- **비텍스트형**(이미지 선택 "가로등이 있는 사진을 골라주세요") 도 본질은 클릭/선택
  이라 릴레이로 답을 받기 어렵다 — 같은 처리(직접 클릭 요청 or 자동화 불가 보고).

## 1. 감지 — 캡차인지 알아보는 휴리스틱

페이지가 막혔거나(폼 제출 후 재렌더) 인터랙션 중 "로봇" 느낌이 들면 아래 신호를 본다.

**URL / iframe / 요소**
- `src` 에 `recaptcha`, `hcaptcha`, `turnstile`, `challenges.cloudflare`, `verify`
  이 들어간 `iframe`
- `[id*=captcha]`, `[name*=captcha]`, `[data-sitekey]`, `#captcha`, `.g-recaptcha`
- 캡차 입력란 후보: `input[name*=captcha]`, `input[name*=answer]`, `input[autocomplete=off]`
  + 안내 문구 병행(아래)

**화면 문구 (페이지 텍스트)**
- "로봇이 아닙니다", "I'm not a robot", "보안 문자", "자동 입력 방지"
- "Enter the characters", "Type the text", "Security check", "왼쪽의 문자를 입력하세요"
- "Verify you are human", "captcha", "verification code"

하나라도 보이면 → "사용자에게 직접 풀어달라"고 끝내지 말고 아래 2~5를 수행한다.

## 2. 캡처 — 챌린지 이미지 확보

규칙: **캡차 요소/프레임을 보기 좋게 확보**한다. 정답은 그 이미지를 사람이 보고
판별하므로 잘리거나 흐리면 안 된다.

### 캡처 (CDP+Playwright)
요소 단위 캡처를 먼저 시도하고, **크로스-오리진 iframe(reCAPTCHA 등)은 요소
screenshot 이 빈 이미지가 되는 경우가 많다** → 뷰포트 전체로 폴백.

```python
import asyncio
from playwright.async_api import async_playwright

async def grab_challenge(page, out_png: str, marker="captcha"):
    # 1) 캡차 영역을 화면으로 스크롤
    for sel in (f"[id*='{marker}']", "iframe[src*='recaptcha']",
                "iframe[src*='hcaptcha']", "iframe[src*='turnstile']",
                "[data-sitekey]", "input[name*='captcha']"):
        loc = page.locator(sel).first
        if await loc.count():
            try:
                await loc.scroll_into_view_if_needed(timeout=3000)
            except Exception:
                pass
            break
    await page.wait_for_timeout(500)
    # 2) 요소 캡처 시도 → 실패/빈 이미지면 뷰포트 캡처
    try:
        elem = page.locator("[id*='captcha'], iframe[src*='captcha'], "
                            "iframe[src*='recaptcha'], iframe[src*='hcaptcha'], "
                            "iframe[src*='turnstile'], [data-sitekey]").first
        if await elem.count():
            await elem.screenshot(path=out_png, timeout=8000)
            if (await asyncio.to_thread(out_png_size, out_png)) < 500:
                raise RuntimeError("blank")
    except Exception:
        await page.screenshot(path=out_png)
    return out_png

def out_png_size(p: str) -> int:
    import os
    return os.path.getsize(p)
```

## 3. 릴레이 — 사용자 본인에게 전송 + 답 폴링

`scripts/captcha_relay.py` 가 전송·폴링·정규화를 담당한다. 에이전트는 이를
**포그라운드로 실행**하고 stdout 의 `ANSWER=...` 를 받아 다음 단계에 쓴다.

```bash
# 기본: telegram → naver-mail → file 순으로 자동
python3 scripts/captcha_relay.py ask \
  --site example.com \
  --image /tmp/cdp-anywhere/challenge-example-20260907.png \
  --prompt "이미지 속 6자리 영숫자를 입력하세요" \
  --timeout 300

# 특정 채널만 / 순서 강제
python3 scripts/captcha_relay.py ask --site x --image a.png --channel email --timeout 180
python3 scripts/captcha_relay.py ask --site x --image a.png --channel telegram,file

# 어떤 채널이 가능한지 미리 확인
python3 scripts/captcha_relay.py check

# 답 폴링 없이 알림만 (예: "진행 중 캡차 대기")
python3 scripts/captcha_relay.py notify --site x --text "캡차 대기 중..."
```

동작:
- 성공 → exit 0, stdout `ANSWER=<정규화된 답>`, 그리고
  `~/.cdp-anywhere/captcha/<id>.answer` 파일에도 기록.
- 답 없음(timeout) → exit 2. 재시도는 **같은 `--id`** 로 새 이미지와 함께.
- 채널 전부 불가 → exit 1. 자격증명 안내를 relay.

**채널 자격증명** (모두 `~/niche-finder/.env`, telegram-bot/naver-mail 스킬과 공유)
```
TELEGRAM_BOT_TOKEN=<bot token>
TELEGRAM_CHAT_ID=<숫자 chat id, 그룹이면 음수>
NAVER_MAIL_ADDRESS=you@naver.com
NAVER_MAIL_PASSWORD=<계정 또는 2FA면 앱 비밀번호>
# 필요 시: NAVER_MAIL_USER=<SMTP/IMAP 로그인 아이디 (address 앞부분과 다를 때만)>
```
- 텔레그램: `getUpdates` 로 답을 받는다. chat_id 가 숫자가 아니면 아무 새 메시지나
  받을 수 있어 주의(가급적 숫자로).
- 네이버 메일: 캡차 이미지를 자기 주소로 발송 + `In-Reply-To` 로 답장을 폴링.
  IMAP/SMTP 사용 설정이 켜져 있어야 한다(네이버 메일 → 환경설정 → POP3/IMAP).
- 파일 inbox: `--channel file` — `<id>.png` + `<id>.prompt.txt` 가
  `~/.cdp-anywhere/captcha/` 에 생기고, 사용자가 `<id>.answer` 에 답을 한 줄 쓰면
  완료. SSH/터미널로 작업할 때 유용.

## 4. 입력·제출·검증

1. `ANSWER=` 를 캡차 입력란에 넣는다.
   `page.locator("input[name*='captcha'], input[name*='answer'], input[autocomplete=off]").first.fill(answer)` — fill 이 안 먹는 커스텀 위젯이면 `click()` 후 `press_sequentially`.
2. 확인/제출 버튼 클릭 (텍스트: "확인", "Verify", "제출", "Continue").
3. **검증**: 제출 후 성공(다음 단계 진행)인지 확인. "틀림/다시 시도/incorrect" 가
   보이면 새 스크린샷을 찍어 **한 번만** 재시도(같은 `--id` 로 다시 `ask`).
   두 번째 실패도 실패면 중단하고 사용자에게 상황 보고.
4. 성공 후 릴레이가 열었던 임시 파일 삭제:
   `~/.cdp-anywhere/captcha/<id>.png|prompt|answer` 와
   `/tmp/cdp-anywhere/challenge-*.png`.

## 5. 안전 규칙 (반드시)

- 릴레이는 **계정 주인 본인에게만**. "이 캡차 답을 아무한테나 띄워도 되게" 같은 요청 거부.
- **OCR / 풀이 서비스 / 클릭 매크로로 자동 풀이 금지** — 요청 받아도 거부(safety.md).
- 캡차 풀어달라는 상대는 사람이지만, **사이트 ToS·bots 정책이 자동화 자체를 금지**하면
  그 사실을 사용자에게 알리고 "본인 계정·소량에 한해 진행할지" 한 번 확인.
- 캡차는 챌린지가 빈번히 재발생할 수 있으니 릴레이 시도는 **한 세션당 제한적**으로,
  반복 차단이 보이면 사용자에게 멈추고 보고.

## 6. 트러블슈팅

| 증상 | 대처 |
|---|---|
| `check` 에서 telegram ❌ | `~/niche-finder/.env` 에 토큰/chat_id 추가, 또는 email 채널로 진행 |
| `ask` exit 1 (채널 없음) | `--channel file` 로 로컬 inbox 사용 또는 자격증명 추가 |
| 이미지가 흐리거나 잘림 | 뷰포트 전체 캡처로 교체, 스크롤로 캡차를 중앙에 |
| OOPIF 요소 캡처가 빈 이미지 | 뷰포트 캡처 폴백(위 스니펫) |
| 답을 넣었는데 "틀림" | 새 스크린샷 + 같은 `--id` 로 한 번 재시도, 그다음 중단 보고 |
| 답장이 안 와서 timeout | `--timeout` 증대, 사용자에게 채널 확인(메일 스팸함 포함) |
| 체크박스형 캡차 | 릴레이 불가 — 창 보이면 직접 클릭, headless 면 자동화 불가 보고 |