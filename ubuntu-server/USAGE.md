# Ubuntu 홈서버 조작 가이드 (LLM 에이전트용)

이 문서 하나만 읽고 바로 작업할 수 있게 쓴 핸드오프 문서다. 대상은 사용자(김기완)의 Ubuntu 홈서버 한 대뿐이다. 다른 원격 호스트에는 쓰지 않는다.

**먼저 알아야 할 두 가지**

1. 계정·인증·별칭은 이미 검증돼 있다. 사용자에게 되묻지 않는다.
2. 이 머신은 Windows와 듀얼부팅이다. SSH가 안 된다고 고장난 게 아니다. 전원을 함부로 끊으면 사용자의 Windows 세션을 강제 종료시킨다. 아래 "전원 판단" 절을 반드시 읽는다.

---

## 1. 접속 정보

| 항목 | 값 |
|---|---|
| SSH 별칭 | `ubuntu-server` (`~/.ssh/config`에 등록됨) |
| Tailscale IP | `100.113.73.17` |
| 호스트명 | `k-MS-7B89` |
| 계정 | `k` |
| 인증 | SSH 공개키 `~/.ssh/id_ed25519`, 비번 없음 |
| Python | 서버의 `python3` = 3.12.3 |
| 하드웨어 | RTX 3060 탑재. NVENC 인코딩 오프로드 노드로 씀 |

IP나 계정을 직접 타이핑하지 말고 항상 별칭을 쓴다.

```bash
ssh ubuntu-server '<명령>'
```

파일 전송은 rsync를 쓴다. venv와 `__pycache__`는 OS 종속이라 반드시 제외한다.

```bash
rsync -av --exclude venv --exclude __pycache__ <로컬경로> ubuntu-server:<원격경로>
```

한 개짜리 소량 복사면 `scp <로컬> ubuntu-server:<원격>`으로 충분하다.

---

## 2. 작업 시작 절차

서버는 평소 꺼져 있을 수 있다. 순서는 이렇다.

```bash
SK=~/.claude/skills/ubuntu-server/scripts

bash "$SK/server_up.sh"     # 켜기. 이미 켜져 있으면 즉시 통과
# ... 여기서 ssh / rsync 실제 작업 ...
bash "$SK/server_down.sh"   # 끄기. 아래 조건을 만족할 때만 부른다
```

`server_down.sh`는 조건부다. 사용자가 "작업 끝나면 서버 꺼줘"라고 했거나, 이 세션이 오직 서버 작업만을 위한 것일 때만 부른다. 애매하면 끄기 전에 물어본다. 전원 차단은 되돌리기 번거롭다.

### 스크립트가 실제로 하는 일

`server_up.sh` — SSH가 이미 되면 즉시 종료한다(코드 0). 안 되면 소비전력을 읽는다. **20W 이상이면 무언가 돌고 있다는 뜻이라 전원을 건드리지 않고 종료코드 2로 중단한다.** 20W 미만(정지)이면 플러그 OFF → 12초 대기 → ON으로 AC 인가 전환을 만들고(그냥 `on`만 보내면 이미 켜진 플러그에는 no-op이라 부팅이 안 걸린다), 5초 간격으로 SSH를 최대 180초까지 폴링한다. 부팅 실패면 종료코드 1.

`server_down.sh` — SSH가 안 되면 플러그만 끄고 종료한다. 되면 `sudo poweroff`를 보내고, Tailscale IP로 ping이 끊길 때까지 최대 90초 기다린 뒤 플러그를 끈다.

---

## 3. 전원 판단 — 여기가 가장 위험한 부분

서버 전원코드에 Tuya 스마트플러그가 물려 있다. BIOS는 `Restore after AC Power Loss = Power On`이라 전기가 들어오면 자동으로 부팅한다. 그래서 플러그 ON/OFF가 곧 전원 버튼 역할을 한다. 전원 인가 후 기본 부팅은 Ubuntu로 들어간다(2026-07-15 실측).

### 왜 켤 때 끄기부터 하는가

BIOS 자동부팅은 AC 전원이 없다가 들어오는 *전환 시점*에만 걸린다. 그런데 플러그는 대부분의 경우 이미 ON이라, `on`을 또 보내면 아무 일도 일어나지 않는다. 예전 스크립트는 이 상태에서 180초를 그냥 흘려보내고 타임아웃했다. 그래서 지금은 **OFF → 12초 → ON**으로 전환을 직접 만든다.

이 순서의 대가는 명확하다. 켜기 동작이 곧 전원차단을 포함한다. 그래서 아래 소비전력 확인이 스크립트 안에 하드코딩된 전제조건이다.

### `server_up.sh`가 코드 2로 중단했을 때

전기는 들어와 있는데 SSH가 안 되는 상태다. **사용자가 Windows를 쓰고 있다**가 가장 흔한 원인이다. Tailscale과 SSH는 둘 다 Ubuntu 쪽 서비스라 Windows가 떠 있으면 당연히 죽어 있다. 이것은 Ubuntu 고장의 증거가 아니다. 2026-07-15에 이 오진으로 사용자의 Windows를 실제로 강제 종료시킨 적이 있다.

