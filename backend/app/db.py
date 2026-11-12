"""PostgreSQL/PostGIS connection pool, schema migration and road-segment seeding."""

import json

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from . import config

SCHEMA_FILE = config.BACKEND_DIR / "db" / "schema.sql"
SEGMENTS_FILE = config.BACKEND_DIR / "db" / "road_segments.geojson"

pool = ConnectionPool(
    config.DATABASE_URL,
    min_size=1,
    max_size=10,
    open=False,
    # autocommit: each statement commits; multi-statement writes use conn.transaction().
    kwargs={"row_factory": dict_row, "autocommit": True,
            "options": "-c TimeZone=Asia/Ho_Chi_Minh"},
)


def init_db():
    pool.open(wait=True, timeout=20)
    with pool.connection() as conn:
        conn.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
        seed_segments(conn)


def seed_segments(conn):
    """Upsert road_segments.geojson so edits to the file reach the DB on restart."""
    features = json.loads(SEGMENTS_FILE.read_text(encoding="utf-8"))["features"]
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO road_segments (segment_id, name, road_name, length_m, geom)
            VALUES (%s, %s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
            ON CONFLICT (segment_id) DO UPDATE SET
                name = EXCLUDED.name, road_name = EXCLUDED.road_name,
                length_m = EXCLUDED.length_m, geom = EXCLUDED.geom
            """,
            [
                (
                    f["properties"]["segment_id"],
                    f["properties"]["name"],
                    f["properties"]["road_name"],
                    f["properties"].get("length_m"),
                    json.dumps(f["geometry"]),
                )
                for f in features
            ],
        )
