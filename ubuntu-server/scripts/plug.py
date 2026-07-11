#!/usr/bin/env python3
"""Tuya smart plug 로컬 제어 (v3.5). 같은 LAN(192.168.0.x)에서만 동작.

사용법:
    plug.py status      # 현재 on/off
    plug.py on
    plug.py off

설정은 옆의 plug_config.json 에서 읽는다. local_key 가 비어 있으면 에러.
"""
import json
import sys
from pathlib import Path

import tinytuya

CONFIG = Path(__file__).with_name("plug_config.json")


def load():
    cfg = json.loads(CONFIG.read_text())
    if not cfg.get("local_key"):
        sys.exit("ERROR: plug_config.json 의 local_key 가 비어 있습니다. "
                 "Tuya IoT 클라우드에서 키를 받아 채워주세요 (get_local_key.py 참고).")
    return cfg


def device(cfg):
    d = tinytuya.OutletDevice(cfg["device_id"], cfg["address"], cfg["local_key"])
    d.set_version(float(cfg["version"]))
    d.set_socketTimeout(5)
    return d


def read_state(d, dp):
    st = d.status()
    if not isinstance(st, dict) or "dps" not in st:
        raise RuntimeError(f"플러그 응답 이상: {st}")
    return st["dps"].get(dp)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("status", "on", "off"):
        sys.exit(__doc__)
    action = sys.argv[1]
    cfg = load()
    dp = cfg.get("switch_dp", "1")
    d = device(cfg)

    if action == "status":
        print("on" if read_state(d, dp) else "off")
        return
    d.set_value(dp, action == "on")
    # 확인
    new = read_state(d, dp)
    print("on" if new else "off")


if __name__ == "__main__":
    main()
