"""Build backend/db/road_segments.geojson from OpenStreetMap (one-off, re-runnable).

    python backend/tools/fetch_osm_segments.py

For each road in ROADS: download its OSM ways inside Thu Duc, merge them into the
longest continuous line, then cut SEGMENTS_PER_ROAD pieces of ~SEGMENT_M metres
from the middle of that line. Needs network + shapely (dev-only dependency).
Data © OpenStreetMap contributors, ODbL 1.0.
"""

import json
import math
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge, substring

OUT = Path(__file__).resolve().parents[1] / "db" / "road_segments.geojson"
OVERPASS = "https://overpass-api.de/api/interpreter"
BBOX = (10.75, 106.715, 10.89, 106.86)  # south, west, north, east: TP Thu Duc
SEGMENT_M = 800
SEGMENTS_PER_ROAD = 2

# Major / frequently flooded roads of TP Thu Duc (former Thu Duc, District 2, District 9).
ROADS = [
    "Kha Vạn Cân", "Võ Văn Ngân", "Đặng Văn Bi", "Tô Ngọc Vân", "Hoàng Diệu 2",
    "Lê Văn Chí", "Phạm Văn Đồng", "Xa lộ Hà Nội", "Lê Văn Việt", "Man Thiện",
    "Đỗ Xuân Hợp", "Nguyễn Duy Trinh", "Trần Não", "Lương Định Của",
    "Nguyễn Thị Định", "Quốc lộ 13",
]

# Equirectangular metres around Thu Duc: accurate to <0.5% over a few km.
LAT0 = math.radians(10.82)
MX, MY = 111_320 * math.cos(LAT0), 110_540


def to_m(coords):
    return [(lon * MX, lat * MY) for lon, lat in coords]


def to_deg(coords):
    return [[round(x / MX, 6), round(y / MY, 6)] for x, y in coords]


def fetch_ways():
    names = "|".join(ROADS)
    query = (
        f'[out:json][timeout:90];'
        f'way["highway"]["name"~"^(Đường )?({names})$",i]{BBOX};'
        f'out geom;'
    )
    req = urllib.request.Request(
        OVERPASS,
        data=urllib.parse.urlencode({"data": query}).encode(),
        headers={"User-Agent": "segment-fetch/1.0"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)["elements"]


def canonical(name):
    lowered = name.lower().removeprefix("đường ").strip()
    return next((r for r in ROADS if r.lower() == lowered), None)


def main():
    by_road = {}
    for way in fetch_ways():
        road = canonical(way.get("tags", {}).get("name", ""))
        if road and len(way.get("geometry", [])) >= 2:
            pts = to_m((g["lon"], g["lat"]) for g in way["geometry"])
            by_road.setdefault(road, []).append(LineString(pts))

    features = []
    for road in ROADS:
        lines = by_road.get(road)
        if not lines:
            print(f"  skip {road}: not found in OSM", file=sys.stderr)
            continue
        merged = linemerge(MultiLineString(lines))
        longest = max(getattr(merged, "geoms", [merged]), key=lambda g: g.length)
        n = min(SEGMENTS_PER_ROAD, int(longest.length // SEGMENT_M))
        start = (longest.length - n * SEGMENT_M) / 2
        for i in range(n):
            piece = substring(longest, start + i * SEGMENT_M, start + (i + 1) * SEGMENT_M)
            features.append({
                "type": "Feature",
                "properties": {
                    "segment_id": f"SEG{len(features) + 1:02d}",
                    "name": f"{road} (đoạn {i + 1})" if n > 1 else road,
                    "road_name": road,
                    "length_m": round(piece.length),
                },
                "geometry": {"type": "LineString", "coordinates": to_deg(piece.coords)},
            })
        print(f"  {road}: {n} segment(s), chain {longest.length / 1000:.1f} km")

    assert 20 <= len(features) <= 40, f"expected 20-40 segments, got {len(features)}"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "type": "FeatureCollection",
        "attribution": "© OpenStreetMap contributors, ODbL 1.0",
        "features": features,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {len(features)} segments -> {OUT}")


if __name__ == "__main__":
    main()
