#!/usr/bin/env python3
"""IG Reels upload on a real Android device (IM-H031) — verified flow 2026-07-04.

Guarded: verifies device model + active IG account before acting; screenshots
every step; stops (exit 2) at the exact step where a selector is missing so a
human/agent can inspect the screenshot and resume manually.
"""
from __future__ import annotations

import argparse
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

    def stop(self, label: str, why: str):
        p = self.snap(f"STOPPED_{label}")
        print(f"STOPPED at [{label}]: {why}\nscreenshot: {p}", file=sys.stderr)
        sys.exit(2)

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

    def _ai_toggle_is_on(self, cy: int) -> bool:
        """State-read the 'Add AI label' toggle by pixel: ON = bright knob at the
        right end of the track, OFF = dark gray track there. Robust to row shift."""
        p = self.shots / "_ailabel_probe.png"
        self.d.screenshot(str(p))
        img = Image.open(p).convert("RGB")
        w, h = img.size
        vals = []
        for x in (AI_TOGGLE_CX + 22, AI_TOGGLE_CX + 26, AI_TOGGLE_CX + 30):
            for y in (cy - 2, cy, cy + 2):
                if 0 <= x < w and 0 <= y < h:
                    r, g, b = img.getpixel((x, y))
                    vals.append((r + g + b) / 3)
        return bool(vals) and (sum(vals) / len(vals)) > 165

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

    # 1. push + media scan
    dest = f"/sdcard/DCIM/Camera/{video.name}"
    subprocess.run(["adb", "-s", args.serial, "push", str(video), dest], check=True)
    sh(["adb", "-s", args.serial, "shell", "am", "broadcast",
        "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{dest}"])

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
    f.snap("account_verified")

    # 3. create → New reel gallery → newest video
    if not d(description="Create").click_exists(timeout=8):
        f.stop("create_btn", "description='Create' not found")
    time.sleep(3)
    f.guard()
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
    #    second 'Next' here). Re-verify AI label ON right before publishing, then Share.
    if args.ai_label:
        f.set_ai_label_on()
    f.snap("pre_share")
    if not d(text="Share").click_exists(timeout=8):
        f.stop("share_btn", "'Share' button not found on share-settings screen")
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
    f.snap("published")
    device.sleep(d)
    print(f"PUBLISHED as {args.account}. Verify Insights/Boost visible in: {shots}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
