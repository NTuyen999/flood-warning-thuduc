"""API tests against a real PostGIS test database.

    docker compose up -d db
    docker compose exec db psql -U flood -c "CREATE DATABASE flood_test"   # once
    python -m pytest backend/tests -v

Runs the real app in uvicorn on a free port and talks HTTP with urllib. The ML inference
(Open-Meteo + XGBoost) is replaced by a fixed fake so tests need no network.
"""

import json
import os
import socket
import statistics
import tempfile
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

os.environ.setdefault(
    "DATABASE_URL", "postgresql://flood:flood_dev_pw@127.0.0.1:5433/flood_test"
)
os.environ["ADMIN_TOKEN"] = "test-admin-token"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="flood-uploads-")

import pytest  # noqa: E402
import uvicorn  # noqa: E402

from backend.app import db, forecast, main  # noqa: E402

PROBS = [0.05, 0.12, 0.31, 0.48, 0.66, 0.40]
LEVELS = ["green", "yellow", "orange", "orange", "red", "orange"]
INFER_CALLS = []


def fake_infer(reference_time, probs=PROBS):
    INFER_CALLS.append(reference_time)
    time.sleep(0.2)  # long enough for concurrent requests to pile up on the lock
    shap = [
        {"feature": "rain_last_3h", "input_value": 12.5, "shap_log_odds": 1.2,
         "effect_on_raw_score": "increases"},
        {"feature": "relative_humidity_2m", "input_value": 90.0, "shap_log_odds": -0.3,
         "effect_on_raw_score": "decreases"},
    ]
    weather = {k: 1.0 for k in forecast.WEATHER_FIELDS}
    return weather, [
        {"horizon": h, "calibrated_event_probability": p, "top_shap_features": shap}
        for h, p in enumerate(probs, 1)
    ]


@pytest.fixture(scope="session")
def base():
    mp = pytest.MonkeyPatch()
    mp.setattr(forecast, "_infer", fake_infer)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 30
    while not server.started:
        assert time.time() < deadline, "server did not start"
        time.sleep(0.05)
    with db.pool.connection() as conn:
        conn.execute("TRUNCATE reports, users, predictions, prediction_explanations, "
                     "weather_hourly RESTART IDENTITY")
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(10)
    mp.undo()


