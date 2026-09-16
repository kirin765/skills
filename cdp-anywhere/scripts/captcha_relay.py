#!/usr/bin/env python3
"""
cdp-anywhere captcha relay — human-in-the-loop 캡차 풀이 릴레이.

자동으로 캡차를 푸는 게 아니다(OCR · 풀이 서비스 · 클릭 매크로 금지). 캡차를 만나면
스크린샷을 **계정 주인(사용자) 본인**에게 전송하고, 사람이 입력한 답을 돌려받아
stdout/파일로 내보낸다 — 에이전트가 그 답을 캡차 입력란에 넣고 제출한다.

채널 (자동 fallback 순서): telegram → naver-mail → file inbox
  - telegram : sendPhoto + getUpdates 폴링. ~/niche-finder/.env 의
               TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 사용.
  - naver-mail : SMTP(발송) + IMAP(답장 폴링). ~/niche-finder/.env 의
               NAVER_MAIL_ADDRESS / NAVER_MAIL_PASSWORD / (NAVER_MAIL_USER).
  - file : ~/.cdp-anywhere/captcha/<id>.png + <id>.prompt.txt 를 두고
           <id>.answer 파일이 생길 때까지 대기 (SSH/터미널 사용자용).

사용 예:
  # check — 어떤 채널을 쓸 수 있는지
  python3 captcha_relay.py check

  # ask — 이미지 전송 + 답 폴링 (성공 시 ANSWER=... 출력 + <id>.answer 파일)
  python3 captcha_relay.py ask --site example.com --image /tmp/chal.png \
      --prompt "이미지 속 문자 6자를 입력하세요" --timeout 300

  # ask — 특정 채널만 / 채널 순서 강제 (auto | telegram | email | file | 쉼표 목록)
  python3 captcha_relay.py ask --site x --image a.png --channel email --timeout 180

  # notify — 답 폴링 없이 알림만 (예: "진행이 막혔어요" 한 번 알림)
  python3 captcha_relay.py notify --site x --text "캡차 대기 중"

성공 exit 0 / 답 없음(timeout) exit 2 / 설정·전송 실패 exit 1 / 기타 오류 exit 3.
"""
from __future__ import annotations

import argparse
import email as email_mod
import imaplib
import json
import os
import re
import smtplib
import subprocess
import sys
import time
import urllib.request
import uuid
from datetime import date
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

ENV_FILE = Path.home() / "niche-finder" / ".env"
WORKDIR = Path(
    os.environ.get("CAPTCHA_DIR", str(Path.home() / ".cdp-anywhere" / "captcha"))
).expanduser()

SMTP_HOST, SMTP_PORT = "smtp.naver.com", 465
IMAP_HOST, IMAP_PORT = "imap.naver.com", 993
TG_API = "https://api.telegram.org"

DEFAULT_TIMEOUT = 300
CHANNEL_ORDER = ["telegram", "email", "file"]


# ---------------------------------------------------------------- creds/env

def load_env() -> None:
    """~/niche-finder/.env 를 os.environ 에 채운다 (이미 있으면 안 덮음)."""
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def channel_ready(ch: str) -> tuple[bool, str]:
    """채널을 쓸 수 있는지 + 상태 메시지."""
    if ch == "telegram":
        tok = os.environ.get("TELEGRAM_BOT_TOKEN")
        cid = os.environ.get("TELEGRAM_CHAT_ID")
        if not tok or not cid:
            return False, "TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID 없음 — ~/niche-finder/.env 에 추가"
        return True, f"telegram (chat_id={cid})"
    if ch == "email":
        a = os.environ.get("NAVER_MAIL_ADDRESS")
        p = os.environ.get("NAVER_MAIL_PASSWORD")
        if not a or not p:
            return False, "NAVER_MAIL_ADDRESS/NAVER_MAIL_PASSWORD 없음 — ~/niche-finder/.env 에 추가"
        return True, f"email ({a})"
    if ch == "file":
        return True, f"file ({WORKDIR})"
    return False, f"알 수 없는 채널: {ch}"


# ------------------------------------------------------------ text handling

