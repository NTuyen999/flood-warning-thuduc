"""
Demo Router for Flood Warning Thu Duc simulation mode.
Prefix: /api/v1/demo
No DB dependency.
"""

import heapq
import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from . import config

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])

TIMEZONE = "Asia/Ho_Chi_Minh"
DISCLAIMER = (
    "Dữ liệu và kết quả định tuyến mang tính MÔ PHỎNG trên khu vực thu nhỏ TP Thủ Đức. "
    "Không cam kết an toàn tuyệt đối."
)
LEVEL_LABELS = {"green": "Thấp", "yellow": "Trung bình", "orange": "Cao", "red": "Rất cao"}
RISK_ORDER = ["green", "yellow", "orange", "red"]

_ROOT = Path(__file__).resolve().parent.parent.parent
_GEOJSON_PATH = _ROOT / "backend" / "db" / "road_segments.geojson"
_NETWORK_PATH = _ROOT / "backend" / "db" / "demo_network.json"
_SCENARIOS_PATH = _ROOT / "backend" / "db" / "demo_scenarios.json"

# Load JSON data into memory at import time
with open(_GEOJSON_PATH, "r", encoding="utf-8") as f:
    _ROAD_SEGMENTS_DATA = json.load(f)

with open(_NETWORK_PATH, "r", encoding="utf-8") as f:
    _NETWORK_DATA = json.load(f)

with open(_SCENARIOS_PATH, "r", encoding="utf-8") as f:
    _SCENARIOS_DATA = json.load(f)


def _risk_level(prob: float | None) -> str | None:
    if prob is None:
        return None
    for max_p, lvl in config.RISK_BANDS:
        if prob < max_p:
            return lvl
    return "red"


def _inherit_level(parent_level: str | None) -> str:
    if parent_level == "red":
        return "red"
    if parent_level == "orange":
        return "yellow"
    return "green"


def _max_level(lvl1: str | None, lvl2: str | None) -> str:
    idx1 = RISK_ORDER.index(lvl1) if lvl1 in RISK_ORDER else -1
    idx2 = RISK_ORDER.index(lvl2) if lvl2 in RISK_ORDER else -1
    return RISK_ORDER[max(idx1, idx2)] if max(idx1, idx2) >= 0 else "green"


def _get_scenario(scenario_id: str) -> dict:
    for s in _SCENARIOS_DATA["scenarios"]:
        if s["id"] == scenario_id:
            return s
    raise HTTPException(422, f"Không có kịch bản '{scenario_id}'. Chọn 'none', 'moderate' hoặc 'heavy'.")


def _get_segment_info(scenario: dict, segment_id: str, horizon: int | None):
    probs = scenario["segment_probabilities"].get(segment_id)
    if not probs:
        probs = [0.02] * 6

    if horizon is not None:
        p = probs[horizon - 1]
    else:
        p = max(probs)
    return p, _risk_level(p)


def _get_effective_edge_state(scenario: dict, edge: dict, horizon: int | None):
    seg_id = edge["segment_id"]

    if edge["kind"] == "alley":
        parent_id = edge.get("inherits_from")
        own_p, own_lvl = _get_segment_info(scenario, seg_id, horizon)

        if parent_id:
            _, parent_lvl = _get_segment_info(scenario, parent_id, horizon)
            inh_lvl = _inherit_level(parent_lvl)
            eff_lvl = _max_level(own_lvl, inh_lvl)
            level_src = own_lvl if own_lvl == eff_lvl else f"inherited:{parent_id}"
        else:
            eff_lvl = own_lvl or "green"
            level_src = "own"

        blocked = (eff_lvl == "red")
        return own_p, eff_lvl, level_src, blocked
    else:
        p, lvl = _get_segment_info(scenario, seg_id, horizon)
        eff_lvl = lvl or "green"
        blocked = (eff_lvl == "red")
        return p, eff_lvl, "own", blocked


