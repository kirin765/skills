# 키움 REST API 상세 참조 (api-map)

공식 스펙: `~/projects/misc/auto-trading/kiwoom-rest-api/kiwoom/_data/kiwoom_api_spec.json` (337개) · `kiwoomcli spec`으로 검색. 이 문서는 실측 검증된 것만 담는다.

## 인증·프로필

- CLI: `uv tool install kwcli` → `kiwoomcli`. 키는 키체인에 저장(운영체제 자격 증명 저장소).
- 프로필: `kiwoomcli setup --alias <별칭> --mode demo|real`. 현재 기본 = `모의계좌`(demo).
- 프로필 확인: `kiwoomcli auth status --profile <별칭>` / `kiwoomcli doctor`
- **모의/실전 키 분리(실측)**: 실전 키를 모의 서버에 쓰면 `8030 투자구분 불일치`, 반대도 동일. 교차 금지.

## 도메인

| 모드 | REST | WebSocket |
|---|---|---|
| real | https://api.kiwoom.com | wss://api.kiwoom.com:10000 |
| demo | https://mockapi.kiwoom.com | (모의) |

## 매매구분 (trde_tp)

| 코드 | 의미 | | 코드 | 의미 |
|---|---|---|---|---|
| 0 | 보통(지정가, ord_uv 필요) | | 13 | 시장가(IOC) |
| 3 | 시장가 (기본) | | 16 | 최유리(IOC) |
| 5 | 조건부지정가(cond_uv) | | 20 | 보통(FOK) |
| 6 | 최유리지정가 | | 23 | 시장가(FOK) |
| 7 | 최우선지정가 | | 28 | 스톱지정가 |
| 10 | 보통(IOC) | | 81 | 장마감후시간외 |

## 주요 응답 키 (실측)

- **ka10081 일봉차트**: 본문 `stk_dt_pole_chart_qry` LIST. 항목: `dt`(일자)·`open_pric`·`high_pric`·`low_pric`·`cur_prc`(종가)·`trde_qty`·`trde_prica`. 수정주가: `upd_stkpc_tp=1` + base_dt를 권리발생일 이후로.
- **kt00001 예수금**: `entr`(예수금)·`ord_alow_amt`(주문가능금액)·`ord_alow_amt_entr`(주문가능금액(예수금))·`pymn_alow_amt`(출금가능금액). qry_tp: 3=추정, 2=일반.
- **kt00018 계좌평가잔고**: `prsm_dpst_aset_amt`(추정예탁자산)·`tot_evlt_amt`(총평가금액)·`tot_pur_amt`(총매입금액)·`tot_evlt_pl`(총평가손익)·`acnt_evlt_remn_indv_tot` LIST(종목별: `stk_cd`·`stk_nm`·`rmnd_qty`·`trde_able_qty`·`cur_prc`·`evlt_amt`). qry_tp: 1=합산, 2=개별.
- **kt10000/kt10001 주문**: `ord_no`(주문번호). 체결가는 잔고 조회로 리컨실레이션.

## 오류 코드 (실측)

| 코드 | 의미 | 처치 |
|---|---|---|
| 8030 | 투자구분(실전/모의) 불일치 | 키와 서버 모드 맞추기 |
| 1700 (HTTP 429) | 허용된 API 요청 개수 초과, 유량=1 | 1초 이상 간격 |
| 8005 / return_code=3 | 토큰 만료·무효 | 런타임이 자동 재발급(401 복구) |

## 유량 정책 (실측 2026-08-29)

- 모의 서버: API별 1건/초. 공식 예제의 0.2s 간격은 429 발생 → autotrader는 1.0s 고정.
- 실전 서버: 동일 간격 사용 중(문제 없음). 단발 300봉 백테스트(연속조회 ~5페이지)는 정상.

## 자동매매 원장 (SQLite: data/ledger.db)

- `trades`: ts·mode·symbol·side(BUY/SELL)·qty·price·gross·fee·tax·reason
- `equity`: ts·equity·cash·positions_value — 자산 곡선
- `signals`: ts·symbol·signal(BUY/SELL/HOLD)·price·detail — 전략 판단 이력
- 실현손익 = 매도 기준 FIFO(수수료·세금 차감). 미체결 포지션 제외.