def normalize_answer(raw: str | None) -> str | None:
    """사람 답장 텍스트 → 후보 답. 못 얻으면 None.

    전략: 인용 원문/라벨을 벗겨낸 뒤, 본문에서 첫 번째 '캡차답처럼 보이는 토큰'
    (영숫자·하이픈 3~8자) 을 뽑는다. 없으면 첫 토큰을 폴백으로 쓴다.
    최종 검증은 에이전트가 제출 후 성공/실패로 확인한다(틀리면 한 번 재시도).
    """
    if not raw:
        return None
    s = raw.replace("\r", "").strip()
    # 인용 원문 이하 제거 (Naver/이메일 답장 헤더 — 맨 앞부터여도 제거)
    body = s
    for sep in ("-----Original Message", "---Original Message",
                "보낸 사람", "보낸사람", "보낸 날짜", "원문 내용"):
        idx = body.find(sep)
        if idx >= 0:
            body = body[:idx].strip()
    if not body:
        body = s
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]
    if not lines:
        return None
    # 이메일 인용(---, >, |) 시작 줄은 스킵
    i = 0
    while i < len(lines) and re.match(r"^[->|]", lines[i]):
        i += 1
    if i >= len(lines):
        return None
    line = lines[i].strip('"\'`“”‘’「」『』').strip()
    # 라벨 제거: "답/답변/정답/answer/captcha/code/보안문자 + (은|는|이)? + (:)?"
    m = re.match(
        r"^(?:답변|정답|답|answer|captcha|code|인증코드|보안문자)"
        r"(?:은|는|이)?\s*[:：]?\s*(.+)$",
        line, re.IGNORECASE)
    candidate = m.group(1) if m else line
    # 첫 캡차답 형태 토큰을 우선. 문장이면 숫자 포함 토큰 > 4~8자 영문 토큰(불용어 제외).
    tokens = [t.strip('.,;:!?()[]{}"\'`“”‘’「」『』') for t in candidate.split()]
    stopwords = {"the", "this", "that", "with", "from", "code", "answer",
                 "answers", "is", "are", "and", "your", "please"}
    for t in tokens:
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{2,7}", t) and re.search(r"[0-9]", t):
            return t
    for t in tokens:
        if (re.fullmatch(r"[A-Za-z][A-Za-z]{3,7}", t)
                and t.lower() not in stopwords):
            return t
    first = tokens[0] if tokens else None
    if first and len(first) >= 3 and re.search(r"[A-Za-z0-9]", first):
        return first
    return None


# --------------------------------------------------------------- telegram

def tg_send(tok: str, cid: str, text: str, image: str | None) -> None:
    """curl multipart 로 사진(+caption) 또는 메시지 발송."""
    if image and Path(image).exists():
        url = f"{TG_API}/bot{tok}/sendPhoto"
        cmd = ["curl", "-sS", "-X", "POST", url,
               "-F", f"chat_id={cid}",
               "-F", f"photo=@{image}",
               "-F", f"caption={text}"]
    else:
        url = f"{TG_API}/bot{tok}/sendMessage"
        cmd = ["curl", "-sS", "-X", "POST", url,
               "-F", f"chat_id={cid}",
               "-F", f"text={text}"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
    except Exception as e:
        raise RuntimeError(f"telegram 전송 실패(실행): {e}") from e
    try:
        resp = json.loads(out.stdout or "{}")
    except json.JSONDecodeError:
        raise RuntimeError(f"telegram 응답 파싱 실패: {out.stdout[:300]}") from None
    if not resp.get("ok"):
        raise RuntimeError(f"telegram 전송 거부: {resp.get('description')}")


def tg_poll(tok: str, cid: str, since_ts: float, timeout_s: float) -> str | None:
    """sendPhoto 이후 새 메시지를 getUpdates 로 폴링해 답 텍스트 반환."""
    try:
        cid_num = int(cid)  # 음수(그룹) 도 그대로 비교
    except (TypeError, ValueError):
        cid_num = None
    offset = None
    deadline = time.time() + timeout_s
    while True:
        remaining = deadline - time.time()
        if remaining <= 0:
            return None
        url = f"{TG_API}/bot{tok}/getUpdates?timeout={min(50, int(remaining))}"
        if offset is not None:
            url += f"&offset={offset}"
        url += '&allowed_updates=["message"]'
        try:
            with urllib.request.urlopen(url, 60) as r:
                data = json.loads(r.read())
        except Exception as e:
            raise RuntimeError(f"telegram getUpdates 실패: {e}") from e
        if not data.get("ok"):
            raise RuntimeError(f"telegram getUpdates 거부: {data.get('description')}")
        updates = data.get("result", [])
        for u in updates:
            uid = u.get("update_id")
            if offset is None or (uid and uid >= offset):
                offset = uid + 1 if uid is not None else None
            msg = u.get("message") or {}
            if not msg.get("text"):
                continue
            mdate = msg.get("date", 0)
            if mdate < since_ts - 5:
                continue
            fid = (msg.get("from") or {}).get("id")
            mcid = (msg.get("chat") or {}).get("id")
            if cid_num is not None and not (fid == cid_num or mcid == cid_num):
                continue
            ans = normalize_answer(msg["text"])
            if ans:
                return ans
        if offset is None:
            offset = max((u.get("update_id", 0) for u in updates), default=0) + 1
        time.sleep(1)


# ------------------------------------------------------------------- email

def _mail_addr() -> str:
    return os.environ["NAVER_MAIL_ADDRESS"]


def _mail_login() -> str:
    return os.environ.get("NAVER_MAIL_USER") or _mail_addr().split("@", 1)[0]


def mail_send(subject: str, body: str, image: str | None) -> str:
    """답장 감지를 위한 Message-ID 를 반환."""
    addr = _mail_addr()
    msg = EmailMessage()
    msg["From"] = formataddr(("cdp-anywhere captcha", addr))
    msg["To"] = addr
    msg["Subject"] = subject
    msg["Message-ID"] = f"<captcha-{uuid.uuid4().hex}@localhost>"
    msg.set_content(body)
    if image and Path(image).exists():
        data = Path(image).read_bytes()
        msg.add_attachment(data, maintype="image",
                           subtype=Path(image).suffix.lstrip(".") or "png",
                           filename=Path(image).name)
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=40) as smtp:
        smtp.login(_mail_login(), os.environ["NAVER_MAIL_PASSWORD"])
        smtp.send_message(msg)
    return msg["Message-ID"]


