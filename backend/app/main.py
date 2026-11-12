"""Flood Warning Thu Duc backend API.

Run from the repo root (PostGIS must be up: `docker compose up -d db`):

    python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

Swagger: http://127.0.0.1:8000/docs
"""

import logging
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Literal

import psycopg
from fastapi import FastAPI, File, Header, HTTPException, Path, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, model_validator

from . import config, db, forecast

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("backend")

TIMEZONE = "Asia/Ho_Chi_Minh"
DISCLAIMER = (
    "Xác suất mưa lớn (≥ 30 mm trong 3 giờ) tại một điểm đại diện TP Thủ Đức, dùng làm chỉ báo "
    "sớm nguy cơ ngập. Chưa được kiểm chứng bằng dữ liệu ngập thực tế."
)
LEVEL_LABELS = {"green": "Thấp", "yellow": "Trung bình", "orange": "Cao", "red": "Rất cao"}
SegmentId = Path(max_length=32, examples=["SEG01"])

config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_app):
    db.init_db()
    log.info("Ready: env=%s model=%s", config.APP_ENV, forecast.model_version())
    yield
    db.pool.close()


app = FastAPI(
    title="Flood Warning Thủ Đức API",
    version="2.0.0",
    description=DISCLAIMER,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"]
)
app.mount("/uploads", StaticFiles(directory=config.UPLOAD_DIR), name="uploads")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    log.info("%s %s -> %s (%.0f ms)", request.method, request.url.path,
             response.status_code, (time.perf_counter() - start) * 1000)
    return response


@app.exception_handler(psycopg.OperationalError)
async def database_unavailable(_request, _exc):
    log.exception("Database error")
    return JSONResponse(status_code=503, content={"detail": "Cơ sở dữ liệu không sẵn sàng"})


@app.exception_handler(forecast.ForecastUnavailable)
async def forecast_unavailable(_request, _exc):
    return JSONResponse(status_code=503, content={"detail": "Chưa lấy được dự báo, thử lại sau"})


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

SEGMENT_COLUMNS = "segment_id, name, road_name, length_m, ST_AsGeoJSON(geom)::json AS geometry"
REPORT_COLUMNS = """
    id, segment_id, ST_Y(location) AS lat, ST_X(location) AS lon, flood_level, status,
    observed_at, note, image_url, created_at,
    round(extract(epoch FROM now() - observed_at) / 60)::int AS age_minutes
"""
POINT = "ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)"


def get_segment(conn, segment_id):
    row = conn.execute(
        f"SELECT {SEGMENT_COLUMNS} FROM road_segments WHERE segment_id = %s", (segment_id,)
    ).fetchone()
    if not row:
        raise HTTPException(404, f"Không có đoạn đường {segment_id}")
    return row


def as_feature(row, **extra):
    props = {k: v for k, v in row.items() if k != "geometry"}
    return {"type": "Feature", "geometry": row["geometry"], "properties": {**props, **extra}}


def expire_old_reports(conn):
    conn.execute(
        "UPDATE reports SET status = 'expired' WHERE status IN ('new', 'verified') "
        "AND observed_at < now() - make_interval(secs => %s)",
        (config.REPORT_TTL_HOURS * 3600,),
    )


# ------------------------------------------------------------
# System + GIS
# ------------------------------------------------------------

@app.get("/health", tags=["system"], summary="API + database status")
def health():
    with db.pool.connection() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok", "db": "ok", "env": config.APP_ENV,
            "model_version": forecast.model_version()}


@app.get("/api/v1/road-segments", tags=["gis"], summary="All road segments (GeoJSON)")
def road_segments():
    with db.pool.connection() as conn:
        rows = conn.execute(f"SELECT {SEGMENT_COLUMNS} FROM road_segments ORDER BY segment_id").fetchall()
    return {"type": "FeatureCollection", "features": [as_feature(r) for r in rows]}


@app.get("/api/v1/road-segments/{segment_id}", tags=["gis"], summary="One road segment (GeoJSON)")
def road_segment(segment_id: str = SegmentId):
    with db.pool.connection() as conn:
        return as_feature(get_segment(conn, segment_id))


# ------------------------------------------------------------
# Weather + forecast
# ------------------------------------------------------------

@app.get("/api/v1/weather/current", tags=["forecast"], summary="Latest hourly weather used by the model")
def weather_current():
    with db.pool.connection() as conn:
        _, stale = forecast.ensure_latest_run(conn)
        row = conn.execute("SELECT * FROM weather_hourly ORDER BY observed_at DESC LIMIT 1").fetchone()
    if not row:
        raise HTTPException(503, "Chưa có dữ liệu thời tiết")
    return {**row, "timezone": TIMEZONE, "stale": stale,
            "note": "Số liệu mô hình Open-Meteo, không phải số đo trạm."}


