---
name: ubuntu-server
description: 사용자의 Ubuntu 홈서버(Tailscale IP 100.113.73.17, 호스트명 k-MS-7B89)에 SSH로 접속해 명령을 실행하거나 파일을 주고받을 때 쓰는 접속 정보 스킬. 사용자가 "우분투 서버에 접속", "ubuntu 서버에서 ~~ 실행", "서버에 올려줘/복사해줘", "홈서버에서 돌려줘", "100.113.73.17에 ~~", "k-MS-7B89", "서버에 스킬/파일 세팅" 같이 *그 우분투 서버를 대상으로 무언가* 하려고 할 때 반드시 발동한다. 어느 프로젝트/세션에서든 동작하며, 접속 계정·인증·별칭을 매번 물어보지 않고 이 스킬의 고정 정보를 그대로 쓴다. 다른 원격 호스트(이 IP/호스트명이 아닌 곳)에는 쓰지 않는다.
---

# Ubuntu 홈서버 접속

사용자의 Ubuntu 홈서버에 접속·명령 실행·파일 전송할 때 아래 고정 정보를 그대로 쓴다.
매번 계정이나 인증 방식을 사용자에게 되묻지 말 것 — 이미 검증돼 있다.

## 접속 정보

| 항목 | 값 |
|---|---|
| 호스트 (Tailscale IP) | `100.113.73.17` |
| 호스트명 | `k-MS-7B89` |
| 계정 | `k` |
| 인증 | SSH 공개키 (`~/.ssh/id_ed25519`) — 비번 불필요 |
| SSH 별칭 | `ubuntu-server` (`~/.ssh/config`에 등록됨) |
| Python | `python3` = 3.12.3 |

## 기본 사용법

별칭이 등록돼 있으니 IP·계정을 직접 쓰지 말고 별칭을 쓴다:

```bash
ssh ubuntu-server '<명령>'
```

파일 전송(로컬 → 서버). venv·`__pycache__`처럼 OS 종속·재생성 가능한 건 제외:

```bash
rsync -av --exclude venv --exclude __pycache__ <로컬경로> ubuntu-server:<원격경로>
```

단발성 소량 복사면 `scp <로컬> ubuntu-server:<원격>`도 된다.

## 자동 전원 제어 (스마트플러그)

서버 전원코드에 Tuya 스마트플러그가 물려 있고, BIOS는 **전원 인가 시 자동 부팅**
(`Restore after AC Power Loss = Power On`)으로 설정돼 있다. 그래서 플러그 ON/OFF로
서버를 켜고 끈다. **끌 때는 반드시 먼저 SSH로 정상 종료한 뒤 플러그를 끊는다**
(하드 전원차단은 파일시스템 손상 위험).

이 스킬로 서버 작업을 요청받으면, 서버가 꺼져 있을 수 있으니 **작업 전에 `server_up.sh`로
켜고**, 작업이 끝나면 **`server_down.sh`로 정상 종료 후 플러그를 끈다.**

```bash
SK=~/.claude/skills/ubuntu-server/scripts

# 켜기: 플러그 ON → BIOS 자동부팅 → SSH 뜰 때까지 대기 (이미 켜져 있으면 즉시 통과)
bash "$SK/server_up.sh"

# ...여기서 실제 작업(ssh/rsync)...

# 끄기: ssh 'sudo poweroff' → halt 확인 → 플러그 OFF
bash "$SK/server_down.sh"

# 플러그 저수준 제어 (필요 시)
"$SK/../venv/bin/python" "$SK/plug.py" status|on|off
```

주의:
- **로컬 제어라 플러그와 같은 LAN(192.168.0.x)에서만 된다.** 집 밖(다른 네트워크)에서는
  `plug.py`가 실패한다. 이땐 사용자에게 플러그를 앱으로 켜달라고 요청하거나, 서버가 이미
  켜져 있다면 그냥 SSH로 진행한다.
- 사용자가 명시적으로 "작업 끝나면 서버 꺼줘"라고 했거나, 세션이 서버 작업만을 위한 것일 때만
  `server_down.sh`를 부른다. 애매하면 끄기 전에 확인한다 (전원 차단은 되돌리기 번거로움).
- 기기 정보/키는 `scripts/plug_config.json`. local_key는 비밀값이다.

Tuya 기기: `eba80b902e77c55e4dawrz` @ `192.168.0.8`, 프로토콜 v3.5, 스위치 DPS `1`.
local key는 이미 `plug_config.json`에 세팅돼 있다. 재발급이 필요하면
`scripts/get_local_key.py <ACCESS_ID> <SECRET> us` (한국 계정 = Western America DC = `us`).
Tuya IoT 프로젝트는 무료판이라 DC 1개만 허용 — 반드시 **Western America** 하나만 활성화.

## 원칙

- **비대화형 세션 주의**: 이 환경의 SSH는 비밀번호 입력을 대신 못 넣는다. 그래서 키 인증이
  전제다. 만약 `Permission denied (publickey)`가 뜨면 키가 서버 `~/.ssh/authorized_keys`에서
  빠진 것이니, 사용자에게 `ssh-copy-id ubuntu-server` 재실행을 요청한다 — 대신 비번을 넣으려
  하지 말 것.
- **venv는 복사 금지**: 가상환경 바이너리는 OS/경로 종속이라 macOS→Ubuntu 복사가 깨진다.
  서버에서 `python3 -m venv`로 새로 만들고 `pip install` 한다.
- **파괴적 명령 확인**: 서버는 사용자의 실제 홈서버다. `rm -rf`, 덮어쓰기, 프로세스 kill 등은
  전역 규칙대로 먼저 확인받는다.

## 알려진 세팅

- `~/.config/youtube-upload/` — youtube-upload 스킬 인증 파일(`client_secret.json`,
  `token*.json`)과 `venv`(google-api-python-client, google-auth-oauthlib 설치됨).
  스크립트는 `~/.claude/skills/youtube-upload/scripts/`에 있다. 즉 이 서버에서
  youtube-upload를 바로 돌릴 수 있다.
