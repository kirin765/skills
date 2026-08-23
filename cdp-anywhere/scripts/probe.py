#!/usr/bin/env python3
"""
cdp-anywhere probe — CDP 9222 응답, 열린 탭, 대상 도메인 쿠키 존재 여부 확인.

스킬은 어떤 작업이든 시작 전 이 스크립트를 먼저 돌린다. 실패하면 즉시 멈추고
사용자에게 안내. 추정으로 본 작업 들어가지 말 것.

이 머신에는 항상 두 개의 Chrome 인스턴스가 있을 수 있다 — 헷갈리지 말 것:
  - "메인 Chrome"   : 사용자가 평소 쓰는 창 (Default 프로파일). Claude in Chrome
                      확장(Engine A)이 여기 붙는다. CDP 포트 없음, 절대 안 건드림.
  - "CDP Chrome"    : $HOME/chrome-cdp-profile 전용 프로파일, --remote-debugging-
                      port=9222 로 뜬 것. Engine B(CDP+Playwright) 전용.
둘을 구분하는 유일한 기준은 **9222 응답 여부**다. `pgrep`/`ps` 로 "Chrome 떠
있나"만 보고 판단하지 말 것 — 메인 Chrome 이 떠 있어도 CDP Chrome 은 안 떠
있을 수 있다.

사용 예:
  python probe.py                       # CDP + 열린 탭만 확인 (안 떠 있으면 자동 기동 시도)
  python probe.py --host linkedin.com   # 추가로 해당 호스트 쿠키 확인
  python probe.py --host x.com --json   # 머신리더블 출력
  python probe.py --no-autolaunch       # 자동 기동 없이 상태만 확인
"""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request

CDP_VERSION = "http://localhost:9222/json/version"
CDP_TABS = "http://localhost:9222/json"
CDP_PROFILE_DIR = "$HOME/chrome-cdp-profile"

# macOS 전용 — 이 스킬은 darwin 환경 기준. 다른 OS는 chrome-setup.md 안내로 폴백.
MACOS_CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def probe_cdp_http() -> tuple[bool, str, dict | None]:
    """HTTP /json/version 으로 CDP 살아있는지 확인. Playwright 없이 가능."""
    try:
        with urllib.request.urlopen(CDP_VERSION, timeout=3) as resp:
            data = json.loads(resp.read())
        return True, data.get("Browser", "Chrome"), data
    except urllib.error.URLError as e:
        return False, f"CDP 9222 미응답: {e.reason}", None
    except Exception as e:
        return False, f"CDP probe 오류: {e}", None