class HorizonOut(BaseModel):
    h: int = Field(ge=1, le=6, description="Giờ tới (+1 … +6)")
    probability: float = Field(ge=0, le=1, description="Xác suất đã hiệu chỉnh")
    level: Literal["green", "yellow", "orange", "red"]


class ForecastOut(BaseModel):
    segment_id: str
    name: str
    issued_at: datetime
    timezone: str
    model_version: str
    is_mock: bool = False
    stale: bool = Field(description="true = Open-Meteo lỗi, đang trả lần dự báo gần nhất")
    horizons: list[HorizonOut]
    disclaimer: str


@app.get("/api/v1/forecast/{segment_id}", tags=["forecast"], response_model=ForecastOut,
         summary="Risk +1h … +6h for one segment")
def get_forecast(segment_id: str = SegmentId):
    with db.pool.connection() as conn:
        seg = get_segment(conn, segment_id)
        issued_at, stale = forecast.ensure_latest_run(conn)
        rows = conn.execute(
            "SELECT horizon AS h, probability, risk_level AS level FROM predictions "
            "WHERE segment_id = %s AND issued_at = %s AND model_version = %s ORDER BY horizon",
            (segment_id, issued_at, forecast.model_version()),
        ).fetchall()
    if len(rows) != 6:
        raise HTTPException(503, "Đoạn đường này chưa có dự báo, thử lại sau")
    return {"segment_id": segment_id, "name": seg["name"], "issued_at": issued_at,
            "timezone": TIMEZONE, "model_version": forecast.model_version(), "stale": stale,
            "horizons": rows, "disclaimer": DISCLAIMER}


@app.get("/api/v1/predictions", tags=["forecast"], summary="Stored prediction history of a segment")
def prediction_history(
    segment_id: str = Query(max_length=32),
    start: datetime | None = None,
    end: datetime | None = None,
    horizon: int | None = Query(None, ge=1, le=6),
    limit: int = Query(500, ge=1, le=5000),
):
    if start and end and start > end:
        raise HTTPException(422, "start phải trước end")
    with db.pool.connection() as conn:
        get_segment(conn, segment_id)
        rows = conn.execute(
            """
            SELECT issued_at, horizon, probability, risk_level, model_version, created_at
            FROM predictions
            WHERE segment_id = %(seg)s
              AND (%(start)s::timestamptz IS NULL OR issued_at >= %(start)s)
              AND (%(end)s::timestamptz IS NULL OR issued_at <= %(end)s)
              AND (%(h)s::int IS NULL OR horizon = %(h)s)
            ORDER BY issued_at DESC, horizon LIMIT %(limit)s
            """,
            {"seg": segment_id, "start": start, "end": end, "h": horizon, "limit": limit},
        ).fetchall()
    return {"segment_id": segment_id, "count": len(rows), "items": rows}


@app.get("/api/v1/explain/{segment_id}", tags=["forecast"], summary="Top SHAP features of a forecast")
def explain(segment_id: str = SegmentId, horizon: int = Query(1, ge=1, le=6)):
    with db.pool.connection() as conn:
        seg = get_segment(conn, segment_id)
        issued_at, stale = forecast.ensure_latest_run(conn)
        row = conn.execute(
            "SELECT p.probability, p.risk_level, e.top_features FROM predictions p "
            "JOIN prediction_explanations e USING (issued_at, horizon, model_version) "
            "WHERE p.segment_id = %s AND p.issued_at = %s AND p.horizon = %s AND p.model_version = %s",
            (segment_id, issued_at, horizon, forecast.model_version()),
        ).fetchone()
    if not row:
        raise HTTPException(503, "Đoạn đường này chưa có dự báo, thử lại sau")
    return {
        "segment_id": segment_id, "name": seg["name"], "issued_at": issued_at, "horizon": horizon,
        "probability": row["probability"], "level": row["risk_level"], "stale": stale,
        "features": [forecast.explain_feature(f) for f in row["top_features"]],
        "note": "Mức đóng góp (SHAP, log-odds) của từng yếu tố vào điểm số mô hình; "
                "không phải quan hệ nhân quả.",
    }


