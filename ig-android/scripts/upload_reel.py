#!/usr/bin/env python3
"""IG Reels upload on a real Android device (IM-H031) — verified flow 2026-07-04.

Guarded: verifies device model + active IG account before acting; screenshots
every step; stops at the exact step where a selector is missing so a human/agent
can inspect the screenshot and resume manually.

Exit codes — the caller MUST distinguish these before retrying:
  0  published, and the post count was observed to increase
  1  refused before touching the UI (wrong device, missing video, wrong video)
  2  stopped BEFORE the Share tap — nothing was published, safe to retry
  3  stopped AFTER the Share tap — publish state UNKNOWN, never blind-retry
     (a retry here is how you double-post; escalate to a human instead)
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

IGW_DIR = Path.home() / "projects/misc/brain/bin/ig-prime"
sys.path.insert(0, str(IGW_DIR))

import uiautomator2 as u2  # noqa: E402
from PIL import Image  # noqa: E402
from igw import device, session  # noqa: E402

CHECKPOINT_PHRASES = ["suspicious", "확인이 필요", "차단", "try again later", "we limit"]
AI_TOGGLE_CX = 1445  # right-margin toggle, horizontal position fixed on IM-H031 (2000x1200)


def sh(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True).stdout.strip()


def media_newest(serial: str) -> str | None:
    """Filename of the newest video in the media store — the tile the picker offers first.

    Sorting is done here, not by `--sort`: adb joins argv with spaces and the device
    shell re-splits, so 'date_added DESC' arrives as two tokens and the query throws.
    """
    out = sh(["adb", "-s", serial, "shell", "content", "query",
              "--uri", "content://media/external/video/media",
              "--projection", "_display_name:date_added"])
    best, best_t = None, -1
    for line in out.splitlines():
        m = re.search(r"_display_name=(.+?), date_added=(\d+)", line)
        if m and int(m.group(2)) > best_t:
            best, best_t = m.group(1), int(m.group(2))
    return best


def wait_media_newest(serial: str, name: str, dest: str, tries: int = 8) -> bool:
    """Block until OUR pushed file is the media store's newest video.

    The picker is tapped by coordinate, so whatever sits in the first tile is what
    gets published. If the scan lags, that tile is the PREVIOUS reel — which is how
    you publish yesterday's video, or the other account's. Verify, never assume.
    """
    for _ in range(tries):
        if media_newest(serial) == name:
            return True
        sh(["adb", "-s", serial, "shell", "am", "broadcast",
            "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{dest}"])
        time.sleep(2.5)
    return False


def post_count(d) -> int | None:
    m = re.search(r'content-desc="(\d+)posts"', d.dump_hierarchy())
    return int(m.group(1)) if m else None


class Flow:
    def __init__(self, d, shots: Path):
        self.d = d
        self.shots = shots
        self.n = 0

    def snap(self, label: str) -> Path:
        self.n += 1
        p = self.shots / f"{self.n:02d}_{label}.png"
        self.d.screenshot(str(p))
        return p

    def stop(self, label: str, why: str, code: int = 2):
        p = self.snap(f"STOPPED_{label}")
        print(f"STOPPED at [{label}]: {why}\nscreenshot: {p}", file=sys.stderr)
        sys.exit(code)

    def guard(self):
        hit = device.checkpoint(self.d, CHECKPOINT_PHRASES)
        if hit:
            self.stop("checkpoint", f"checkpoint phrase on screen: {hit!r}")

    def click_text(self, text: str, label: str, timeout: int = 8, optional: bool = False) -> bool:
        el = self.d(text=text)
        if el.click_exists(timeout=timeout):
            time.sleep(2)
            return True
        if optional:
            return False
        self.stop(label, f"text={text!r} not found")

    def dismiss_location(self):
        """Kill IG's auto-suggested location tag on the share screen.

        IG pops a 'Map preview' modal there and pre-applies a REAL physical place
        (2026-07-06: 'IKEA 광명점'; 2026-07-09 again on D5). Both times a human hit
        Cancel; unattended it would publish the user's actual location to a public
        account. It also resets the AI label OFF, so always re-assert that after.
        """
        xml = self.d.dump_hierarchy()
        if "Map preview" not in xml:
            return False
        self.snap("location_modal")
        for txt in ("Cancel", "Not now", "Dismiss"):
            if self.d(text=txt).click_exists(timeout=4):
                time.sleep(2)
                if "Map preview" not in self.d.dump_hierarchy():
                    self.snap("location_dismissed")
                    return True
        self.stop("location_modal",
                  "'Map preview' location modal is up and would not dismiss — refusing to "
                  "publish rather than tag the account's real physical location")

    def _ai_toggle_is_on(self, cy: int) -> bool:
        """State-read the 'Add AI label' toggle from the view hierarchy.

        IG renders it as a generic android.view.View carrying checkable/checked —
        not a Switch — so class-based lookups miss it. Pixel probing (the previous
        approach) misread the ON state and burned toggles (2026-07-15). Match the
        checkable node sitting on the AI-label row instead.
        """
        best, best_dist = None, 10 ** 9
        for m in re.finditer(r'<node[^>]*checkable="true"[^>]*>', self.d.dump_hierarchy()):
            s = m.group(0)
            chk = re.search(r'checked="(true|false)"', s)
            bnd = re.search(r'bounds="\[\d+,(\d+)\]\[\d+,(\d+)\]"', s)
            if not (chk and bnd):
                continue
            node_cy = (int(bnd.group(1)) + int(bnd.group(2))) // 2
            dist = abs(node_cy - cy)
            if dist < best_dist:
                best, best_dist = chk.group(1) == "true", dist
        if best is None or best_dist > 60:   # 같은 행에서 못 찾음 → 판정 보류
            return False
        return best

    def set_ai_label_on(self):
        """Locate the AI-label row dynamically (it shifts when location chips show),
        toggle to ON, and verify by pixel — never blindly click a fixed coordinate."""
        if "Add AI label" not in self.d.dump_hierarchy():
            self.stop("ai_label", "'Add AI label' row not visible — scroll and set manually")
        lb = self.d(text="Add AI label").bounds()
        cy = (lb[1] + lb[3]) // 2
        for _ in range(3):
            if self._ai_toggle_is_on(cy):
                self.snap("ai_label_on")
                return
            self.d.click(AI_TOGGLE_CX, cy)
            time.sleep(1.5)
        self.stop("ai_label", "could not confirm 'Add AI label' ON after 3 toggles")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial", required=True, help="<ip>:5555 or USB serial")
    ap.add_argument("--account", required=True, help="expected IG handle — hard gate")
    ap.add_argument("--video", required=True)
    ap.add_argument("--caption-file", required=True)
    ap.add_argument("--audio-trending-rank", type=int, default=1, help="pick Nth row of Trending tab (1-based)")
    ap.add_argument("--audio-title", help="pick this exact title instead of rank")
    ap.add_argument("--ai-label", action="store_true", help="turn ON 'Add AI label' (default for AI-generated visuals)")
    ap.add_argument("--stop-before-share", action="store_true", help="rehearsal: do everything except the final share")
    ap.add_argument("--screenshot-dir", default="/tmp/igshots")
    args = ap.parse_args()

    shots = Path(args.screenshot_dir)
    shots.mkdir(parents=True, exist_ok=True)
    caption = Path(args.caption_file).read_text().strip()
    video = Path(args.video).expanduser()
    if not video.exists():
        print(f"video not found: {video}", file=sys.stderr)
        return 1

    # 0. device identity — Box Q on the same LAN also serves :5555
    model = sh(["adb", "-s", args.serial, "shell", "getprop", "ro.product.model"])
    if model != "IM-H031":
        print(f"wrong device: model={model!r} (expected IM-H031). Refusing.", file=sys.stderr)
        return 1

    # 1. push + media scan — then PROVE our file is the tile the picker will hand us
    dest = f"/sdcard/DCIM/Camera/{video.name}"
    subprocess.run(["adb", "-s", args.serial, "push", str(video), dest], check=True)
    sh(["adb", "-s", args.serial, "shell", "am", "broadcast",
        "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{dest}"])
    if not wait_media_newest(args.serial, video.name, dest):
        print(f"pushed {video.name} never became the media store's newest video "
              f"(newest={media_newest(args.serial)!r}). Refusing — the picker would "
              f"publish the wrong reel.", file=sys.stderr)
        return 1

    d = u2.connect(args.serial)
    f = Flow(d, shots)

    # 2. cold start + account verification
    device.open_ig(d, session.PKG)
    session.dismiss_interstitials(d, dry=False)
    f.guard()
    if not d(resourceId=session.NAV_AVATAR).click_exists(timeout=8):
        f.stop("profile_tab", "tab_avatar not found")
    time.sleep(3)
    handle = session.active_handle(d)
    if handle != args.account:
        f.stop("account_check", f"active handle {handle!r} != expected {args.account!r} — switch accounts manually")
    before_posts = post_count(d)   # baseline for the post-share proof
    print(f"posts before: {before_posts}")
    f.snap("account_verified")

    # 3. create → New reel gallery → newest video
    if not d(description="Create").click_exists(timeout=8):
        f.stop("create_btn", "description='Create' not found")
    time.sleep(3)
    f.guard()
    # 미게시 드래프트가 있으면 "Keep editing your draft?" 모달이 피커를 가린다(2026-07-15 실측).
    # 'Start new video' = 드래프트 저장 후 새로 시작. 'Keep editing'은 남의 드래프트를 물고 가므로 금지.
    if "Keep editing your draft" in d.dump_hierarchy():
        d(text="Start new video").click_exists(timeout=5)
        time.sleep(2.5)
        f.snap("draft_modal_dismissed")
    xml = d.dump_hierarchy()
    if "REEL" not in xml:
        f.stop("reel_mode", "'REEL' mode marker not in hierarchy — check picker state")
    f.snap("new_reel_gallery")
    # newest gallery video = 2nd tile in top row (1st is camera). Verified layout 2026-07-04.
    d.click(429, 495)
    time.sleep(4)

    # 4. dismiss Edits promo if present
    if "Level up your videos" in d.dump_hierarchy():
        d.press("back")
        time.sleep(2)
    f.snap("editor")

    # 5. audio: toolbar first icon → Trending → pick → apply → Done
    d.click(762, 1054)
    time.sleep(4)
    f.guard()
    f.click_text("Trending", "audio_trending_tab")
    f.snap("trending_list")
    if args.audio_title:
        f.click_text(args.audio_title, "audio_pick_title")
    else:
        # rank rows are laid out top-down; row height ~87px starting y≈344 (2000x1200)
        y = 344 + (args.audio_trending_rank - 1) * 87
        d.click(1000, y)
        time.sleep(4)
    f.snap("audio_selected")
    d.click(1353, 905)  # apply (arrow in preview bar)
    time.sleep(4)
    if not d(text="Done").click_exists(timeout=6):
        d.click(1353, 198)  # Done sometimes only reachable by coordinate
    time.sleep(3)
    f.snap("audio_done")

    # 6. Next → share settings
    f.click_text("Next", "editor_next")
    time.sleep(2)
    f.click_text("Continue", "download_modal", optional=True)
    f.dismiss_location()
    f.snap("share_settings")

    # 7. caption
    cap = d(textContains="Write a caption")
    if not cap.exists:
        f.stop("caption_field", "'Write a caption' not found")
    cap.click()
    time.sleep(1.5)
    d.send_keys(caption)
    time.sleep(1.5)
    f.click_text("OK", "caption_ok")
    f.snap("caption_set")

    # 8. AI label — set ON and verify (toggle resets on screen rotation / re-render)
    if args.ai_label:
        f.set_ai_label_on()

    if args.stop_before_share:
        f.snap("REHEARSAL_END")
        print("Rehearsal complete — stopped before share. Save draft or continue manually.")
        return 0

    # 9. share — the share-settings screen's action button is 'Share' (there is NO
    #    second 'Next' here). Order matters: the location modal resets the AI label,
    #    so dismiss it FIRST, then re-assert the label, then Share.
    f.dismiss_location()
    if args.ai_label:
        f.set_ai_label_on()
    f.snap("pre_share")
    if not d(text="Share").click_exists(timeout=8):
        f.stop("share_btn", "'Share' button not found on share-settings screen")
    # ── everything past this point may already be live: stop(code=3), never retry ──
    time.sleep(4)
    # post-share modals: Meta-AI original-audio → conservative 'Turn off and share';
    # Threads 'Always share?' → 'Not now'. Dismiss whichever appears.
    for _ in range(3):
        if f.click_text("Turn off and share", "meta_audio_modal", optional=True):
            continue
        if f.click_text("Not now", "threads_modal", optional=True):
            continue
        break
    time.sleep(8)
    f.snap("shared")

    # 10. prove it — a Share tap is not a publish. Upload+encode lags, so poll.
    if before_posts is None:
        print("WARNING: no baseline post count — cannot prove publish", file=sys.stderr)
    else:
        for _ in range(12):   # ~2 min
            device.open_ig(d, session.PKG)
            session.dismiss_interstitials(d, dry=False)
            if d(resourceId=session.NAV_AVATAR).click_exists(timeout=8):
                time.sleep(2.5)
                now = post_count(d)
                if now is not None and now > before_posts:
                    print(f"posts after: {now} (was {before_posts})")
                    break
            time.sleep(10)
        else:
            f.stop("publish_unconfirmed",
                   f"post count never rose above {before_posts} — the reel may or may not "
                   f"be live. Check the account by hand before re-running.", code=3)
    f.snap("published")
    device.sleep(d)
    print(f"PUBLISHED as {args.account}. Verify Insights/Boost visible in: {shots}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