def launch_cdp_chrome_macos() -> tuple[bool, str]:
    """CDP 전용 Chrome(chrome-cdp-profile, 9222) 을 백그라운드로 띄운다.

    메인 Chrome(사용자 평소 창)은 절대 건드리지 않는다 — 별도 --user-data-dir
    이라 이미 메인 Chrome 이 떠 있어도 충돌 없이 공존 가능. 실행 후 최대 ~15초
    폴링해 9222 가 응답할 때까지 기다린다.
    """
    import os

    profile_dir = os.path.expanduser("~/chrome-cdp-profile")
    try:
        subprocess.Popen(
            [
                MACOS_CHROME_BIN,
                "--remote-debugging-port=9222",
                f"--user-data-dir={profile_dir}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except FileNotFoundError:
        return False, f"Chrome 실행파일 없음: {MACOS_CHROME_BIN}"
    except Exception as e:
        return False, f"CDP Chrome 기동 실패: {e}"

    for _ in range(15):
        time.sleep(1)
        ok, _, _ = probe_cdp_http()
        if ok:
            return True, "CDP Chrome 자동 기동 성공"
    return False, "CDP Chrome 을 띄웠지만 15초 내 9222 응답 없음 (첫 기동은 프로파일 초기화로 느릴 수 있음 — 잠시 후 재시도)"


def ensure_page_target() -> None:
    """connect_over_cdp는 page target이 0개면 setDownloadBehavior에서 깨진다
    (창을 모두 닫아 windowless로 떠 있는 Chrome). 탭 하나를 보장한다.
    사용자 Chrome은 절대 닫지 않고, 없을 때만 about:blank 탭을 하나 연다."""
    try:
        with urllib.request.urlopen(CDP_TABS, timeout=3) as resp:
            tabs = json.loads(resp.read())
    except Exception:
        return
    if any(t.get("type") == "page" for t in tabs):
        return
    try:
        urllib.request.urlopen(
            urllib.request.Request("http://localhost:9222/json/new?about:blank", method="PUT"),
            timeout=8,
        )
    except Exception:
        pass


def list_tabs() -> list[dict]:
    try:
        with urllib.request.urlopen(CDP_TABS, timeout=3) as resp:
            tabs = json.loads(resp.read())
    except Exception:
        return []
    out = []
    for t in tabs:
        if t.get("type") != "page":
            continue
        out.append({
            "title": (t.get("title") or "").strip()[:80],
            "url": t.get("url"),
        })
    return out


async def probe_host_cookies(host: str) -> tuple[bool, str, list[str]]:
    """
    Playwright 로 컨텍스트에 붙어 host 의 쿠키 존재 여부 확인.
    리턴: (ok, message, cookie_names)
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return False, "playwright 미설치 (pip install playwright + playwright install chromium)", []

    try:
        pw = await async_playwright().start()
    except Exception as e:
        return False, f"playwright start 실패: {e}", []

    try:
        browser = await pw.chromium.connect_over_cdp("http://localhost:9222")
    except Exception as e:
        await pw.stop()
        return False, f"connect_over_cdp 실패: {e}", []

    try:
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        # https://host 쿠키 + .host 도메인 쿠키 모두 확인
        url_https = host if host.startswith("http") else f"https://{host}"
        cookies = await context.cookies(url_https)
        names = sorted({c["name"] for c in cookies})
        if not names:
            return False, f"{host} 쿠키 0개 — 로그인 안 됐거나 다른 도메인일 수 있음", []
        return True, f"{host} 쿠키 {len(names)}개", names
    finally:
        # 사용자 Chrome 은 절대 닫지 않음
        await pw.stop()


def main() -> int:
    ap = argparse.ArgumentParser(description="cdp-anywhere precondition probe")
    ap.add_argument("--host", help="확인할 대상 호스트 (예: x.com, linkedin.com)")
    ap.add_argument("--json", action="store_true", help="JSON 출력 (스크립트 연동용)")
    ap.add_argument(
        "--no-autolaunch",
        action="store_true",
        help="CDP 미응답 시 자동 기동 시도 없이 상태만 보고",
    )
    args = ap.parse_args()

    report: dict = {"cdp": None, "tabs": [], "host": None, "autolaunched": False}

    # 1. CDP HTTP 응답
    ok, msg, ver = probe_cdp_http()

    # 1b. 안 떠 있으면 backup 으로 자동 기동 시도 (macOS). 실패해도 사용자에게 물어보기
    # 전에 한 번은 스스로 띄워본다 — "메인 Chrome" 은 절대 건드리지 않고 별도
    # chrome-cdp-profile 로만 띄우므로 안전.
    if not ok and not args.no_autolaunch and sys.platform == "darwin":
        if not args.json:
            print("⏳ CDP 9222 미응답 — CDP 전용 Chrome(chrome-cdp-profile) 자동 기동 시도 중...")
        launch_ok, launch_msg = launch_cdp_chrome_macos()
        report["autolaunched"] = launch_ok
        if not args.json:
            print(("✅ " if launch_ok else "❌ ") + launch_msg)
        ok, msg, ver = probe_cdp_http()

    report["cdp"] = {"ok": ok, "message": msg}
    if ver:
        report["cdp"]["browser"] = ver.get("Browser")
        report["cdp"]["webSocketDebuggerUrl"] = ver.get("webSocketDebuggerUrl")

    if not ok:
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(f"❌ CDP: {msg}")
            print()
            print("자동 기동도 실패 — 사용자에게 CDP 전용 Chrome 을 직접 띄워달라고 요청:")
            print("  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\")
            print("    --remote-debugging-port=9222 \\")
            print("    --user-data-dir=\"$HOME/chrome-cdp-profile\"")
            print()
            print("(메인/평소 Chrome 이 이미 떠 있는 건 무관 — 별도 프로파일이라 공존함)")
        return 2

    # 2. page target 보장 (windowless Chrome 이면 connect_over_cdp 가 깨지므로)
    ensure_page_target()

    # 3. 열린 탭
    tabs = list_tabs()
    report["tabs"] = tabs

    # 3. 호스트 쿠키 (옵션)
    if args.host:
        try:
            ok_h, msg_h, names = asyncio.run(probe_host_cookies(args.host))
        except Exception as e:
            ok_h, msg_h, names = False, f"호스트 probe 예외: {e}", []
        report["host"] = {
            "host": args.host,
            "ok": ok_h,
            "message": msg_h,
            "cookie_names": names,
        }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if (report["cdp"]["ok"] and (not args.host or report["host"]["ok"])) else 2

    # 사람이 읽는 출력
    print(f"✅ CDP: {report['cdp'].get('browser', 'Chrome')}")
    print(f"   열린 탭 {len(tabs)}개:")
    for t in tabs[:15]:
        print(f"   - {t['title'] or '(untitled)'}\n     {t['url']}")
    if len(tabs) > 15:
        print(f"   ... +{len(tabs) - 15} more")

    if args.host:
        h = report["host"]
        mark = "✅" if h["ok"] else "❌"
        print(f"\n{mark} {h['host']}: {h['message']}")
        if h["cookie_names"]:
            preview = ", ".join(h["cookie_names"][:8])
            extra = "" if len(h["cookie_names"]) <= 8 else f", +{len(h['cookie_names']) - 8} more"
            print(f"   cookies: {preview}{extra}")
        if not h["ok"]:
            return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
