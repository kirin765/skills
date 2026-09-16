---
name: kiwoom-trade-api
description: Use when the user wants to use their own Kiwoom (키움증권) account via the official REST API — 시세/차트/잔고/예수금 조회, 매수·매도 주문, 자동매매(paper/demo/live), 백테스트. Triggers: "키움 API", "키움 주문/잔고/시세/차트", "자동매매", "auto trading", "kiwoom", "모의투자/실전 계좌", "KODEX/ETF 시세", "005930/069500 조회". Auth is pre-configured via `kiwoomcli setup` (macOS keychain). GOTCHA — 모의(demo) 키와 실전(real) 키는 서로 다르고 교차 호출 시 8030으로 거부된다. 실전 주문은 게이트(2026-09-12, demo 검증 통과) 전 금지. 모의 서버는 API별 유량 1건/초(1700·429)를 강제한다.
---

# 키움 REST API — 조회·주문·자동매매

키움증권이 개인 고객에게 무료로 여는 REST API(2025-03 출시). 본인 계좌의 시세·차트·잔고를 읽고, 주문을 내고, 자동매매 시스템을 돌리는 스킬.

## ⚠️ 핵심 규칙 (이 스킬의 안전장치 — 순서대로)

1. **실전 주문은 게이트(2026-09-12) 통과 전 금지.** 게이트 = 모의(demo) 매매 ≥10회 AND 누적손익 > 0. 통과 전에는 어떤 실전 주문도 내지 않는다. 자동매매 live 모드도 `ALLOW_LIVE=1` + `--confirm=YES` 이중 잠금.
2. **모의/실전 키는 분리.** `실전계좌` 프로필(real)과 `모의계좌` 프로필(demo)이 따로 있다. 8030 오류("투자구분이 달라서 Appkey를 사용할수 없습니다") = 키와 서버 모드 불일치이지 서버 장애가 아니다.
3. **모의 서버는 API별 유량 1건/초**(오류 1700, HTTP 429). 연속 호출 사이 1초 이상 간격. 실전도 같은 간격이 안전하다.
4. **주문은 `--confirm` 없이는 전송되지 않는다**(CLI 기본). 주문 확인 출력 → 사용자 확인 → `--confirm` 재실행 순서를 지킨다.
5. **키 값은 절대 출력·로그·커밋 금지.** 키는 macOS 키체인에만 있다.

## 준비물 (설정 완료 — 변경 없이 사용)

- CLI: `kiwoomcli` (`uv tool install kwcli`로 설치됨, PATH `~/.local/bin`)
- 프로필 2개 (키체인): `실전계좌`(real) · `모의계좌`(demo, 현재 기본)
- 프로젝트: `~/projects/misc/auto-trading` (uv sync 완료, kwcli 런타임 포함)
- 장중: 평일 09:00~15:30 KST. 공휴일 캘린더 미구현.

## 기본 사용법

```bash
export PATH="$HOME/.local/bin:$PATH"

# 인증 상태 / 프로필 전환
kiwoomcli auth status --profile 모의계좌
kiwoomcli auth login --profile 모의계좌      # 현재 기본 프로필 전환

# 시세 (읽기 전용)
kiwoomcli domestic quotes price --code 005930 --profile 모의계좌
kiwoomcli domestic candles daily --code 069500 --pages 3 --profile 모의계좌

# 계좌 (읽기 전용)
kiwoomcli domestic accounts cash --profile 모의계좌        # 예수금·주문가능금액
kiwoomcli domestic accounts valuation --profile 모의계좌   # 평가잔고
kiwoomcli domestic accounts holdings --profile 모의계좌    # 보유 종목
kiwoomcli domestic orders list-fills --profile 모의계좌    # 체결 내역

# 주문 (demo에서만, 게이트 전 실전 금지)
kiwoomcli domestic orders buy --code 069500 --qty 10 --order-type market --profile 모의계좌
#   ↑ --confirm 없으면 미전송 확인만 출력. 사용자 확인 후:
kiwoomcli domestic orders buy --code 069500 --qty 10 --order-type market --confirm --profile 모의계좌
```

