#!/usr/bin/env python3
"""Tuya IoT 클라우드에서 이 기기의 local_key 를 받아 plug_config.json 에 저장.

한 번만 실행하면 된다.

사용법:
    get_local_key.py <ACCESS_ID> <ACCESS_SECRET> <REGION>

REGION: cn(China DC) | us | us-e | eu | eu-w | in
"""
import json
import sys
from pathlib import Path

import tinytuya

CONFIG = Path(__file__).with_name("plug_config.json")


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    api_id, api_secret, region = sys.argv[1], sys.argv[2], sys.argv[3]
    cfg = json.loads(CONFIG.read_text())
    dev_id = cfg["device_id"]

    c = tinytuya.Cloud(apiRegion=region, apiKey=api_id, apiSecret=api_secret,
                       apiDeviceID=dev_id)
    devices = c.getdevices(True)
    if not isinstance(devices, list):
        sys.exit(f"클라우드 오류(리전/키/링크 확인): {devices}")

    match = next((d for d in devices if d.get("id") == dev_id), None)
    if not match:
        ids = [d.get("id") for d in devices]
        sys.exit(f"기기 {dev_id} 를 클라우드에서 못 찾음. Link 된 기기들: {ids}")

    key = match.get("key") or match.get("local_key")
    if not key:
        sys.exit(f"local key 필드 없음: {json.dumps(match, ensure_ascii=False)}")

    cfg["local_key"] = key
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    print(f"OK: local_key 저장 완료 (len={len(key)})")


if __name__ == "__main__":
    main()
