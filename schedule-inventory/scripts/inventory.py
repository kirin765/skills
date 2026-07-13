#!/usr/bin/env python3
"""Read-only inventory of every scheduling surface on this Mac:
   Claude Code file-routines, user/system launchd, and cron.
   Prints a consolidated, sectioned report. Changes nothing."""
import os, glob, plistlib, subprocess, re

HOME = os.path.expanduser("~")

def sh(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=25).stdout
    except Exception:
        return ""

# ---------- launchctl loaded state: label -> (pid, last_exit) ----------
def launchctl_state():
    m = {}
    for line in sh(["launchctl", "list"]).splitlines()[1:]:
        p = line.split("\t")
        if len(p) >= 3:
            m[p[2]] = (p[0], p[1])
    return m

def fmt_schedule(pl):
    if "StartInterval" in pl:
        s = pl["StartInterval"]
        return f"every {s}s (~{s//60}m)" if isinstance(s, int) else f"every {s}"
    if "StartCalendarInterval" in pl:
        sci = pl["StartCalendarInterval"]
        items = sci if isinstance(sci, list) else [sci]
        out = []
        for it in items:
            h = it.get("Hour"); mi = it.get("Minute", 0)
            t = f"{h if h is not None else '*'}:{mi:02d}" if isinstance(mi, int) else f"{h}:{mi}"
            extra = []
            if "Weekday" in it: extra.append(f"wday={it['Weekday']}")
            if "Day" in it:     extra.append(f"day={it['Day']}")
            if "Month" in it:   extra.append(f"mon={it['Month']}")
            out.append(t + (" " + " ".join(extra) if extra else ""))
        return "at " + ", ".join(out)
    if pl.get("RunAtLoad") and pl.get("KeepAlive"): return "RunAtLoad+KeepAlive (long-running daemon)"
    if pl.get("KeepAlive"): return "KeepAlive (long-running)"
    if pl.get("RunAtLoad"): return "RunAtLoad (at login/load)"
    if pl.get("WatchPaths"): return "WatchPaths " + str(pl["WatchPaths"])
    return "on-demand/trigger"

def flag_exit(status):
    # '0' last run ok, '-' na/never, anything else = failed/killed last run
    if status in ("0", "-"):
        return ""
    return "  ⚠ last-exit=" + status

def program(pl):
    if "ProgramArguments" in pl:
        return " ".join(str(a) for a in pl["ProgramArguments"])
    return str(pl.get("Program", ""))

def launchd_section(title, pattern, state, brief=False):
    files = sorted(glob.glob(pattern))
    labels = []
    print(f"\n===== {title} ({len(files)}) =====")
    for f in files:
        try:
            with open(f, "rb") as fh:
                pl = plistlib.load(fh)
        except Exception as e:
            print(f"  • {os.path.basename(f)}  (unreadable: {e})")
            continue
        label = pl.get("Label", os.path.basename(f).replace(".plist", ""))
        labels.append(label)
        pid, status = state.get(label, ("-", "-"))
        loaded = "loaded" if label in state else "NOT loaded"
        if brief:
            print(f"  • {label}  [{loaded}]{flag_exit(status)}")
            continue
        print(f"  • {label}")
        print(f"      schedule: {fmt_schedule(pl)}")
        print(f"      run:      {program(pl)[:110]}")
        line = f"      state:    {loaded}, pid={pid}, last-exit={status}"
        if flag_exit(status):
            line += "  ⚠ FAILED/killed on last run"
        print(line)
        log = pl.get("StandardErrorPath") or pl.get("StandardOutPath")
        if log and flag_exit(status):
            print(f"      log:      {log}")
    return labels

def routines_section():
    for label, base in (("ACTIVE", "scheduled-tasks"), ("DISABLED", "scheduled-tasks-disabled")):
        root = os.path.join(HOME, ".claude", base)
        dirs = sorted(d for d in glob.glob(root + "/*") if os.path.isdir(d))
        print(f"\n===== Claude Code file-routines — {label} ({len(dirs)}) =====")
        for d in dirs:
            name = os.path.basename(d)
            desc = ""
            sk = os.path.join(d, "SKILL.md")
            if os.path.exists(sk):
                with open(sk, encoding="utf-8", errors="replace") as fh:
                    for ln in fh:
                        mo = re.match(r"^description:\s*(.*)", ln)
                        if mo:
                            desc = mo.group(1).strip()
                            break
            print(f"  • {name}")
            if desc:
                print(f"      {desc}")
    print("\n  ↳ 권위 메타(schedule·enabled·lastRunAt·nextRunAt)는 `mcp__scheduled-tasks__list_scheduled_tasks`")
    print("    (무인 루틴 실행 컨텍스트에서만 주입). 위 목록은 파일 정의 + description의 스케줄 산문.")

def cron_section():
    out = sh(["crontab", "-l"])
    lines = [l for l in out.splitlines() if l.strip() and not l.strip().startswith("#")]
    print(f"\n===== user crontab ({len(lines)}) =====")
    print("  " + "\n  ".join(lines) if lines else "  (none)")

def main():
    state = launchctl_state()
    print("# Scheduler inventory —", sh(["date", "+%Y-%m-%d %H:%M %Z"]).strip())
    routines_section()
    mine = launchd_section("user launchd  ~/Library/LaunchAgents", HOME + "/Library/LaunchAgents/*.plist", state)
    launchd_section("system launchd  /Library/LaunchAgents", "/Library/LaunchAgents/*.plist", state, brief=True)
    launchd_section("system launchd  /Library/LaunchDaemons", "/Library/LaunchDaemons/*.plist", state, brief=True)
    cron_section()
    # failure roll-up — only user-managed agents (Apple/Google on-demand agents exit -9 when idle: noise)
    fails = [l for l in mine if state.get(l, ("-", "-"))[1] not in ("0", "-")]
    print("\n===== ⚠ 내 루틴 마지막 실행 실패/종료 (user launchd only) =====")
    if fails:
        for lbl in fails:
            print(f"  • {lbl}  (exit {state[lbl][1]})")
    else:
        print("  (none — 전부 정상)")

if __name__ == "__main__":
    main()