## 자동매매 (auto-trader)

```bash
cd ~/projects/misc/auto-trading

uv run python -m autotrader.cli status                              # 거래 원장 요약
uv run python -m autotrader.cli backtest --symbols 069500 --bars 300 # 읽기 전용 백테스트
uv run python -m autotrader.cli run --mode paper --cycles 30        # 키 없이 가상 (1사이클=가상 1거래일)
uv run python -m autotrader.cli run --mode demo --symbols 069500    # 모의 서버 매매 (장중 폴링)
# live는 ALLOW_LIVE=1 + --confirm=YES 둘 다 없으면 실행 거부. 게이트 전 사용 금지.
```

- 전략: SMA 교차 기본. `autotrader/strategy.py`의 `Strategy` 인터페이스로 교체.
- 안전장치: 포지션 한도·1포지션 예산 상한(현금×20%)·일일 손실 한도(2% 초과 시 당일 중단).
- 원장: `data/ledger.db` (SQLite — trades/equity/signals). 판정은 원장 숫자로만 한다.

## 런타임 직접 호출 (커스텀 API가 필요할 때)

`~/projects/misc/auto-trading`에서 `uv run python`으로 `from kiwoom import get_client` 사용.
공식 스펙 전체 337개: `kiwoom-rest-api/kiwoom/_data/kiwoom_api_spec.json` · `kiwoomcli spec`으로 검색.

| 작업 | api_id | path | body |
|---|---|---|---|
| 종목정보 | ka10001 | /api/dostk/stkinfo | stk_cd |
| 일봉차트 | ka10081 | /api/dostk/chart | stk_cd, base_dt(YYYYMMDD), upd_stkpc_tp=1 |
| 예수금 | kt00001 | /api/dostk/acnt | qry_tp=3(추정) |
| 계좌평가잔고 | kt00018 | /api/dostk/acnt | qry_tp=1, dmst_stex_tp=KRX |
| 매수(시장가) | kt10000 | /api/dostk/ordr | dmst_stex_tp=KRX, stk_cd, ord_qty, trde_tp=3 |
| 매도(시장가) | kt10001 | /api/dostk/ordr | 동일 |

- 차트 응답은 LIST(`stk_dt_pole_chart_qry`), 잔고 종목은 LIST(`acnt_evlt_remn_indv_tot`)로 온다. 연속조회는 cont-yn/next-key.
- 자세한 컬럼·오류 코드·매매구분(trde_tp) 전체 목록: `references/api-map.md`

## 흔한 실패

| 증상 | 원인/처치 |
|---|---|
| 8030 투자구분 불일치 | 키와 모드 불일치. `kiwoomcli auth status`로 프로필 확인 후 `--profile`/`--mode` 맞추기 |
| 429 / 1700 유량 초과 | 모의 서버 1건/초. 1초 이상 간격. autotrader는 1.0s 고정 |
| 자격 증명 없음 | `kiwoomcli setup --alias <별칭> --mode demo\|real` — 키는 키체인 저장 |
| 장 마감 응답 | 평일 09:00~15:30 KST만. autotrader는 자동 대기 |
| 주문 미체결 확인만 출력 | `--confirm` 누락. 사용자 확인 후 재실행 |

## 하지 말 것

- 게이트(09-12) 전 실전 주문 — demo 검증 없이는 절대.
- 키 값을 출력·로그·커밋.
- 유량 무시한 연속 호출(모의 서버 429).
- 사용자가 요청하지 않은 계좌·종목 주문.
- 자동매매 결과를 게이트 판정 없이 "성공"으로 단정 — paper 랜덤워크 수익률은 성과가 아니다. 판정은 demo 원장으로만.