def _decode_part(part) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def mail_poll(marker_id: str, msgid: str, since_ts: float, timeout_s: float) -> str | None:
    """INBOX 에서 내 Message-ID 로의 답장(Reply) 을 폴링."""
    deadline = time.time() + timeout_s
    sent_msgid = msgid.strip("<>").lower()
    while True:
        if time.time() > deadline:
            return None
        imap = None
        try:
            imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=40)
            imap.login(_mail_login(), os.environ["NAVER_MAIL_PASSWORD"])
            imap.select("INBOX", readonly=True)
            since = date.fromtimestamp(since_ts).strftime("%d-%b-%Y")
            typ, resp = imap.uid("SEARCH", None, f"(SINCE {since})")
            uids = resp[0].split() if typ == "OK" and resp[0] else []
            # 최신 우선
            for uid in reversed(uids[-40:]):
                typ2, msg_resp = imap.uid("FETCH", uid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM IN-REPLY-TO REFERENCES MESSAGE-ID DATE)])")
                if typ2 != "OK" or not msg_resp or msg_resp[0] is None:
                    continue
                hdr = email_mod.message_from_bytes(msg_resp[0][1])
                subj = str(hdr.get("Subject", ""))
                if marker_id not in subj and marker_id.lower() not in subj.lower():
                    continue
                if sent_msgid and sent_msgid not in str(hdr.get("In-Reply-To", "")).lower() \
                        and sent_msgid not in str(hdr.get("References", "")).lower():
                    # 내가 자기 자신에게 보낸 원본(제목 일치)은 제외
                    if str(hdr.get("From", "")).find(_mail_addr()) >= 0 \
                            and str(hdr.get("In-Reply-To", "")) == "":
                        continue
                typ3, body_resp = imap.uid("FETCH", uid, "(BODY.PEEK[TEXT])")
                if typ3 != "OK" or not body_resp or body_resp[0] is None:
                    continue
                raw_text = body_resp[0][1]
                m = email_mod.message_from_bytes(raw_text)
                parts = [p for p in m.walk() if p.get_content_type() == "text/plain"]
                body = "\n".join(_decode_part(p) for p in parts)
                if not body.strip():
                    body = str(raw_text, "utf-8", "replace")
                ans = normalize_answer(body)
                if ans:
                    return ans
        except Exception as e:
            raise RuntimeError(f"naver mail 폴링 실패: {e}") from e
        finally:
            try:
                imap.logout()
            except Exception:
                pass
        time.sleep(15)