def call(base, method, path, body=None, headers=None, raw=None, content_type="application/json"):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(base + path, data=data, method=method,
                                 headers={"Content-Type": content_type, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            payload = r.read()
            return r.status, json.loads(payload) if payload.startswith((b"{", b"[")) else payload
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def upload(base, data, filename="photo.jpg"):
    boundary = "----floodtestboundary"
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
    return call(base, "POST", "/api/v1/uploads", raw=body,
                content_type=f"multipart/form-data; boundary={boundary}")


def segment_point(base, segment_id="SEG01"):
    _, seg = call(base, "GET", f"/api/v1/road-segments/{segment_id}")
    lon, lat = seg["geometry"]["coordinates"][1]
    return lat, lon


def shift_reference(monkeypatch, hours):
    real = forecast.live.get_reference_time
    monkeypatch.setattr(forecast.live, "get_reference_time",
                        lambda: real() + timedelta(hours=hours))


def iso(dt):
    return dt.isoformat()


# ------------------------------------------------------------
# GIS + system
# ------------------------------------------------------------

def test_health_and_segments(base):
    status, health = call(base, "GET", "/health")
    assert status == 200 and health["db"] == "ok"
    assert health["model_version"].startswith("xgb-final-")

    status, fc = call(base, "GET", "/api/v1/road-segments")
    assert status == 200 and fc["type"] == "FeatureCollection"
    ids = [f["properties"]["segment_id"] for f in fc["features"]]
    assert 20 <= len(ids) <= 40 and len(set(ids)) == len(ids)
    for f in fc["features"]:
        assert f["geometry"]["type"] == "LineString" and len(f["geometry"]["coordinates"]) >= 2
        assert f["properties"]["name"] and f["properties"]["road_name"]

    with db.pool.connection() as conn:
        row = conn.execute(
            "SELECT bool_and(ST_IsValid(geom)) AS valid, "
            "bool_and(ST_Within(geom, ST_MakeEnvelope(106.68, 10.70, 106.90, 10.93, 4326))) AS inside "
            "FROM road_segments").fetchone()
    assert row["valid"] and row["inside"]

    assert call(base, "GET", "/api/v1/road-segments/NOPE")[0] == 404


# ------------------------------------------------------------
# Forecast, model serving, prediction store
# ------------------------------------------------------------

def test_forecast_contract(base):
    status, fc = call(base, "GET", "/api/v1/forecast/SEG01")
    assert status == 200
    assert fc["segment_id"] == "SEG01" and fc["is_mock"] is False and fc["stale"] is False
    assert [h["h"] for h in fc["horizons"]] == [1, 2, 3, 4, 5, 6]
    assert [h["level"] for h in fc["horizons"]] == LEVELS
    assert fc["horizons"][0]["probability"] == pytest.approx(0.05)
    assert datetime.fromisoformat(fc["issued_at"]).utcoffset() == timedelta(hours=7)
    assert call(base, "GET", "/api/v1/forecast/NOPE")[0] == 404


def test_inference_once_per_hour_and_history_kept(base, monkeypatch):
    with db.pool.connection() as conn:
        n_segments = conn.execute("SELECT count(*) AS n FROM road_segments").fetchone()["n"]

    # Next hour: 10 concurrent requests must trigger exactly one inference.
    shift_reference(monkeypatch, 1)
    monkeypatch.setattr(forecast, "_infer", lambda t: fake_infer(t, [0.9] * 6))
    before = len(INFER_CALLS)
    with ThreadPoolExecutor(10) as ex:
        results = list(ex.map(lambda _: call(base, "GET", "/api/v1/forecast/SEG02"), range(10)))
    assert all(s == 200 for s, _ in results)
    assert len(INFER_CALLS) - before == 1
    assert results[0][1]["horizons"][0]["level"] == "red"

    with db.pool.connection() as conn:
        rows = conn.execute("SELECT issued_at, count(*) AS n FROM predictions "
                            "GROUP BY issued_at ORDER BY issued_at").fetchall()
    assert [r["n"] for r in rows] == [n_segments * 6, n_segments * 6]  # old hour untouched

    status, hist = call(base, "GET", "/api/v1/predictions?segment_id=SEG02&horizon=1")
    assert status == 200 and hist["count"] == 2
    assert [i["probability"] for i in hist["items"]] == pytest.approx([0.9, 0.05])  # newest first

    newest = hist["items"][0]["issued_at"]
    status, only_new = call(base, "GET", "/api/v1/predictions?segment_id=SEG02&horizon=1&start="
                            + urllib.request.quote(newest))
    assert status == 200 and only_new["count"] == 1
    assert call(base, "GET", "/api/v1/predictions?segment_id=SEG02&start=2026-02-01T00:00:00"
                             "&end=2026-01-01T00:00:00")[0] == 422
    assert call(base, "GET", "/api/v1/predictions?segment_id=NOPE")[0] == 404


def test_stale_fallback_when_weather_source_down(base, monkeypatch):
    def broken(_t):
        raise RuntimeError("Open-Meteo down")

    monkeypatch.setattr(forecast, "_infer", broken)
    shift_reference(monkeypatch, 2)  # latest stored run (+1h) is 1 hour old -> served as stale
    status, fc = call(base, "GET", "/api/v1/forecast/SEG01")
    assert status == 200 and fc["stale"] is True

    shift_reference(monkeypatch, 6)  # nothing within 3 hours -> 503, not a 500
    status, err = call(base, "GET", "/api/v1/forecast/SEG01")
    assert status == 503 and "detail" in err


def test_weather_and_explain(base):
    status, w = call(base, "GET", "/api/v1/weather/current")
    assert status == 200 and w["is_verified_observation"] is False
    assert set(forecast.WEATHER_FIELDS) <= set(w)

    status, ex = call(base, "GET", "/api/v1/explain/SEG01?horizon=3")
    assert status == 200 and ex["horizon"] == 3 and ex["level"] == "orange"
    first = ex["features"][0]
    assert first["feature"] == "rain_last_3h" and first["direction"] == "increases"
    assert first["text"] == "Tổng mưa 3 giờ qua = 12.5 mm → làm tăng nguy cơ"
    assert ex["features"][1]["direction"] == "decreases"
    assert call(base, "GET", "/api/v1/explain/SEG01?horizon=7")[0] == 422


# ------------------------------------------------------------
# Community reports
# ------------------------------------------------------------

def test_report_create_snap_and_duplicates(base):
    lat, lon = segment_point(base, "SEG05")
    report = {"lat": lat, "lon": lon, "flood_level": "light", "note": "Ngập tới mắt cá"}

    status, r = call(base, "POST", "/api/v1/reports", report)
    assert status == 201, r
    assert r["segment_id"] == "SEG05" and r["status"] == "new" and r["age_minutes"] == 0

    status, dup = call(base, "POST", "/api/v1/reports", report)
    assert status == 409 and dup["detail"]["duplicate_of"] == r["id"]

    # Same place, per-device de-duplication.
    assert call(base, "POST", "/api/v1/reports", report | {"device_id": "device-AAAA"})[0] == 201
    assert call(base, "POST", "/api/v1/reports", report | {"device_id": "device-AAAA"})[0] == 409
    assert call(base, "POST", "/api/v1/reports", report | {"device_id": "device-BBBB"})[0] == 201
    # Different flood level is new information, not a duplicate.
    assert call(base, "POST", "/api/v1/reports", report | {"flood_level": "heavy"})[0] == 201

    status, listed = call(base, "GET", "/api/v1/reports?segment_id=SEG05")
    assert status == 200 and listed["count"] == 4

    status, m = call(base, "GET", "/api/v1/map/risks")
    seg5 = next(f for f in m["features"] if f["properties"]["segment_id"] == "SEG05")
    assert seg5["properties"]["report_summary"]["active"] == 4
    assert seg5["properties"]["report_summary"]["flooded"] == 4
    assert [lg["level"] for lg in m["legend"]] == ["green", "yellow", "orange", "red"]
    assert all(f["properties"]["risk_level"] for f in m["features"])


@pytest.mark.parametrize("patch, reason", [
    ({"lat": 10.30, "lon": 106.60}, "outside Thu Duc"),
    ({"flood_level": "tsunami"}, "bad level"),
    ({"segment_id": "NOPE"}, "unknown segment"),
    ({"note": "x" * 501}, "note too long"),
    ({"image_url": "http://evil.example/a.jpg"}, "foreign image url"),
    ({"image_url": "/uploads/" + "a" * 32 + ".jpg"}, "image not uploaded"),
    ({"observed_at": "FUTURE"}, "future time"),
    ({"observed_at": "OLD"}, "older than TTL"),
])
def test_report_validation(base, patch, reason):
    now = forecast.now_local()
    times = {"FUTURE": iso(now + timedelta(hours=1)), "OLD": iso(now - timedelta(hours=7))}
    if "observed_at" in patch:
        patch = {"observed_at": times[patch["observed_at"]]}
    body = {"lat": 10.85, "lon": 106.77, "flood_level": "none"} | patch
    assert call(base, "POST", "/api/v1/reports", body)[0] == 422, reason


def test_report_expiry_and_moderation(base):
    lat, lon = segment_point(base, "SEG07")
    _, fresh = call(base, "POST", "/api/v1/reports", {"lat": lat, "lon": lon, "flood_level": "heavy"})
    _, old = call(base, "POST", "/api/v1/reports", {
        "lat": lat, "lon": lon, "flood_level": "none",
        "observed_at": iso(forecast.now_local() - timedelta(hours=5))})
    with db.pool.connection() as conn:  # let 2 hours pass for the old report
        conn.execute("UPDATE reports SET observed_at = observed_at - interval '2 hours' WHERE id = %s",
                     (old["id"],))

    _, listed = call(base, "GET", "/api/v1/reports?segment_id=SEG07")
    by_id = {r["id"]: r["status"] for r in listed["items"]}
    assert by_id == {fresh["id"]: "new", old["id"]: "expired"}

    path = f"/api/v1/reports/{fresh['id']}/status"
    assert call(base, "PATCH", path, {"status": "verified"})[0] == 401
    assert call(base, "PATCH", path, {"status": "verified"}, {"X-Admin-Token": "wrong"})[0] == 401
    admin = {"X-Admin-Token": "test-admin-token"}
    status, r = call(base, "PATCH", path, {"status": "verified"}, admin)
    assert status == 200 and r["status"] == "verified"
    assert call(base, "PATCH", path, {"status": "expired"}, admin)[0] == 422
    assert call(base, "PATCH", f"/api/v1/reports/{old['id']}/status", {"status": "verified"}, admin)[0] == 409
    assert call(base, "PATCH", "/api/v1/reports/999999/status", {"status": "verified"}, admin)[0] == 404

    assert call(base, "PATCH", path, {"status": "rejected"}, admin)[0] == 200
    _, listed = call(base, "GET", "/api/v1/reports?segment_id=SEG07")
    assert [r["id"] for r in listed["items"]] == [old["id"]]  # rejected hidden by default
    _, rejected = call(base, "GET", "/api/v1/reports?status=rejected")
    assert [r["id"] for r in rejected["items"]] == [fresh["id"]]


def test_image_upload(base):
    jpeg = b"\xff\xd8\xff\xe0" + b"\x00" * 100
    status, up = upload(base, jpeg)
    assert status == 201 and up["image_url"].startswith("/uploads/")
    status, served = call(base, "GET", up["image_url"])
    assert status == 200 and served == jpeg

    lat, lon = segment_point(base, "SEG09")
    status, r = call(base, "POST", "/api/v1/reports",
                     {"lat": lat, "lon": lon, "flood_level": "heavy", "image_url": up["image_url"]})
    assert status == 201 and r["image_url"] == up["image_url"]

    assert upload(base, b"<?php echo 1; ?>", "shell.jpg")[0] == 415  # content checked, not name
    assert upload(base, b"\xff\xd8\xff" + b"\x00" * (5 * 1024 * 1024))[0] == 413


# ------------------------------------------------------------
# Basic performance
# ------------------------------------------------------------

def test_performance(base):
    for path in ["/api/v1/map/risks", "/api/v1/forecast/SEG01", "/api/v1/reports"]:
        timings = []
        for _ in range(30):
            start = time.perf_counter()
            assert call(base, "GET", path)[0] == 200
            timings.append((time.perf_counter() - start) * 1000)
        p95 = statistics.quantiles(timings, n=20)[-1]
        print(f"\n{path}: median {statistics.median(timings):.0f} ms, p95 {p95:.0f} ms")
        assert p95 < 500, f"{path} too slow: p95 {p95:.0f} ms"
