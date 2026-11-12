-- Flood warning Thu Duc: PostgreSQL 17 + PostGIS 3.5 schema.
-- Idempotent: the API runs this file on every startup, so it doubles as the migration.
-- Every geometry is WGS84 (SRID 4326), coordinates are [lon, lat].

CREATE EXTENSION IF NOT EXISTS postgis;

-- App users are anonymous devices (no login in the MVP); used to de-duplicate reports.
CREATE TABLE IF NOT EXISTS users (
    id          BIGSERIAL PRIMARY KEY,
    device_id   TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS road_segments (
    segment_id  TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    road_name   TEXT NOT NULL,
    length_m    INTEGER,
    geom        geometry(LineString, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS road_segments_geom_idx ON road_segments USING GIST (geom);

-- One row per Open-Meteo hour. Open-Meteo values are model output, not station data.
CREATE TABLE IF NOT EXISTS weather_hourly (
    observed_at           TIMESTAMPTZ PRIMARY KEY,
    temperature_2m        REAL,
    relative_humidity_2m  REAL,
    pressure_msl          REAL,
    surface_pressure      REAL,
    cloud_cover           REAL,
    wind_speed_10m        REAL,
    wind_gusts_10m        REAL,
    wind_direction_10m    REAL,
    precipitation         REAL,
    source                TEXT NOT NULL DEFAULT 'open-meteo-forecast',
    is_verified_observation BOOLEAN NOT NULL DEFAULT FALSE,
    fetched_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Prediction history: never updated, never overwritten (insert ... on conflict do nothing).
CREATE TABLE IF NOT EXISTS predictions (
    id             BIGSERIAL PRIMARY KEY,
    segment_id     TEXT NOT NULL REFERENCES road_segments(segment_id),
    issued_at      TIMESTAMPTZ NOT NULL,
    horizon        SMALLINT NOT NULL CHECK (horizon BETWEEN 1 AND 6),
    probability    REAL NOT NULL CHECK (probability BETWEEN 0 AND 1),
    risk_level     TEXT NOT NULL CHECK (risk_level IN ('green', 'yellow', 'orange', 'red')),
    model_version  TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (segment_id, issued_at, horizon, model_version)
);
CREATE INDEX IF NOT EXISTS predictions_segment_time_idx ON predictions (segment_id, issued_at DESC);

-- SHAP top features per model run and horizon (the model has one input point, so these
-- are shared by every segment of the run).
CREATE TABLE IF NOT EXISTS prediction_explanations (
    issued_at      TIMESTAMPTZ NOT NULL,
    horizon        SMALLINT NOT NULL CHECK (horizon BETWEEN 1 AND 6),
    model_version  TEXT NOT NULL,
    top_features   JSONB NOT NULL,
    PRIMARY KEY (issued_at, horizon, model_version)
);

CREATE TABLE IF NOT EXISTS reports (
    id           BIGSERIAL PRIMARY KEY,
    segment_id   TEXT REFERENCES road_segments(segment_id),
    user_id      BIGINT REFERENCES users(id),
    location     geometry(Point, 4326) NOT NULL,
    flood_level  TEXT NOT NULL CHECK (flood_level IN ('none', 'light', 'heavy')),
    status       TEXT NOT NULL DEFAULT 'new'
                 CHECK (status IN ('new', 'verified', 'expired', 'rejected')),
    observed_at  TIMESTAMPTZ NOT NULL,
    note         TEXT CHECK (length(note) <= 500),
    image_url    TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS reports_location_idx ON reports USING GIST (location);
CREATE INDEX IF NOT EXISTS reports_segment_time_idx ON reports (segment_id, observed_at DESC);