# -------------------------------------------------------------------- file

def file_send(site: str, cid: str, prompt: str, image: str | None) -> Path:
    """<dir>/<cid>.png + <cid>.prompt.txt 를 만들고 <cid>.answer 파일 경로 반환."""
    WORKDIR.mkdir(parents=True, exist_ok=True)
    if image and Path(image).exists():
        import shutil
        shutil.copyfile(image, WORKDIR / f"{cid}.png")
    (WORKDIR / f"{cid}.prompt.txt").write_text(
        f"site: {site}\nprompt: {prompt}\nanswer 를 {cid}.answer 파일에 한 줄로 적어주세요.\n",
        encoding="utf-8")
    return WORKDIR / f"{cid}.answer"


def file_poll(cid: str, timeout_s: float) -> str | None:
    deadline = time.time() + timeout_s
    apath = WORKDIR / f"{cid}.answer"
    while True:
        if apath.exists():
            ans = normalize_answer(apath.read_text(encoding="utf-8"))
            if ans:
                return ans
        if time.time() > deadline:
            return None
        time.sleep(3)


# ------------------------------------------------------------------- flow

def build_prompt(site: str, prompt: str | None, cid: str) -> str:
    p = prompt or "첨부 이미지의 보안 문자(캡차)를 확인해주세요."
    return (f"[캡차] {site}\n{p}\n"
            f"답을 텍스트로만 보내주세요 (예: 4F2K).\n챌린지 ID: {cid}")


def resolve_channels(channel_arg: str) -> list[str]:
    if channel_arg in (None, "", "auto"):
        return CHANNEL_ORDER
    return [c.strip() for c in channel_arg.split(",") if c.strip()]