이때 스크립트를 우회해 `plug.py off`를 직접 때리지 않는다. 사용자에게 묻는다.

### 전원을 끊기 전 반드시 소비전력을 본다

`plug.py status`가 돌려주는 on/off는 *플러그 스위치* 상태일 뿐, 서버가 도는지 여부가 아니다. 반드시 와트를 봐야 한다. `server_up.sh`가 내부적으로 확인하지만, 수동으로 볼 때는:

```bash
# DPS 19 = cur_power(W×10), 18 = cur_current(mA), 20 = cur_voltage(V×10)
~/.claude/skills/ubuntu-server/venv/bin/python ~/.claude/skills/ubuntu-server/scripts/plug.py watts
```

판정 기준은 실측값이다. 정지 상태는 2~5W, 가동 중은 100W대다(실측 102.4W).

- **와트가 높다 = 무언가 돌고 있다.** 🔴 전원을 끊지 않는다. 대개 Windows 사용 중이다. 와트는 "켜져 있다"만 알려줄 뿐 Windows인지 Ubuntu인지 구분하지 못한다. 사용자에게 "지금 서버에서 Windows 쓰고 계신가요?"라고 묻고 판단을 받는다. 보통 정답은 Ubuntu로 재부팅해 달라고 요청하는 것이다.
- **와트가 0에 가깝다 = 정지 상태다.** `server_up.sh`가 플러그 OFF → 12초 대기 → ON으로 AC 전환을 만들어 자동부팅시킨다. 복구 실측 타이밍은 0W → 99.6W(t+24초) → SSH 응답(t+50초)이다.

### 상태 확인 시 믿으면 안 되는 것들

- `k-MS-7B89.local` mDNS 조회는 ISP DNS 와일드카드 때문에 엉뚱한 공인 IP(218.38.x.x)를 돌려준다.
- LAN 서브넷 스윕은 포트스캔으로 분류돼 차단된다.
- Tailscale 피어 확인은 `/Applications/Tailscale.app/Contents/MacOS/Tailscale status`로 한다. `tailscale` CLI는 PATH에 없다.

---

## 4. 플러그 저수준 제어

```bash
SK=~/.claude/skills/ubuntu-server/scripts
"$SK/../venv/bin/python" "$SK/plug.py" status|watts|on|off
```

기기 정보와 키는 `scripts/plug_config.json`에 있다. `local_key`는 비밀값이므로 로그나 문서에 출력하지 않는다.

| 항목 | 값 |
|---|---|
| Tuya device id | `eba80b902e77c55e4dawrz` |
| 주소 | `192.168.0.8` |
| 프로토콜 | v3.5 |
| 스위치 DPS | `1` |

**로컬 제어라 플러그와 같은 LAN(192.168.0.x)에서만 동작한다.** 집 밖 다른 네트워크에서는 `plug.py`가 실패한다. 이때는 사용자에게 앱으로 켜달라고 요청하거나, 서버가 이미 켜져 있다면 그냥 SSH로 진행한다.

local key 재발급이 필요하면 `scripts/get_local_key.py <ACCESS_ID> <SECRET> us`를 쓴다. 한국 계정은 Western America DC라 리전 코드가 `us`다. Tuya IoT 프로젝트가 무료판이라 DC를 하나만 허용하므로 Western America 하나만 활성화해야 한다.

---

## 5. 지켜야 할 원칙

- **비밀번호를 대신 입력하려 하지 않는다.** 이 환경의 SSH는 비대화형이라 비번을 넣을 수 없고, 그래서 키 인증이 전제다. `Permission denied (publickey)`가 뜨면 서버의 `~/.ssh/authorized_keys`에서 키가 빠진 것이다. 사용자에게 `ssh-copy-id ubuntu-server` 재실행을 요청한다.
- **venv를 복사하지 않는다.** 가상환경 바이너리는 OS와 경로에 종속이라 macOS에서 Ubuntu로 복사하면 깨진다. 서버에서 `python3 -m venv`로 새로 만들고 `pip install`한다.
- **파괴적 명령은 먼저 확인받는다.** 이 서버는 사용자의 실제 홈서버다. `rm -rf`, 파일 덮어쓰기, 프로세스 kill은 실행 전에 사용자 승인을 받는다.

---

## 6. 이미 세팅된 것

- `~/bin/render-on-server` — NVENC 렌더 오프로드 래퍼.
- `~/.config/youtube-upload/` — youtube-upload 스킬의 인증 파일(`client_secret.json`, `token*.json`)과 venv(google-api-python-client, google-auth-oauthlib 설치됨). 스크립트는 로컬 맥의 `~/.claude/skills/youtube-upload/scripts/`에 있다. 즉 이 서버에서 youtube-upload를 바로 돌릴 수 있다.
- 저장은 루트 계정 소유 경로만 쓴다. Tailscale 네트워크로만 접근한다.