@app.get("/api/v1/map/risks", tags=["gis"], summary="Segments + risk + report summary (GeoJSON)")
def map_risks(horizon: int | None = Query(None, ge=1, le=6,
                                          description="Bỏ trống = mức cao nhất trong 6 giờ tới")):
    with db.pool.connection() as conn:
        issued_at, stale = forecast.ensure_latest_run(conn)
        expire_old_reports(conn)
        rows = conn.execute(
            """
            WITH p AS (
                SELECT segment_id, max(probability) AS probability FROM predictions
                WHERE issued_at = %(issued)s AND model_version = %(v)s
                  AND (%(h)s::int IS NULL OR horizon = %(h)s)
                GROUP BY segment_id
            ), r AS (
                SELECT segment_id, count(*) AS active,
                       count(*) FILTER (WHERE flood_level <> 'none') AS flooded,
                       max(observed_at) AS latest_at
                FROM reports WHERE status IN ('new', 'verified') GROUP BY segment_id
            )
            SELECT s.segment_id, s.name, ST_AsGeoJSON(s.geom)::json AS geometry,
                   p.probability, r.active, r.flooded, r.latest_at
            FROM road_segments s LEFT JOIN p USING (segment_id) LEFT JOIN r USING (segment_id)
            ORDER BY s.segment_id
            """,
            {"issued": issued_at, "v": forecast.model_version(), "h": horizon},
        ).fetchall()
    features = []
    for r in rows:
        p = r["probability"]
        features.append({
            "type": "Feature",
            "geometry": r["geometry"],
            "properties": {
                "segment_id": r["segment_id"], "name": r["name"], "probability": p,
                "risk_level": forecast.risk_level(p) if p is not None else None,
                "report_summary": {"active": r["active"] or 0, "flooded": r["flooded"] or 0,
                                   "latest_at": r["latest_at"]},
            },
        })
    bounds = [b for b, _ in config.RISK_BANDS] + [1.0]
    return {
        "type": "FeatureCollection", "issued_at": issued_at, "horizon": horizon, "stale": stale,
        "model_version": forecast.model_version(), "disclaimer": DISCLAIMER,
        "legend": [{"level": lvl, "label": LEVEL_LABELS[lvl], "max_probability": b}
                   for b, lvl in zip(bounds, LEVEL_LABELS)],
        "features": features,
    }


# ------------------------------------------------------------
# Community reports
# ------------------------------------------------------------