def send_one(ch: str, site: str, cid: str, text: str, image: str | None) -> tuple[bool, str, str]:
    """(성공, 상태메시지, telegram 이면 답장 감지용 부가정보)"""
    ok, msg = channel_ready(ch)
    if not ok:
        return False, msg, ""
    if ch == "telegram":
        tg_send(os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"], text, image)
        return True, msg, os.environ["TELEGRAM_CHAT_ID"]
    if ch == "email":
        mid = mail_send(f"[captcha:{cid}] {site} — 답장으로 답을 보내주세요", text, image)
        return True, msg, mid
    if ch == "file":
        apath = file_send(site, cid, text, image)
        print(f"[file] challenge: {WORKDIR / cid}.png  |  answer file: {apath}")
        return True, msg, ""
    return False, f"알 수 없는 채널 {ch}", ""


def poll_one(ch: str, cid: str, extra: str, since_ts: float, timeout_s: float) -> str | None:
    """채널별 답 폴링. 성공 시 정규화된 답, 아니면 None."""
    if ch == "telegram":
        return tg_poll(os.environ["TELEGRAM_BOT_TOKEN"], extra, since_ts, timeout_s)
    if ch == "email":
        return mail_poll(cid, extra, since_ts, timeout_s)
    if ch == "file":
        return file_poll(cid, timeout_s)
    return None


def cmd_check(args) -> int:
    load_env()
    print("채널 상태:")
    ok_any = False
    for ch in CHANNEL_ORDER:
        ok, msg = channel_ready(ch)
        print(f"  {'✅' if ok else '❌'} {ch}: {msg}")
        ok_any = ok_any or ok
    print(f"\n작업 디렉토리: {WORKDIR}")
    return 0 if ok_any else 1


def cmd_notify(args) -> int:
    load_env()
    text = (args.text or "").strip()
    if not text:
        print("notify: --text 필요", file=sys.stderr)
        return 1
    # notify 는 메시지성 채널(telegram/email) 만. file inbox 는 ask 용.
    channels = [c for c in resolve_channels(args.channel or "auto") if c != "file"]
    for ch in channels:
        ok, msg = channel_ready(ch)
        if not ok:
            print(f"[notify] {ch} 건너뜀 — {msg}", file=sys.stderr)
            continue
        try:
            send_one(ch, args.site, uuid.uuid4().hex[:10], text, args.image)
        except Exception as e:
            print(f"[notify] {ch} 실패 — {e}", file=sys.stderr)
            continue
        print(f"[notify] {ch} 전송 완료")
        return 0
    print("ERR notify: 사용 가능한 채널 없음", file=sys.stderr)
    return 1


def cmd_ask(args) -> int:
    load_env()
    cid = args.id or f"{re.sub(r'[^a-z0-9.-]', '_', (args.site or 'captcha').lower())}-{time.strftime('%Y%m%d-%H%M%S')}"
    if not args.image:
        print("ask: --image 필요 (캡차 스크린샷 경로)", file=sys.stderr)
        return 1
    if not Path(args.image).exists():
        print(f"ask: 이미지 없음 — {args.image}", file=sys.stderr)
        return 1
    channels = resolve_channels(args.channel)
    deadline = time.time() + max(10, int(args.timeout))
    text = build_prompt(args.site or "", args.prompt, cid)

    # 1) 전송
    attempts = []
    for ch in channels:
        ok, msg = channel_ready(ch)
        if not ok:
            print(f"[send] {ch} 건너뜀 — {msg}", file=sys.stderr)
            continue
        try:
            ok_send, msg_send, extra = send_one(ch, args.site or "", cid, text, args.image)
        except Exception as e:
            print(f"[send] {ch} 실패 — {e}", file=sys.stderr)
            continue
        print(f"[send] {ch} 전송 완료 — {msg_send}")
        attempts.append((ch, extra))

    if not attempts:
        print("ERR 사용 가능한 채널 없음 — 텔레그램/네이버메일 자격증명 추가 후 재시도, "
              "또는 --channel file 로 로컬 inbox 사용.", file=sys.stderr)
        return 1

    # 2) 폴링 (전송 순서대로, 전체 deadline 내)
    since = time.time()
    for ch, extra in attempts:
        remaining = deadline - time.time()
        if remaining <= 5:
            break
        print(f"[wait] {ch} 에서 답 대기 (최대 {int(remaining)}s)...", file=sys.stderr)
        try:
            ans = poll_one(ch, cid, extra, since, remaining)
        except Exception as e:
            print(f"[wait] {ch} 오류 — {e}", file=sys.stderr)
            ans = None
        if ans:
            WORKDIR.mkdir(parents=True, exist_ok=True)
            (WORKDIR / f"{cid}.answer").write_text(ans + "\n", encoding="utf-8")
            print(f"ANSWER={ans}")
            print(f"saved {WORKDIR / cid}.answer", file=sys.stderr)
            return 0

    print("ERR 답 없음 — 사용자에게 다시 물어보거나 중단. "
          f"(챌린지 {cid}, 재시도 시 --id {cid} 로 새 이미지와 함께 다시 실행 가능)", file=sys.stderr)
    return 2


def main() -> int:
    ap = argparse.ArgumentParser(description="cdp-anywhere captcha relay")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ck = sub.add_parser("check", help="채널 자격증명 확인")
    ck.set_defaults(fn=cmd_check)

    nf = sub.add_parser("notify", help="답 폴링 없이 알림만 (텍스트/이미지)")
    nf.add_argument("--site", default="")
    nf.add_argument("--text", required=True)
    nf.add_argument("--image", default=None)
    nf.add_argument("--channel", default="auto")
    nf.set_defaults(fn=cmd_notify)

    ak = sub.add_parser("ask", help="캡차 이미지 전송 + 답 폴링 (본 작업)")
    ak.add_argument("--site", default="")
    ak.add_argument("--image", required=True)
    ak.add_argument("--prompt", default=None, help="화면에 보이는 캡차 지시문 (예: 6자리 숫자 입력)")
    ak.add_argument("--channel", default="auto",
                    help="auto | telegram | email | file | 쉼표 구분 순서")
    ak.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                    help=f"전체 대기 시간 초 (기본 {DEFAULT_TIMEOUT})")
    ak.add_argument("--id", default=None, help="챌린지 id (없으면 자동)")
    ak.add_argument("--dir", default=None, help="작업 디렉토리 (기본 ~/.cdp-anywhere/captcha)")
    ak.set_defaults(fn=cmd_ask)

    args = ap.parse_args()
    if getattr(args, "dir", None):
        global WORKDIR
        WORKDIR = Path(args.dir).expanduser()
    try:
        return int(args.fn(args))
    except KeyboardInterrupt:
        print("\n중단됨 (Ctrl-C)", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
