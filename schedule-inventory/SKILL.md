---
name: schedule-inventory
description: 이 Mac의 모든 예약 실행 표면을 한 번에 조회한다 — Claude Code 파일 루틴(~/.claude/scheduled-tasks), 유저·시스템 launchd(~/Library/LaunchAgents 등), user crontab. 각 항목의 스케줄·실행명령·로드 상태·마지막 종료코드를 보여주고, 내 루틴 중 마지막 실행이 실패한 것만 골라 롤업한다. "내 루틴/예약작업 전부 보여줘", "돌고 있는 스케줄 뭐 있어", "launchd/cron 조회", "어떤 routine 있지", "안 도는 루틴 있나", "list my scheduled jobs/agents" 류 요청에 발동. Read-only — 아무것도 바꾸지 않는다.
---

# schedule-inventory

이 맥에서 "정기/예약 실행되는 모든 것"을 한 화면에 모아 보여주는 read-only 인벤토리.

## 언제

사용자가 자기 예약 루틴·launchd·cron 전반을 파악하려 하거나("뭐가 돌고 있지", "루틴 목록", "안 도는 거 있나"), 특정 루틴이 살아있는지 확인하려 할 때.

## 실행

```bash
python3 ~/.claude/skills/schedule-inventory/scripts/inventory.py
```

표준 라이브러리만 쓰므로 시스템 `python3`로 바로 실행. 인자 없음. 출력이 곧 리포트다 — 사용자에게는 섹션별로 요약해 전달하되, **마지막 실패 롤업(⚠)은 반드시 그대로 짚어준다.**

## 커버하는 4개 표면

1. **Claude Code 파일 루틴** — `~/.claude/scheduled-tasks/*/`(활성)·`~/.claude/scheduled-tasks-disabled/*/`(비활성). 각 디렉터리의 `SKILL.md` frontmatter `name`+`description`을 출력(스케줄은 description에 산문으로 적힘).
2. **유저 launchd** — `~/Library/LaunchAgents/*.plist`. 스케줄(StartCalendarInterval/StartInterval/KeepAlive)·실행명령·`launchctl list` 로드상태·마지막 종료코드.
3. **시스템 launchd** — `/Library/LaunchAgents`·`/Library/LaunchDaemons`(간략 목록+로드상태).
4. **user crontab** — `crontab -l`.

마지막에 **유저 launchd 중 last-exit ≠ 0/‑** 만 골라 실패 롤업. (Apple/Google 온디맨드 에이전트는 유휴 시 exit ‑9로 종료되는 게 정상이라 노이즈 → 시스템 것은 롤업에서 제외.)

## 권위 메타 보강 (선택)

파일 루틴의 정확한 `cronExpression·enabled·lastRunAt·nextRunAt`은 **`mcp__scheduled-tasks__list_scheduled_tasks`** 도구가 소스다. 단 이 MCP 도구는 **무인 루틴 실행 컨텍스트에만 주입**되고 일반 대화형 세션엔 없다. 현재 세션에서 그 도구가 보이면 호출해 스케줄·마지막 실행시각을 붙여주고, 없으면 파일 정의(description의 스케줄 산문)로만 보고한다.

## 해석 가이드

- **last-exit=0** 마지막 실행 정상 · **last-exit=‑** 미실행/해당없음 · **그 외 숫자/음수** 마지막 실행 실패 또는 시그널 종료.
- KeepAlive 데몬의 음수 종료(예: ‑15 SIGTERM)는 재시작 흔적일 수 있으니 `pid`가 현재 잡혀 있으면 살아있는 것 — pid와 함께 판단.
- 스케줄이 `on-demand/trigger`면 시각 예약이 아니라 이벤트/소켓 트리거(예: WatchPaths, 다른 프로세스가 호출).

Read-only 원칙: 이 스킬은 조회만 한다. 루틴을 켜고/끄거나 고치는 건 별도 작업(launchctl load/unload, 파일 이동 등)으로, 사용자 확인 후에만.
