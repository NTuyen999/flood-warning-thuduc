#!/usr/bin/env python3
"""
Exports demo API fixtures to mobile/test/fixtures/ for Dart unit/widget tests.
"""

import json
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.main import app

def main():
    root = Path(__file__).resolve().parent.parent.parent
    fixtures_dir = root / "mobile" / "test" / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    client = TestClient(app)

    # Export maps
    for scenario in ["none", "moderate", "heavy"]:
        res = client.get(f"/api/v1/demo/map?scenario={scenario}")
        assert res.status_code == 200
        path = fixtures_dir / f"demo_map_{scenario}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(res.json(), f, ensure_ascii=False, indent=2)

    # Export routes
    # 1. OK route: P1 -> J2 in none scenario
    res_ok = client.get("/api/v1/demo/route?scenario=none&from=P1&to=J2")
    assert res_ok.status_code == 200
    with open(fixtures_dir / "demo_route_ok.json", "w", encoding="utf-8") as f:
        json.dump(res_ok.json(), f, ensure_ascii=False, indent=2)

    # 2. Detour route: P1 -> J2 in heavy scenario (avoids SEG02 via AL03)
    res_detour = client.get("/api/v1/demo/route?scenario=heavy&from=P1&to=J2")
    assert res_detour.status_code == 200
    with open(fixtures_dir / "demo_route_detour.json", "w", encoding="utf-8") as f:
        json.dump(res_detour.json(), f, ensure_ascii=False, indent=2)

    # 3. Unreachable route: P1 -> P2 in heavy scenario
    res_unreachable = client.get("/api/v1/demo/route?scenario=heavy&from=P1&to=P2")
    assert res_unreachable.status_code == 200
    with open(fixtures_dir / "demo_route_unreachable.json", "w", encoding="utf-8") as f:
        json.dump(res_unreachable.json(), f, ensure_ascii=False, indent=2)

    print(f"Successfully exported all fixtures to {fixtures_dir}")

if __name__ == "__main__":
    main()
