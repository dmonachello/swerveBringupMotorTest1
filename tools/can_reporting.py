from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional, Tuple

from can_analyzer import CanLiveAnalyzer
from can_nt_publish import decode_frc_ext_id
from can_state import SnifferState


def print_or_dump_nt_keys(devices, print_keys: bool, dump_path: str) -> None:
    keys = []
    for spec in devices:
        base = f"bringup/diag/dev/{spec['manufacturer']}/{spec['device_type']}/{spec['device_id']}"
        keys.extend(
            [
                f"{base}/label",
                f"{base}/status",
                f"{base}/ageSec",
                f"{base}/msgCount",
                f"{base}/lastSeen",
                f"{base}/presenceSource",
                f"{base}/presenceConfidence",
                f"{base}/trafficAgeSec",
                f"{base}/statusAgeSec",
                f"{base}/manufacturer",
                f"{base}/deviceType",
                f"{base}/deviceId",
            ]
        )
    keys.append("bringup/diag/can/summary/json")
    keys.extend(
        [
            "bringup/diag/can/pc/heartbeat",
            "bringup/diag/can/pc/openOk",
            "bringup/diag/can/pc/framesPerSec",
            "bringup/diag/can/pc/framesTotal",
            "bringup/diag/can/pc/readErrors",
            "bringup/diag/can/pc/lastFrameAgeSec",
            "bringup/diag/console/(dynamic keys per rule/device)",
            "bringup/diag/console/reset",
        ]
    )
    payload = {
        "keys": keys,
        "count": len(keys),
    }
    if print_keys:
        print("NetworkTables keys published by can_nt_bridge.py:")
        for key in keys:
            print(f"  {key}")
    if dump_path:
        try:
            with open(dump_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as exc:
            print(f"ERROR: Failed to write NT keys dump '{dump_path}': {exc}")
        print(f"Wrote NT key inventory to {dump_path}")


def print_status_transitions(
    devices,
    last_seen: Dict[Tuple[int, int, int], float],
    status_last_seen: Dict[Tuple[int, int, int], float],
    control_last_seen: Dict[Tuple[int, int, int], float],
    now: float,
    timeout_s: float,
    last_status: Dict[Tuple[int, int, int], str],
    uses_status_presence,
) -> None:
    for spec in devices:
        key = (spec["manufacturer"], spec["device_type"], spec["device_id"])
        traffic_ts = last_seen.get(key)
        status_ts = status_last_seen.get(key)
        control_ts = control_last_seen.get(key)
        ts = status_ts if uses_status_presence(key[0], key[1]) else traffic_ts
        if ts is None:
            status = "CONTROL_ONLY" if control_ts is not None else "MISSING"
        else:
            status = "OK" if (now - ts) < timeout_s else "MISSING"
        prev = last_status.get(key)
        if prev is None:
            last_status[key] = status
            continue
        if prev != status:
            label = spec.get("label", "")
            if status == "OK":
                print(f"[seen] {label} mfg={key[0]} type={key[1]} id={key[2]}")
            else:
                print(f"[missing] {label} mfg={key[0]} type={key[1]} id={key[2]} ({status})")
        last_status[key] = status


def build_device_label_map(devices: List[Dict[str, Any]]) -> Dict[Tuple[int, int, int], str]:
    labels: Dict[Tuple[int, int, int], str] = {}
    for dev in devices:
        try:
            key = (int(dev["manufacturer"]), int(dev["device_type"]), int(dev["device_id"]))
            label = str(dev.get("label", "")).strip()
            if label:
                labels[key] = label
        except Exception:
            continue
    return labels


def format_frame_line(
    kind: str,
    arb_id: int,
    mfg: int,
    dtype: int,
    device_id: int,
    api_class: int,
    api_index: int,
    data: bytes,
    label: str,
) -> str:
    mfg_names = {
        1: "NI",
        4: "CTRE",
        5: "REV",
    }
    type_names = {
        2: "MotorController",
        8: "Pneumatics",
    }
    mfg_name = mfg_names.get(mfg)
    type_name = type_names.get(dtype)

    label_text = f" {label}" if label else ""
    mfg_text = f" mfgName={mfg_name}" if mfg_name else ""
    type_text = f" typeName={type_name}" if type_name else ""
    return (
        f"[{kind}] id=0x{arb_id:X}"
        f"{label_text} mfg={mfg}{mfg_text} type={dtype}{type_text} "
        f"devId={device_id} apiClass={api_class} apiIndex={api_index} "
        f"len={len(data)} data={data.hex()}"
    )


def format_can_id(can_id_hex: str, labels: Dict[Tuple[int, int, int], str]) -> str:
    try:
        can_id = int(can_id_hex, 16)
    except Exception:
        return f"id={can_id_hex}"
    mfg, dtype, did = decode_frc_ext_id(can_id)
    label = labels.get((mfg, dtype, did), "")
    label_part = f"{label} " if label else ""
    mfg_names = {
        1: "NI",
        4: "CTRE",
        5: "REV",
    }
    type_names = {
        2: "MotorController",
        8: "Pneumatics",
    }
    mfg_name = mfg_names.get(mfg)
    type_name = type_names.get(dtype)
    mfg_text = f" mfgName={mfg_name}" if mfg_name else ""
    type_text = f" typeName={type_name}" if type_name else ""
    return f"{label_part}mfg={mfg}{mfg_text} type={dtype}{type_text} id={did} can={can_id_hex}"


def get_bus_dropped(bus) -> Optional[int]:
    for attr in ("dropped_frames", "drop_count", "rx_overflow", "rx_dropped"):
        value = getattr(bus, attr, None)
        if isinstance(value, int):
            return value
    return None


def build_summary_extra(
    summary: Dict[str, Any],
    devices: List[Dict[str, Any]],
    analyzer: CanLiveAnalyzer,
    state: SnifferState,
    bus,
    bitrate: int,
) -> Dict[str, Any]:
    bytes_per_s = summary.get("bus", {}).get("bytes_per_s", 0.0)
    bus_load_pct = None
    if isinstance(bytes_per_s, (int, float)) and bitrate > 0:
        bus_load_pct = (bytes_per_s * 8.0 / float(bitrate)) * 100.0
    known_keys = {(d["manufacturer"], d["device_type"], d["device_id"]) for d in devices}
    seen_keys = {decode_frc_ext_id(cid) for cid in analyzer.seen_ids()}
    unknown_keys = seen_keys - known_keys
    return {
        "bus_load_pct": bus_load_pct,
        "read_errors": state.read_errors,
        "pcap_errors": state.pcap_errors,
        "dropped": get_bus_dropped(bus),
        "seen_devices": len(seen_keys),
        "unknown_devices": len(unknown_keys),
    }


def print_summary(
    summary,
    now: float,
    labels: Dict[Tuple[int, int, int], str],
    extra: Dict[str, Any],
) -> None:
    bus = summary.get("bus", {})
    health = summary.get("health", {})
    top = summary.get("top", [])
    total = bus.get("fps")
    missing = health.get("missing", [])
    ts = time.strftime("%H:%M:%S", time.localtime(now))
    bus_load = extra.get("bus_load_pct")
    bus_load_text = f"{bus_load:.1f}%" if isinstance(bus_load, (int, float)) else "n/a"
    dropped = extra.get("dropped")
    dropped_text = str(dropped) if isinstance(dropped, int) else "n/a"
    print(
        f"[summary {ts}] fps={total} missing={len(missing)} top={len(top)} "
        f"busLoad={bus_load_text} readErr={extra.get('read_errors', 0)} "
        f"pcapErr={extra.get('pcap_errors', 0)} dropped={dropped_text} "
        f"seen={extra.get('seen_devices', 0)} unknown={extra.get('unknown_devices', 0)}"
    )
    for row in top[:5]:
        try:
            print(
                "  "
                f"{format_can_id(row.get('id', ''), labels)} "
                f"hz={row.get('hz')}"
            )
        except Exception:
            continue
