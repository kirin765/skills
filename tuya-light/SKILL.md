---
name: tuya-light
description: Use when the user talks about mood, situation, or comfort in relation to their room light — 기분("i feel blooming"), 독서 환경("신문 읽는데 너무 어둡다"), 프라이버시("불을 밝히면 창밖에 사람이 보일까"), 잠자리, Mac 밖 활동(폰 유튜브·콘솔 게임·종이책). Maps the spoken situation to a Tuya ceiling-light scene or raw brightness/temp/color and applies it via the tuya-light CLI. Also usable for scheduled hold.
---

# tuya-light — 기분·상황 → 조명

천장등(Tuya, 로컬 제어)을 상황·기분에 맞춘다. LAN에서 직접 제어하며 인터넷·클라우드가 필요 없다. 모든 조명 값은 **가정값**이다. 기기 수령 후 `status` 실측으로 보정한다. 이 스킬은 값을 소비할 뿐이고, 보정 작업을 대신하지 않는다.

## 언제 발동

사용자가 조명·밝기·분위기·기분·독서 환경·프라이버시를 언급하며 조명 조정을 원할 때.

- 예: "기분이 blooming이야" / "신문 읽는데 너무 어둡다" / "불 더 밝히면 창밖 사람이 나를 볼 수 있다" / "잘 시간이야" / "폰으로 유튜브 볼게" / "불 꺼줘".

## 절차

1. **현재 상태를 읽는다.** `python3 <repo>/tuya-light/light.py scene`(씬 목록·홀드 상태)과 `status`(현재 DP)를 본다.
2. **의도를 해석한다.** 상황 단서 → 씬/값. 아래 매핑은 제안이다. 값이 이상하면 말하고 사용자 확인을 받는다.
3. **적용 전 한 문장으로 행동을 말한다.** 예: "천장등을 read 씬으로 바꾸고 밝기를 800으로 올립니다."
4. **적용한다.** `light.py scene <이름>` 또는 `brightness/temp/color` 직접 값.
5. **결과를 확인·보고한다.** status 응답을 한두 문장으로 요약한다. 실패하면 원인(IP·키·프로토콜) 한 줄로 보고하고 재시도 루프를 돌지 않는다.

## 상황 → 씬 매핑 (제안, 보정 대상)

| 상황 단서 | 씬/값 | 비고 |
|---|---|---|
| 활기·상승 기분("blooming" 등) | code | 밝고 차가움. 낮 시간 각성 지지(일반 지침) |
| 집중·작업·vibecoding | code | Mac 브라우저 포함(사용자 실측) |
| 독서·신문·수첩 | read | 기본 600/450 |
| "너무 어둡다" (독서 중) | read + 밝기 상향 | 600→800 수준 |
| "너무 밝다"·눈부심 | 밝기 하향 | 400 이하로 |
| 저녁·이완·"잘 시간" | night | 150/200. 필요시 --hold |
| 폰·TV 시청, 콘솔 게임 | youtube / game + --hold | Mac 밖 활동 — 자동 대상 아님 |
| 색 요청("색 바꿔줘") | color <hex> | 밝기 400 이하 권장 |
| 단서 없음 | 적용하지 않는다 | 무엇을 원하는지 물어본다 |

## 제약 해석 (사용자 예시 포함)

- **"reading newspaper, but it's too dark"** → 독서용으로 밝기를 올린다. read 씬 밝기 상향이 기본.
- **"if light is brighter outside the window people could see me"** → 프라이버시 트레이드오프다. 천장등은 방향 조절이 안 되므로, 밝히면 창밖 노출도 커진다. **밝기 상향과 함께 커튼·블라인드를 닫는 것을 제안**하고, 사용자가 고르면 그대로 적용한다.
- 잠자리 전 밝은 빛 → night 권장. 조명은 기분 치료가 아니며, 일반 지침 수준의 효과만 말한다.

## 명령 참조

```
python3 tuya-light/light.py scene                # 씬 목록 + 홀드 상태
python3 tuya-light/light.py scene code           # 씬 적용
python3 tuya-light/light.py scene read --hold 60 # 적용 + 60분 고정(Mac 밖 활동)
python3 tuya-light/light.py scene auto           # 홀드 해제
python3 tuya-light/light.py status               # 현재 DP 스냅샷 (JSON)
python3 tuya-light/light.py brightness 800       # 0~1000
python3 tuya-light/light.py temp 500             # 0~1000, 높을수록 차가움 (가정)
python3 tuya-light/light.py color ff8000         # hex 6자리
python3 tuya-light/light.py set 3 750            # 원시 DP (실측 확정 후에만)
```

경로: `/Users/kiwankim/projects/misc/brain/tuya-light/`. venv가 있으면 `.venv/bin/python light.py`를 쓴다.

## 하지 말 것

- `.env`(DEVICE_ID·IP·LOCAL_KEY)와 `scenes.json`을 사용자 요청 없이 고치지 않는다.
- "설정 누락"으로 실패하면 README 1~3단계(앱 연동·키 수령·.env)를 안내하고 추측으로 넘어가지 않는다.
- 밝기 0~1000, 색온도 0~1000 범위 밖의 값을 쓰지 않는다. 클램프는 CLI가 한다.
- 실패 재시도를 무한히 돌지 않는다. 백오프는 follow.py가 담당한다.
- 조명-기분 효과를 치료 수준으로 말하지 않는다.