class ReportIn(BaseModel):
    lat: float = Field(ge=-90, le=90, examples=[10.8505])
    lon: float = Field(ge=-180, le=180, examples=[106.7718])
    flood_level: Literal["none", "light", "heavy"]
    observed_at: datetime | None = Field(None, description="Bỏ trống = bây giờ")
    segment_id: str | None = Field(None, max_length=32,
                                   description="Bỏ trống = tự gán đoạn gần nhất trong 150 m")
    note: str | None = Field(None, max_length=500)
    image_url: str | None = Field(None, pattern=r"^/uploads/[0-9a-f]{32}\.(jpg|png|webp)$",
                                  description="Giá trị image_url trả về từ POST /api/v1/uploads")
    device_id: str | None = Field(None, min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")

    @model_validator(mode="after")
    def check_place_and_time(self):
        lat_min, lon_min, lat_max, lon_max = config.THU_DUC_BBOX
        if not (lat_min <= self.lat <= lat_max and lon_min <= self.lon <= lon_max):
            raise ValueError("Vị trí nằm ngoài TP Thủ Đức")
        now = forecast.now_local()
        if self.observed_at is None:
            self.observed_at = now
        elif self.observed_at.tzinfo is None:
            self.observed_at = self.observed_at.replace(tzinfo=forecast.live.LOCAL_TZ)
        if self.observed_at > now + timedelta(minutes=5):
            raise ValueError("Thời điểm quan sát ở tương lai")
        if self.observed_at < now - timedelta(hours=config.REPORT_TTL_HOURS):
            raise ValueError(f"Báo cáo cũ hơn {config.REPORT_TTL_HOURS:g} giờ")
        return self


@app.post("/api/v1/reports", tags=["reports"], status_code=201, summary="Send a community report")
def create_report(body: ReportIn):
    if body.image_url and not (config.UPLOAD_DIR / body.image_url.rsplit("/", 1)[1]).is_file():
        raise HTTPException(422, "image_url không tồn tại, hãy tải ảnh lên trước")
    params = body.model_dump() | {"rad": config.DUPLICATE_RADIUS_M, "win": config.DUPLICATE_WINDOW_MIN,
                                  "snap": config.SEGMENT_SNAP_M}
    with db.pool.connection() as conn, conn.transaction():
        if body.segment_id:
            if not conn.execute("SELECT 1 FROM road_segments WHERE segment_id = %s",
                                (body.segment_id,)).fetchone():
                raise HTTPException(422, f"Không có đoạn đường {body.segment_id}")
        else:
            near = conn.execute(
                f"SELECT segment_id FROM road_segments "
                f"WHERE ST_DWithin(geom::geography, {POINT}::geography, %(snap)s) "
                f"ORDER BY geom <-> {POINT} LIMIT 1",
                params,
            ).fetchone()
            params["segment_id"] = near and near["segment_id"]

        params["uid"] = None
        if body.device_id:
            params["uid"] = conn.execute(
                "INSERT INTO users (device_id) VALUES (%s) ON CONFLICT (device_id) "
                "DO UPDATE SET device_id = EXCLUDED.device_id RETURNING id",
                (body.device_id,),
            ).fetchone()["id"]

        expire_old_reports(conn)
        dup = conn.execute(
            f"""
            SELECT id FROM reports
            WHERE status IN ('new', 'verified') AND flood_level = %(flood_level)s
              AND abs(extract(epoch FROM observed_at - %(observed_at)s)) <= %(win)s * 60
              AND ST_DWithin(location::geography, {POINT}::geography, %(rad)s)
              AND (%(uid)s::bigint IS NULL OR user_id = %(uid)s)
            LIMIT 1
            """,
            params,
        ).fetchone()
        if dup:
            raise HTTPException(409, {"message": "Đã có báo cáo tương tự gần đây",
                                      "duplicate_of": dup["id"]})

        new_id = conn.execute(
            f"""
            INSERT INTO reports (segment_id, user_id, location, flood_level, observed_at, note, image_url)
            VALUES (%(segment_id)s, %(uid)s, {POINT}, %(flood_level)s, %(observed_at)s,
                    %(note)s, %(image_url)s)
            RETURNING id
            """,
            params,
        ).fetchone()["id"]
        return conn.execute(f"SELECT {REPORT_COLUMNS} FROM reports WHERE id = %s", (new_id,)).fetchone()


@app.get("/api/v1/reports", tags=["reports"], summary="Recent reports (newest first)")
def list_reports(
    segment_id: str | None = Query(None, max_length=32),
    status: Literal["new", "verified", "expired", "rejected"] | None = Query(
        None, description="Bỏ trống = mọi trạng thái trừ rejected"),
    limit: int = Query(50, ge=1, le=200),
):
    with db.pool.connection() as conn:
        expire_old_reports(conn)
        rows = conn.execute(
            f"""
            SELECT {REPORT_COLUMNS} FROM reports
            WHERE (%(seg)s::text IS NULL OR segment_id = %(seg)s)
              AND (CASE WHEN %(st)s::text IS NULL THEN status <> 'rejected' ELSE status = %(st)s END)
            ORDER BY observed_at DESC LIMIT %(limit)s
            """,
            {"seg": segment_id, "st": status, "limit": limit},
        ).fetchall()
    return {"count": len(rows), "items": rows}


class StatusIn(BaseModel):
    status: Literal["verified", "rejected"]


@app.patch("/api/v1/reports/{report_id}/status", tags=["reports"],
           summary="Moderate a report (needs X-Admin-Token)")
def moderate_report(report_id: int, body: StatusIn, x_admin_token: str | None = Header(None)):
    if not config.ADMIN_TOKEN:
        raise HTTPException(403, "Chưa bật kiểm duyệt (thiếu ADMIN_TOKEN trên server)")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, config.ADMIN_TOKEN):
        raise HTTPException(401, "Sai X-Admin-Token")
    with db.pool.connection() as conn:
        expire_old_reports(conn)
        row = conn.execute(
            f"UPDATE reports SET status = %s WHERE id = %s AND status <> 'expired' "
            f"RETURNING {REPORT_COLUMNS}",
            (body.status, report_id),
        ).fetchone()
        if row:
            return row
        exists = conn.execute("SELECT 1 FROM reports WHERE id = %s", (report_id,)).fetchone()
    raise HTTPException(409 if exists else 404,
                        "Báo cáo đã hết hạn" if exists else f"Không có báo cáo {report_id}")


def image_extension(data):
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


@app.post("/api/v1/uploads", tags=["reports"], status_code=201,
          summary="Upload a report photo (JPEG/PNG/WebP, max 5 MB)")
def upload_image(file: UploadFile = File(...)):
    data = file.file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Ảnh lớn hơn 5 MB")
    ext = image_extension(data)  # check the bytes, not the client-supplied content type
    if not ext:
        raise HTTPException(415, "Chỉ nhận ảnh JPEG, PNG hoặc WebP")
    name = f"{uuid.uuid4().hex}.{ext}"
    (config.UPLOAD_DIR / name).write_bytes(data)
    return {"image_url": f"/uploads/{name}"}
