"""
Unit tests for Demo Simulation API router (/api/v1/demo/*).
Independent of Database connection.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = ROOT / "mobile" / "test" / "fixtures"


def test_list_scenarios():
    res = client.get("/api/v1/demo/scenarios")
    assert res.status_code == 200
    data = res.json()
    assert data["is_demo"] is True
    scenarios = data["scenarios"]
    assert len(scenarios) == 3
    ids = [s["id"] for s in scenarios]
    assert ids == ["none", "moderate", "heavy"]


def test_demo_map_target_levels():
    # Test none: all green
    res_none = client.get("/api/v1/demo/map?scenario=none")
    assert res_none.status_code == 200
    data_none = res_none.json()
    assert data_none["is_demo"] is True
    for feat in data_none["features"]:
        assert feat["properties"]["risk_level"] == "green"

    # Test moderate
    res_mod = client.get("/api/v1/demo/map?scenario=moderate")
    assert res_mod.status_code == 200
    feats_mod = {f["properties"]["segment_id"]: f["properties"] for f in res_mod.json()["features"]}
    assert feats_mod["SEG01"]["risk_level"] == "yellow"
    assert feats_mod["SEG02"]["risk_level"] == "orange"
    assert feats_mod["AL01"]["risk_level"] == "yellow"
    assert feats_mod["AL01"]["level_source"] == "inherited:SEG02"
    assert feats_mod["AL02"]["risk_level"] == "orange"
    assert feats_mod["AL02"]["level_source"] == "own"
    assert feats_mod["AL03"]["risk_level"] == "green"
    assert feats_mod["AL04"]["risk_level"] == "green"

    # Test heavy
    res_heavy = client.get("/api/v1/demo/map?scenario=heavy")
    assert res_heavy.status_code == 200
    feats_heavy = {f["properties"]["segment_id"]: f["properties"] for f in res_heavy.json()["features"]}
    assert feats_heavy["SEG01"]["risk_level"] == "orange"
    assert feats_heavy["SEG02"]["risk_level"] == "red"
    assert feats_heavy["SEG02"]["blocked"] is True
    assert feats_heavy["AL01"]["risk_level"] == "red"
    assert feats_heavy["AL01"]["level_source"] == "inherited:SEG02"
    assert feats_heavy["AL01"]["blocked"] is True
    assert feats_heavy["AL02"]["risk_level"] == "red"
    assert feats_heavy["AL02"]["level_source"] == "own"
    assert feats_heavy["AL02"]["blocked"] is True
    assert feats_heavy["AL03"]["risk_level"] == "orange"
    assert feats_heavy["AL04"]["risk_level"] == "green"


def test_demo_forecast():
    res = client.get("/api/v1/demo/forecast/SEG02?scenario=heavy")
    assert res.status_code == 200
    data = res.json()
    assert data["segment_id"] == "SEG02"
    assert data["is_mock"] is True
    assert data["is_demo"] is True
    assert len(data["horizons"]) == 6
    assert data["horizons"][-1]["level"] == "red"


def test_demo_route_points():
    res = client.get("/api/v1/demo/route-points")
    assert res.status_code == 200
    data = res.json()
    assert data["is_demo"] is True
    pts = {p["id"]: p for p in data["items"]}
    assert "P1" in pts and "J2" in pts and "P2" in pts
    assert "H1" in pts and "H2" in pts and "H4" in pts


def test_demo_routing_scenarios():
    # 1. P1 -> J2 in none: status == ok (main road shortest)
    r1 = client.get("/api/v1/demo/route?scenario=none&from=P1&to=J2").json()
    assert r1["status"] == "ok"
    assert r1["recommended"]["max_level"] == "green"

    # 2. P1 -> J2 in moderate: status == detour (takes AL03 green instead of SEG02 orange)
    r2 = client.get("/api/v1/demo/route?scenario=moderate&from=P1&to=J2").json()
    assert r2["status"] == "detour"
    assert "AL03" in r2["recommended"]["edges"]

    # 3. P1 -> J2 in heavy: status == detour (takes AL03 orange avoiding SEG02 red)
    r3 = client.get("/api/v1/demo/route?scenario=heavy&from=P1&to=J2").json()
    assert r3["status"] == "detour"

    # 4. P1 -> P2 in heavy: unreachable (all paths must use SEG02 red)
    r4 = client.get("/api/v1/demo/route?scenario=heavy&from=P1&to=P2").json()
    assert r4["status"] == "unreachable"
    assert r4["recommended"] is None

    # 5. P1 -> H1 (AL01 end) in heavy: unreachable (AL01 is red)
    r5 = client.get("/api/v1/demo/route?scenario=heavy&from=P1&to=H1").json()
    assert r5["status"] == "unreachable"

    # 6. P1 -> H2 (AL02 end) in heavy: unreachable (AL02 is red)
    r6 = client.get("/api/v1/demo/route?scenario=heavy&from=P1&to=H2").json()
    assert r6["status"] == "unreachable"

    # 7. P1 -> H4 (AL04 end) in heavy: ok/warning (H4 is green, path via SEG01 orange)
    r7 = client.get("/api/v1/demo/route?scenario=heavy&from=P1&to=H4").json()
    assert r7["status"] in ("ok", "detour", "warning")
    assert r7["recommended"] is not None
    assert "AL04" in r7["recommended"]["edges"]


def test_bbox_and_dead_end_rules():
    res_map = client.get("/api/v1/demo/map?scenario=heavy").json()
    lat_min, lon_min, lat_max, lon_max = 10.70, 106.68, 10.93, 106.90

    for feat in res_map["features"]:
        coords = feat["geometry"]["coordinates"]
        for lon, lat in coords:
            assert lat_min <= lat <= lat_max, f"Latitude {lat} out of Thu Duc BBOX"
            assert lon_min <= lon <= lon_max, f"Longitude {lon} out of Thu Duc BBOX"


def test_fixtures_match():
    # Exported fixtures match current API output
    for scenario in ["none", "moderate", "heavy"]:
        fixture_path = FIXTURES_DIR / f"demo_map_{scenario}.json"
        assert fixture_path.exists(), f"Missing fixture {fixture_path}"
        with open(fixture_path, "r", encoding="utf-8") as f:
            expected = json.load(f)
        actual = client.get(f"/api/v1/demo/map?scenario={scenario}").json()
        assert actual == expected
