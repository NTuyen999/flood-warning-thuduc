# Báo cáo Kỹ thuật Phần Mobile & Gợi ý Đường đi - Đồ án Cảnh báo Mưa lớn TP Thủ Đức

Tài liệu chi tiết đóng góp phần Mobile (Tường) cho báo cáo đồ án cuối kỳ, bao gồm tính năng Gợi ý đường đi và Chế độ mô phỏng.

---

## 1. Kiến trúc & Thiết kế Ứng dụng Mobile

Ứng dụng di động được xây dựng bằng **Flutter SDK (Dart)** theo kiến trúc phân tầng sạch (Clean UI + Service Pattern):

```
lib/
├── core/                  # Thư viện dùng chung (Màu sắc rủi ro, Widgets, DemoMode)
│   ├── demo_mode.dart     # ValueNotifier quản lý trạng thái bật/tắt & kịch bản mô phỏng
│   ├── risk_colors.dart   # Định nghĩa 4 mức nguy cơ & màu sắc/icon/nhãn tương ứng
│   └── widgets.dart       # BaseMap, LoadView, ErrorRetry, Pill, SectionTitle
├── data/                  # Tầng dữ liệu & giao tiếp API
│   ├── models/            # Forecast, RiskMap, RoadSegment, Report, Weather, Demo models
│   │   ├── demo.dart      # DemoScenario, RoutePoint, RoutePath, RouteResult
│   │   └── road_segment.dart # Mở rộng thuộc tính kind, deadEnd, parentSegmentId, blocked
│   └── services/          # ApiService (dùng Dio HTTP client, hỗ trợ /api/v1/demo/*)
└── features/              # Các tính năng chính (Feature-first)
    ├── map/               # Bản đồ rủi ro, hẻm mô phỏng & danh sách tuyến đường
    ├── forecast/          # Màn hình chi tiết dự báo 6 giờ (thực tế & mô phỏng)
    ├── explain/           # Màn hình giải thích SHAP ("Vì sao?")
    ├── report/            # Form gửi báo cáo ngập & Lịch sử báo cáo cộng đồng
    └── route/             # Màn hình Gợi ý đường đi (RouteScreen)
```

---

## 2. Bảng Màn hình và Endpoint API (Bao gồm các Endpoint Mô phỏng)

| Màn hình | Chức năng | Endpoint API sử dụng | Phương thức |
|---|---|---|---|
| **Bản đồ (Thực tế)** | Vẽ đoạn đường tô màu rủi ro & Marker báo cáo | `/api/v1/map/risks?horizon=` | `GET` |
| **Bản đồ (Mô phỏng)** | Vẽ 29 đoạn chính + 4 hẻm phụ theo kịch bản | `/api/v1/demo/map?scenario=&horizon=` | `GET` |
| **Gợi ý đường đi** | Danh sách điểm chọn đi/đến có tên | `/api/v1/demo/route-points` | `GET` |
| **Gợi ý đường đi** | Thuật toán Dijkstra gợi ý đường vòng ít rủi ro | `/api/v1/demo/route?scenario=&from=&to=` | `GET` |
| **Tuyến đường** | Danh sách các đường xếp theo số báo cáo ngập | `/api/v1/map/risks` | `GET` |
| **Dự báo (Thực tế)** | Thẻ tóm tắt & Biểu đồ dự báo 6 cột | `/api/v1/forecast/{segment_id}` | `GET` |
| **Dự báo (Mô phỏng)** | Biểu đồ dự báo 6 cột kịch bản mô phỏng | `/api/v1/demo/forecast/{segment_id}?scenario=` | `GET` |
| **Vì sao?** | Giải thích yếu tố ảnh hưởng SHAP | `/api/v1/explain/{segment_id}?horizon=` | `GET` |
| **Báo cáo** | Tải ảnh báo cáo lên server | `/api/v1/uploads` | `POST` |
| **Báo cáo** | Gửi thông tin báo cáo ngập vị trí GPS | `/api/v1/reports` | `POST` |
| **Máy chủ API** | Kiểm tra trạng thái máy chủ & phiên bản mô hình | `/health` | `GET` |

---

## 3. Các Quyết định Kỹ thuật Chính

1. **Gợi ý đường đi trên mạng mô phỏng (Demo Routing Engine):**
   - Xây dựng thuật toán Dijkstra trên đồ thị giao thông mạng lưới thu nhỏ (`demo_network.json`).
   - Tự động chuyển tuyến (`detour`) qua Hẻm liên thông 78 khi đường chính Kha Vạn Cân 2 bị ngập Đỏ.
   - Cảnh báo hẻm cụt (`warning`) và thông báo không thể tới nơi (`unreachable`) khi bị chặn hoàn toàn.
2. **Kế thừa mức rủi ro Hẻm (`inherits_from` & `dead_end`):**
   - Hẻm cụt AL01 kế thừa nguy cơ ngập tràn từ đường chính Kha Vạn Cân 2. Khi Kha Vạn Cân 2 ngập Đỏ, Hẻm AL01 tự động chuyển sang mức Đỏ bị chặn.
   - Hẻm cụt AL02 thể hiện trường hợp hẻm trũng tự ngập độc lập với đường chính.
3. **Nguồn bản đồ nền linh hoạt (Esri + CARTO fallback):**
   - Mặc định dùng **Esri World Street Map** kèm fallback **CARTO**, hỗ trợ cấu hình qua `--dart-define=TILE_URL=...`.
4. **Kiểm thử tự động toàn diện:**
   - Xây dựng bộ test suite 41 test cases (UI widget tests, Accessibility 360x640 / textScale 1.8, Demo routing, Error handling) pass 100%.

---

## 4. Hạn chế Kỹ thuật & Định hướng Phát triển

### Hạn chế kỹ thuật hiện tại:
- **Đồ thị mô phỏng thu nhỏ:** Tính năng gợi ý đường đi hiện chạy trên đồ thị mô phỏng 11 nút / 11 cạnh khu vực Kha Vạn Cân, chưa kết nối toàn bộ mạng lưới đường TP Thủ Đức.
- **Dữ liệu đầu vào ML đồng nhất:** Mô hình XGBoost ML lấy 1 điểm tọa độ thời tiết cho toàn khu vực, các kịch bản mô phỏng giúp thể hiện sự phân hóa nguy cơ mưa lớn giữa các tuyến.
- **Hình học hẻm:** Các hẻm AL01–AL04 là dữ liệu giả lập cho mục đích mô phỏng thuật toán và giao diện.

### Định hướng phát triển:
- Mở rộng đồ thị giao thông bằng pgRouting cho toàn địa bàn TP Thủ Đức.
- Cập nhật trọng số cạnh thời gian thực kết hợp giữa mô hình ML, dữ liệu độ cao DEM và báo cáo ngập từ người đi đường.

---

## 5. Lưu ý về Báo cáo Giữa kỳ
Mục *"App chạy toàn dữ liệu mock"* trong tài liệu Báo cáo giữa kỳ (`BAO_CAO_GIUA_KY.md`) đã **lỗi thời**. Ứng dụng di động hiện tại hoạt động song song 2 chế độ:
1. **Chế độ thực tế (Mặc định):** Đọc dữ liệu REST API từ backend FastAPI, DB PostgreSQL/PostGIS và mô hình XGBoost ML thực tế.
2. **Chế độ mô phỏng (Demo Mode):** Cho phép người dùng thử nghiệm 3 kịch bản thời tiết, quan sát sự ngập lụt ở các hẻm cụt và trải nghiệm tính năng gợi ý đường đi ít rủi ro hơn.
