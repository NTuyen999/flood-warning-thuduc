#!/usr/bin/env python3
"""
Generates backend/db/demo_network.json from SEG01 and SEG02 in road_segments.geojson.
Deterministic output with coordinates rounded to 6 decimal places.
"""

import json
import math
from pathlib import Path

# Haversine distance in meters
def haversine_m(coord1, coord2):
    lon1, lat1 = coord1
    lon2, lat2 = coord2
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def round_coords(coords):
    return [[round(c[0], 6), round(c[1], 6)] for c in coords]

def main():
    root = Path(__file__).resolve().parent.parent.parent
    geojson_path = root / "backend" / "db" / "road_segments.geojson"
    out_path = root / "backend" / "db" / "demo_network.json"

    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    seg01 = next(f for f in data["features"] if f["properties"]["segment_id"] == "SEG01")
    seg02 = next(f for f in data["features"] if f["properties"]["segment_id"] == "SEG02")

    coords1 = seg01["geometry"]["coordinates"]
    coords2 = seg02["geometry"]["coordinates"]

    # Key junctions along main road:
    # SEG01 start: idx 0 -> P1
    # SEG01 AL02: idx 6
    # SEG01 AL04: idx 9
    # SEG01 J1 (AL03 start): idx 13
    # SEG01 end / SEG02 start: idx 18 / 0 -> Mid Junction
    # SEG02 J2 (AL03 end): idx 4
    # SEG02 AL01: idx 9
    # SEG02 end: idx 15 -> P2

    # Define Node Table
    nodes = {
        "N_P1": {"id": "N_P1", "name": "Đầu Kha Vạn Cân (đoạn 1)", "coord": round_coords([coords1[0]])[0], "route_point": "P1"},
        "N_AL02_J": {"id": "N_AL02_J", "name": "Nút giao hẻm B", "coord": round_coords([coords1[6]])[0], "route_point": None},
        "N_AL04_J": {"id": "N_AL04_J", "name": "Nút giao hẻm D", "coord": round_coords([coords1[9]])[0], "route_point": None},
        "N_J1": {"id": "N_J1", "name": "Ngã giao hẻm C (J1)", "coord": round_coords([coords1[13]])[0], "route_point": None},
        "N_MID": {"id": "N_MID", "name": "Giữa Kha Vạn Cân (nối SEG01-SEG02)", "coord": round_coords([coords1[18]])[0], "route_point": None},
        "N_J2": {"id": "N_J2", "name": "Ngã giao hẻm tắt (J2)", "coord": round_coords([coords2[4]])[0], "route_point": "J2"},
        "N_AL01_J": {"id": "N_AL01_J", "name": "Nút giao hẻm A", "coord": round_coords([coords2[9]])[0], "route_point": None},
        "N_P2": {"id": "N_P2", "name": "Cuối Kha Vạn Cân (đoạn 2)", "coord": round_coords([coords2[15]])[0], "route_point": "P2"},

        # Alley End Nodes (Route points H1, H2, H4)
        "N_H1": {"id": "N_H1", "name": "Cuối hẻm cụt A (AL01)", "coord": [106.731439, 10.838981], "route_point": "H1"},
        "N_H2": {"id": "N_H2", "name": "Cuối hẻm cụt B (AL02)", "coord": [106.723655, 10.832657], "route_point": "H2"},
        "N_H4": {"id": "N_H4", "name": "Cuối hẻm cụt D (AL04)", "coord": [106.726616, 10.831100], "route_point": "H4"},
    }

    # Main road edges:
    # SEG01 split into 4 parts:
    # E_SEG01_1: P1 -> AL02_J
    # E_SEG01_2: AL02_J -> AL04_J
    # E_SEG01_3: AL04_J -> J1
    # E_SEG01_4: J1 -> MID
    sub_seg01_1 = round_coords(coords1[0:7])
    sub_seg01_2 = round_coords(coords1[6:10])
    sub_seg01_3 = round_coords(coords1[9:14])
    sub_seg01_4 = round_coords(coords1[13:19])

    # SEG02 split into 3 parts:
    # E_SEG02_1: MID -> J2
    # E_SEG02_2: J2 -> AL01_J
    # E_SEG02_3: AL01_J -> P2
    sub_seg02_1 = round_coords(coords2[0:5])
    sub_seg02_2 = round_coords(coords2[4:10])
    sub_seg02_3 = round_coords(coords2[9:16])

    def line_length(pts):
        return sum(haversine_m(pts[i], pts[i+1]) for i in range(len(pts)-1))

    # Alleys:
    # AL01: N_AL01_J -> N_H1 (dead end, inherits_from SEG02)
    al01_coords = round_coords([nodes["N_AL01_J"]["coord"], [106.731939, 10.838481], nodes["N_H1"]["coord"]])

    # AL02: N_AL02_J -> N_H2 (dead end, self flooding, inherits_from null)
    al02_coords = round_coords([nodes["N_AL02_J"]["coord"], [106.724155, 10.832157], nodes["N_H2"]["coord"]])

    # AL03: N_J1 -> N_J2 (through loop alley)
    al03_coords = round_coords([
        nodes["N_J1"]["coord"],
        [106.725800, 10.834600],
        [106.728000, 10.836800],
        [106.729800, 10.837200],
        nodes["N_J2"]["coord"],
    ])

    # AL04: N_AL04_J -> N_H4 (dead end, green, inherits_from null)
    al04_coords = round_coords([nodes["N_AL04_J"]["coord"], [106.726116, 10.831600], nodes["N_H4"]["coord"]])

    edges = [
        # SEG01 main road sections
        {
            "id": "E_SEG01_1",
            "segment_id": "SEG01",
            "name": "Kha Vạn Cân (đoạn 1 - phần 1)",
            "kind": "main",
            "from_node": "N_P1",
            "to_node": "N_AL02_J",
            "length_m": round(line_length(sub_seg01_1), 1),
            "coordinates": sub_seg01_1,
            "inherits_from": None,
            "dead_end": False,
        },
        {
            "id": "E_SEG01_2",
            "segment_id": "SEG01",
            "name": "Kha Vạn Cân (đoạn 1 - phần 2)",
            "kind": "main",
            "from_node": "N_AL02_J",
            "to_node": "N_AL04_J",
            "length_m": round(line_length(sub_seg01_2), 1),
            "coordinates": sub_seg01_2,
            "inherits_from": None,
            "dead_end": False,
        },
        {
            "id": "E_SEG01_3",
            "segment_id": "SEG01",
            "name": "Kha Vạn Cân (đoạn 1 - phần 3)",
            "kind": "main",
            "from_node": "N_AL04_J",
            "to_node": "N_J1",
            "length_m": round(line_length(sub_seg01_3), 1),
            "coordinates": sub_seg01_3,
            "inherits_from": None,
            "dead_end": False,
        },
        {
            "id": "E_SEG01_4",
            "segment_id": "SEG01",
            "name": "Kha Vạn Cân (đoạn 1 - phần 4)",
            "kind": "main",
            "from_node": "N_J1",
            "to_node": "N_MID",
            "length_m": round(line_length(sub_seg01_4), 1),
            "coordinates": sub_seg01_4,
            "inherits_from": None,
            "dead_end": False,
        },

        # SEG02 main road sections
        {
            "id": "E_SEG02_1",
            "segment_id": "SEG02",
            "name": "Kha Vạn Cân (đoạn 2 - phần 1)",
            "kind": "main",
            "from_node": "N_MID",
            "to_node": "N_J2",
            "length_m": round(line_length(sub_seg02_1), 1),
            "coordinates": sub_seg02_1,
            "inherits_from": None,
            "dead_end": False,
        },
        {
            "id": "E_SEG02_2",
            "segment_id": "SEG02",
            "name": "Kha Vạn Cân (đoạn 2 - phần 2)",
            "kind": "main",
            "from_node": "N_J2",
            "to_node": "N_AL01_J",
            "length_m": round(line_length(sub_seg02_2), 1),
            "coordinates": sub_seg02_2,
            "inherits_from": None,
            "dead_end": False,
        },
        {
            "id": "E_SEG02_3",
            "segment_id": "SEG02",
            "name": "Kha Vạn Cân (đoạn 2 - phần 3)",
            "kind": "main",
            "from_node": "N_AL01_J",
            "to_node": "N_P2",
            "length_m": round(line_length(sub_seg02_3), 1),
            "coordinates": sub_seg02_3,
            "inherits_from": None,
            "dead_end": False,
        },

        # Alleys
        {
            "id": "AL01",
            "segment_id": "AL01",
            "name": "Hẻm 112 Kha Vạn Cân (Hẻm cụt A)",
            "kind": "alley",
            "from_node": "N_AL01_J",
            "to_node": "N_H1",
            "length_m": round(line_length(al01_coords), 1),
            "coordinates": al01_coords,
            "inherits_from": "SEG02",
            "dead_end": True,
        },
        {
            "id": "AL02",
            "segment_id": "AL02",
            "name": "Hẻm 45 Kha Vạn Cân (Hẻm cụt B)",
            "kind": "alley",
            "from_node": "N_AL02_J",
            "to_node": "N_H2",
            "length_m": round(line_length(al02_coords), 1),
            "coordinates": al02_coords,
            "inherits_from": None,
            "dead_end": True,
        },
        {
            "id": "AL03",
            "segment_id": "AL03",
            "name": "Hẻm liên thông 78 (Đường vòng tránh ngập)",
            "kind": "alley",
            "from_node": "N_J1",
            "to_node": "N_J2",
            "length_m": round(line_length(al03_coords), 1),
            "coordinates": al03_coords,
            "inherits_from": None,
            "dead_end": False,
        },
        {
            "id": "AL04",
            "segment_id": "AL04",
            "name": "Hẻm 60 Kha Vạn Cân (Hẻm cụt D)",
            "kind": "alley",
            "from_node": "N_AL04_J",
            "to_node": "N_H4",
            "length_m": round(line_length(al04_coords), 1),
            "coordinates": al04_coords,
            "inherits_from": None,
            "dead_end": True,
        },
    ]

    # Verification assertions:
    node_degrees = {}
    for e in edges:
        node_degrees[e["from_node"]] = node_degrees.get(e["from_node"], 0) + 1
        node_degrees[e["to_node"]] = node_degrees.get(e["to_node"], 0) + 1

    assert node_degrees["N_H1"] == 1, "H1 must be dead end"
    assert node_degrees["N_H2"] == 1, "H2 must be dead end"
    assert node_degrees["N_H4"] == 1, "H4 must be dead end"
    assert node_degrees["N_J1"] >= 3, "J1 must be junction"
    assert node_degrees["N_J2"] >= 3, "J2 must be junction"

    # Main road length J1 -> J2
    main_j1_j2_dist = line_length(sub_seg01_4) + line_length(sub_seg02_1)
    al03_dist = line_length(al03_coords)
    ratio = al03_dist / main_j1_j2_dist
    assert 1.25 <= ratio <= 2.5, f"AL03 ratio must be between 1.25 and 2.5, got {ratio:.2f}"

    output = {
        "is_demo": True,
        "nodes": list(nodes.values()),
        "edges": edges,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Successfully generated {out_path} with {len(nodes)} nodes and {len(edges)} edges.")
    print(f"AL03 length: {al03_dist:.1f}m, Main J1-J2 length: {main_j1_j2_dist:.1f}m (ratio: {ratio:.2f}x)")

if __name__ == "__main__":
    main()
