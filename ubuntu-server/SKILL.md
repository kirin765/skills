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
