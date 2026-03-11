from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple


def dump_api_inventory(
    path: str,
    profile: str,
    interface: str,
    channel: str,
    bitrate: int,
    pairs: Dict[Tuple[int, int, int, int, int], Dict[str, float]],
) -> None:
    devices: Dict[Tuple[int, int, int], List[Dict[str, Any]]] = {}
    for (mfg, dtype, did, api_class, api_index), stats in pairs.items():
        key = (mfg, dtype, did)
        duration = max(0.0, stats["last"] - stats["first"])
        fps = (stats["count"] / duration) if duration > 0 else 0.0
        entry = {
            "apiClass": api_class,
            "apiIndex": api_index,
            "count": int(stats["count"]),
            "firstSeen": stats["first"],
            "lastSeen": stats["last"],
            "fps": fps,
        }
        devices.setdefault(key, []).append(entry)

    payload = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time())),
        "profile": profile,
        "interface": interface,
        "channel": channel,
        "bitrate": bitrate,
        "devices": [
            {
                "mfg": mfg,
                "type": dtype,
                "id": did,
                "pairs": sorted(pairs, key=lambda p: (p["apiClass"], p["apiIndex"])),
            }
            for (mfg, dtype, did), pairs in sorted(devices.items())
        ],
    }
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as exc:
        print(f"ERROR: Failed to write API inventory '{path}': {exc}")


def load_inventory(path: str) -> Dict[Tuple[int, int, int, int, int], float]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: Failed to load inventory file '{path}': {exc}")
        return {}
    result: Dict[Tuple[int, int, int, int, int], float] = {}
    for dev in payload.get("devices", []):
        try:
            mfg = int(dev.get("mfg"))
            dtype = int(dev.get("type"))
            did = int(dev.get("id"))
        except Exception:
            continue
        for pair in dev.get("pairs", []):
            try:
                api_class = int(pair.get("apiClass"))
                api_index = int(pair.get("apiIndex"))
                fps = float(pair.get("fps", 0.0))
            except Exception:
                continue
            result[(mfg, dtype, did, api_class, api_index)] = fps
    return result


def print_inventory_diff(path_a: str, path_b: str, top_n: int) -> None:
    a = load_inventory(path_a)
    b = load_inventory(path_b)
    keys_a = set(a.keys())
    keys_b = set(b.keys())

    new_pairs = sorted(keys_b - keys_a)
    missing_pairs = sorted(keys_a - keys_b)
    deltas = []
    for key in sorted(keys_a & keys_b):
        fps_a = a.get(key, 0.0)
        fps_b = b.get(key, 0.0)
        delta = fps_b - fps_a
        deltas.append((abs(delta), delta, key, fps_a, fps_b))
    deltas.sort(reverse=True)

    print("=== Inventory Diff ===")
    print(f"New pairs: {len(new_pairs)}")
    for key in new_pairs[:top_n]:
        mfg, dtype, did, api_class, api_index = key
        print(f"  + mfg={mfg} type={dtype} id={did} apiClass={api_class} apiIndex={api_index}")
    if len(new_pairs) > top_n:
        print(f"  ... {len(new_pairs) - top_n} more")

    print(f"Missing pairs: {len(missing_pairs)}")
    for key in missing_pairs[:top_n]:
        mfg, dtype, did, api_class, api_index = key
        print(f"  - mfg={mfg} type={dtype} id={did} apiClass={api_class} apiIndex={api_index}")
    if len(missing_pairs) > top_n:
        print(f"  ... {len(missing_pairs) - top_n} more")

    print(f"Biggest rate changes (top {top_n}):")
    for _, delta, key, fps_a, fps_b in deltas[:top_n]:
        mfg, dtype, did, api_class, api_index = key
        print(
            "  "
            f"mfg={mfg} type={dtype} id={did} apiClass={api_class} apiIndex={api_index} "
            f"fps={fps_a:.2f} -> {fps_b:.2f} (delta {delta:+.2f})"
        )