@router.get("/scenarios", summary="Danh sách các kịch bản mô phỏng")
def list_scenarios():
    return {
        "is_demo": True,
        "scenarios": [
            {
                "id": s["id"],
                "label": s["label"],
                "description": s["description"],
                "rain_mm_per_h": s["rain_mm_per_h"],
                "banner": s["banner"],
            }
            for s in _SCENARIOS_DATA["scenarios"]
        ],
    }


@router.get("/map", summary="Bản đồ nguy cơ dạng GeoJSON cho kịch bản mô phỏng")
def get_demo_map(
    scenario: Literal["none", "moderate", "heavy"] = Query("heavy"),
    horizon: int | None = Query(None, ge=1, le=6),
):
    sc_data = _get_scenario(scenario)
    issued_at = "2026-11-12T09:00:00+07:00"

    # Mock report summary lookup
    reports_by_seg = {}
    for r in sc_data.get("reports", []):
        sid = r.get("segment_id")
        if sid:
            entry = reports_by_seg.setdefault(sid, {"active": 0, "flooded": 0, "latest_at": None})
            entry["active"] += 1
            if r.get("flood_level") != "none":
                entry["flooded"] += 1
            entry["latest_at"] = r.get("observed_at") or issued_at

    features = []

    # 1. Real 29 segments
    for feat in _ROAD_SEGMENTS_DATA["features"]:
        sid = feat["properties"]["segment_id"]
        name = feat["properties"]["name"]
        p, lvl = _get_segment_info(sc_data, sid, horizon)
        rep = reports_by_seg.get(sid, {"active": 0, "flooded": 0, "latest_at": None})

        features.append({
            "type": "Feature",
            "geometry": feat["geometry"],
            "properties": {
                "segment_id": sid,
                "name": name,
                "probability": p,
                "risk_level": lvl,
                "report_summary": rep,
                "kind": "main",
                "dead_end": False,
                "parent_segment_id": None,
                "level_source": "own",
                "blocked": (lvl == "red"),
                "is_demo": True,
            },
        })

    # 2. Alleys from demo_network
    for edge in _NETWORK_DATA["edges"]:
        if edge["kind"] != "alley":
            continue

        p, eff_lvl, level_src, blocked = _get_effective_edge_state(sc_data, edge, horizon)
        sid = edge["segment_id"]
        rep = reports_by_seg.get(sid, {"active": 0, "flooded": 0, "latest_at": None})

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": edge["coordinates"],
            },
            "properties": {
                "segment_id": sid,
                "name": edge["name"],
                "probability": p,
                "risk_level": eff_lvl,
                "report_summary": rep,
                "kind": "alley",
                "dead_end": edge["dead_end"],
                "parent_segment_id": edge.get("inherits_from"),
                "level_source": level_src,
                "blocked": blocked,
                "is_demo": True,
            },
        })

    bounds = [b for b, _ in config.RISK_BANDS] + [1.0]
    return {
        "type": "FeatureCollection",
        "issued_at": issued_at,
        "horizon": horizon,
        "stale": False,
        "model_version": "demo-scenario",
        "disclaimer": DISCLAIMER,
        "legend": [
            {"level": lvl, "label": LEVEL_LABELS[lvl], "max_probability": b}
            for b, lvl in zip(bounds, LEVEL_LABELS)
        ],
        "features": features,
        "is_demo": True,
    }


@router.get("/forecast/{segment_id}", summary="Dự báo 6 giờ cho đoạn đường/hẻm mô phỏng")
def get_demo_forecast(
    segment_id: str,
    scenario: Literal["none", "moderate", "heavy"] = Query("heavy"),
):
    sc_data = _get_scenario(scenario)
    issued_at = "2026-11-12T09:00:00+07:00"

    # Find name
    name = f"Đoạn đường {segment_id}"
    for f in _ROAD_SEGMENTS_DATA["features"]:
        if f["properties"]["segment_id"] == segment_id:
            name = f["properties"]["name"]
            break
    for e in _NETWORK_DATA["edges"]:
        if e["segment_id"] == segment_id:
            name = e["name"]
            break

    # Calculate 6 horizons
    horizons = []
    alley_edge = next((e for e in _NETWORK_DATA["edges"] if e["segment_id"] == segment_id), None)

    for h in range(1, 7):
        if alley_edge:
            p, lvl, _, _ = _get_effective_edge_state(sc_data, alley_edge, h)
        else:
            p, lvl = _get_segment_info(sc_data, segment_id, h)
            lvl = lvl or "green"
        horizons.append({"h": h, "probability": p, "level": lvl})

    return {
        "segment_id": segment_id,
        "name": name,
        "issued_at": issued_at,
        "timezone": TIMEZONE,
        "model_version": "demo-scenario",
        "is_mock": True,
        "stale": False,
        "horizons": horizons,
        "disclaimer": DISCLAIMER,
        "is_demo": True,
    }


