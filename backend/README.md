# Backend: FastAPI + PostgreSQL/PostGIS

Phục vụ dự báo nguy cơ mưa lớn +1…+6 giờ theo từng đoạn đường ở TP Thủ Đức, lưu lịch sử dự báo, nhận báo cáo ngập từ cộng đồng, và trả GeoJSON cho bản đồ.

- Kiến trúc, ERD, API contract: [docs/architecture.md](docs/architecture.md)
- Schema: [db/schema.sql](db/schema.sql). API tự chạy file này mỗi lần khởi động; file viết idempotent nên đóng vai trò migration.
- 29 đoạn đường thật lấy từ OpenStreetMap: [db/road_segments.geojson](db/road_segments.geojson) (© OpenStreetMap contributors, ODbL)

## Chạy ở máy dev

Cần Docker Desktop và Python 3.13. Mọi lệnh chạy từ **thư mục gốc repo**.

```bash
docker compose up -d --wait db                     # PostGIS ở 127.0.0.1:5433
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Mở Swagger tại http://127.0.0.1:8000/docs. Nếu muốn chạy cả DB, API và app trên máy ảo bằng một lệnh thì dùng `run_demo.bat`.

Chạy cả API trong Docker (không cần cài Python):

```bash
docker compose up -d --build
```

## Biến môi trường

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `APP_ENV` | `dev` | `prod` thì bắt buộc phải đặt `DATABASE_URL` và `ADMIN_TOKEN` |
| `DATABASE_URL` | `postgresql://flood:flood_dev_pw@127.0.0.1:5433/flood` | Chuỗi kết nối PostgreSQL (cần extension PostGIS) |
| `ADMIN_TOKEN` | rỗng | Token cho `PATCH /reports/{id}/status`. Để rỗng thì tắt chức năng duyệt |
| `CORS_ORIGINS` | `*` | Các domain được phép, cách nhau bằng dấu phẩy |
| `REPORT_TTL_HOURS` | `6` | Báo cáo cũ hơn mốc này chuyển sang `expired` |
| `UPLOAD_DIR` | `backend/uploads` | Nơi lưu ảnh báo cáo |
| `POSTGRES_PASSWORD` | `flood_dev_pw` | Mật khẩu DB, chỉ dùng trong docker compose |

## Kiểm thử

```bash
pip install -r backend/requirements-dev.txt
docker compose exec db psql -U flood -c "CREATE DATABASE flood_test"   # chỉ cần 1 lần
python -m pytest backend/tests -v
```

Test chạy app thật bằng uvicorn trên PostGIS thật (DB `flood_test`). Phần inference ML được thay bằng kết quả giả cố định nên test không cần mạng.

**Kết quả ngày 12/11/2026:** 17/17 test pass trong 8,7 giây. Các nhóm được kiểm tra:

| Nhóm | Nội dung kiểm tra |
|---|---|
| GIS | 20–40 đoạn, `ST_IsValid`, nằm trong vùng Thủ Đức |
| Forecast | Đúng contract của app, đủ 6 horizon, đúng mức rủi ro, 404 khi sai id |
| Model serving | 10 request đồng thời chỉ chạy inference 1 lần; giờ mới thêm dòng mới mà không sửa dòng cũ; lọc lịch sử theo thời gian |
| Lỗi nguồn dữ liệu | Open-Meteo lỗi thì trả bản gần nhất `stale: true`; quá 3 giờ thì 503, không trả 500 |
| Explain | Văn bản tiếng Việt, đúng chiều tăng/giảm, `horizon` sai thì 422 |
| Report | Tự gán đoạn đường, chống trùng (chung và theo thiết bị), 8 trường hợp input sai đều 422, hết hạn sau 6 giờ |
| Moderation | Thiếu hoặc sai token thì 401, báo cáo đã hết hạn thì 409, rejected bị ẩn |
| Upload | Ảnh JPEG lưu được và tải lại được; file giả đuôi `.jpg` bị 415; quá 5 MB bị 413 |
| Hiệu năng | 30 request liên tiếp mỗi endpoint |

Kết quả hiệu năng (máy dev, DB trong Docker):

| Endpoint | Trung vị | p95 |
|---|---|---|
| `/api/v1/map/risks` | 38 ms | 66 ms |
| `/api/v1/forecast/{id}` | 18 ms | 52 ms |
| `/api/v1/reports` | 20 ms | 30 ms |

Lần gọi đầu tiên trong mỗi giờ mất khoảng 0,8 giây vì phải chạy inference thật.

## Triển khai (deploy)

Backend gồm hai phần: một container API (`backend/Dockerfile`, build từ thư mục gốc repo) và một PostgreSQL có PostGIS.

- **VPS có Docker:** clone repo, tạo file `.env` với `APP_ENV=prod`, `POSTGRES_PASSWORD=...`, `ADMIN_TOKEN=...`, `CORS_ORIGINS=...`, rồi chạy `docker compose up -d --build`. Compose chỉ mở cổng trên `127.0.0.1`, nên cần đặt reverse proxy có HTTPS (Caddy/Nginx) phía trước cổng 8000.
- **Render / Railway:** tạo một PostgreSQL (Railway có template PostGIS; Render Postgres hỗ trợ `CREATE EXTENSION postgis`). Tạo Web Service từ `backend/Dockerfile`, đặt `APP_ENV=prod`, `DATABASE_URL`, `ADMIN_TOKEN`, `CORS_ORIGINS`. Ảnh upload nằm trên ổ đĩa của container, nên cần gắn persistent disk vào `/app/backend/uploads`.

Cập nhật đoạn đường: sửa `ROADS` trong [tools/fetch_osm_segments.py](tools/fetch_osm_segments.py), chạy `python backend/tools/fetch_osm_segments.py` (cần `shapely`), rồi khởi động lại API để nạp lại vào DB.