@router.get("/route-points", summary="Danh sách điểm chọn đi/đến có tên trên mạng mô phỏng")
def get_route_points():
    points = []
    for node in _NETWORK_DATA["nodes"]:
        rp = node.get("route_point")
        if rp:
            points.append({
                "id": rp,
                "node_id": node["id"],
                "name": node["name"],
                "coordinates": node["coord"],
            })
    return {"is_demo": True, "items": points}


@router.get("/route", summary="Gợi ý đường đi ít rủi ro hơn trên mạng mô phỏng")
def get_demo_route(
    scenario: Literal["none", "moderate", "heavy"] = Query("heavy"),
    from_point: str = Query("P1", alias="from", description="Tên điểm đi (P1, J2, P2, H1, H2, H4)"),
    to_point: str = Query("J2", alias="to", description="Tên điểm đến (P1, J2, P2, H1, H2, H4)"),
    horizon: int | None = Query(None, ge=1, le=6),
):
    sc_data = _get_scenario(scenario)

    # Find nodes for from_point and to_point
    start_node = next((n for n in _NETWORK_DATA["nodes"] if n.get("route_point") == from_point), None)
    end_node = next((n for n in _NETWORK_DATA["nodes"] if n.get("route_point") == to_point), None)

    if not start_node or not end_node:
        raise HTTPException(422, f"Không tìm thấy điểm đi/đến '{from_point}' hoặc '{to_point}'.")

    # Build adjacency list graph
    # edges list
    edges = _NETWORK_DATA["edges"]
    adj = {n["id"]: [] for n in _NETWORK_DATA["nodes"]}

    for e in edges:
        p, eff_lvl, level_src, blocked = _get_effective_edge_state(sc_data, e, horizon)
        edge_info = {
            "id": e["id"],
            "segment_id": e["segment_id"],
            "name": e["name"],
            "from": e["from_node"],
            "to": e["to_node"],
            "length_m": e["length_m"],
            "coordinates": e["coordinates"],
            "kind": e["kind"],
            "dead_end": e["dead_end"],
            "level": eff_lvl,
            "blocked": blocked,
            "level_source": level_src,
        }
        adj[e["from_node"]].append(edge_info)
        # Bidirectional graph
        reverse_e = dict(edge_info)
        reverse_e["from"] = e["to_node"]
        reverse_e["to"] = e["from_node"]
        reverse_e["coordinates"] = list(reversed(e["coordinates"]))
        adj[e["to_node"]].append(reverse_e)

    # Multipliers for cost
    MULTIPLIERS = {"green": 1.0, "yellow": 1.4, "orange": 4.0, "red": float("inf")}

    def run_dijkstra(use_risk_cost=True):
        """
        Dijkstra algorithm.
        If use_risk_cost=True: cost = length * multiplier, excludes red edges.
        If use_risk_cost=False: cost = length, ignores risk levels.
        Dead-end rule: dead-end alley edge allowed only if start or end node is in that dead-end alley.
        """
        start_id = start_node["id"]
        end_id = end_node["id"]

        # pq: (cost, current_node_id, path_edges)
        pq = [(0.0, start_id, [])]
        best_cost = {n["id"]: float("inf") for n in _NETWORK_DATA["nodes"]}
        best_cost[start_id] = 0.0

        while pq:
            cost, u, path = heapq.heappop(pq)

            if cost > best_cost[u]:
                continue

            if u == end_id:
                return path, cost

            for edge in adj[u]:
                v = edge["to"]

                # Dead-end rule:
                if edge["dead_end"]:
                    # Dead end edge can only be traversed if start_id or end_id is either edge's from or to node
                    if start_id not in (edge["from"], edge["to"]) and end_id not in (edge["from"], edge["to"]):
                        continue

                mult = MULTIPLIERS[edge["level"]] if use_risk_cost else 1.0
                if mult == float("inf"):
                    continue

                edge_cost = edge["length_m"] * mult
                new_cost = cost + edge_cost

                if new_cost < best_cost[v]:
                    best_cost[v] = new_cost
                    heapq.heappush(pq, (new_cost, v, path + [edge]))

        return None, float("inf")

    rec_path, rec_cost = run_dijkstra(use_risk_cost=True)
    short_path, short_cost = run_dijkstra(use_risk_cost=False)

    # Combine coordinates and edges for path
    def build_path_payload(path_edges):
        if not path_edges:
            return None
        total_len = sum(e["length_m"] for e in path_edges)
        eta = round(max(1.0, total_len / 500.0), 1)  # 500 m/min = 30 km/h
        max_lvl = "green"
        coords = []
        edge_ids = []
        for i, e in enumerate(path_edges):
            edge_ids.append(e["id"])
            max_lvl = _max_level(max_lvl, e["level"])
            c_list = e["coordinates"]
            if i > 0:
                c_list = c_list[1:]  # avoid duplicate point at junction
            coords.extend(c_list)
        return {
            "length_m": round(total_len, 1),
            "eta_min": eta,
            "max_level": max_lvl,
            "edges": edge_ids,
            "geometry": {"type": "LineString", "coordinates": coords},
        }

    rec_payload = build_path_payload(rec_path)
    short_payload = build_path_payload(short_path)

    blocked_in_shortest = [e["id"] for e in (short_path or []) if e["blocked"]]

    if short_payload:
        short_payload["blocked_edges"] = blocked_in_shortest

    # Determine status & messages
    messages = []

    if rec_payload is None:
        status = "unreachable"
        messages.append("Không tìm thấy tuyến đường thông suốt do có đoạn bị ngập nặng (mức Đỏ/bị chặn). Cân nhắc hoãn di chuyển.")
    else:
        # Check if shortest path went through blocked/orange edges that recommended avoided
        rec_edge_set = set(rec_payload["edges"])
        short_edge_set = set(short_payload["edges"]) if short_payload else set()

        is_different = (rec_edge_set != short_edge_set)

        is_start_or_end_dead_end_warning = False
        for node in (start_node, end_node):
            if node.get("route_point") in ("H1", "H2", "H4"):
                # check if the alley level is orange/red/yellow
                alley_id = "AL01" if node["route_point"] == "H1" else "AL02" if node["route_point"] == "H2" else "AL04"
                a_edge = next(e for e in edges if e["id"] == alley_id)
                _, a_lvl, _, _ = _get_effective_edge_state(sc_data, a_edge, horizon)
                if a_lvl in ("orange", "red", "yellow"):
                    is_start_or_end_dead_end_warning = True

        if is_different and (blocked_in_shortest or any(e["level"] in ("orange", "red") for e in (short_path or []))):
            status = "detour"
            messages.append("Đã tìm thấy tuyến đường vòng tránh các đoạn ngập lụt / nguy cơ cao.")
        elif is_start_or_end_dead_end_warning:
            status = "warning"
            messages.append("Cảnh báo: Điểm đi/đến nằm trong hẻm cụt có nguy cơ ngập, chú ý khả năng bị kẹt.")
        else:
            status = "ok"
            messages.append("Tuyến đường thông suốt, không có đoạn bị cản trở nghiêm trọng.")

    return {
        "status": status,
        "scenario": scenario,
        "from_point": from_point,
        "to_point": to_point,
        "horizon": horizon,
        "recommended": rec_payload,
        "shortest": short_payload,
        "messages": messages,
        "disclaimer": DISCLAIMER,
        "is_demo": True,
    }
