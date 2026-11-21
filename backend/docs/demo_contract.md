# Contract API & Quy tắc Mô phỏng Gợi ý Đường đi (Demo Routing)

Tài liệu quy định chi tiết các API endpoint, bảng kịch bản giả lập, quy tắc kế thừa mức rủi ro hẻm và thuật toán định tuyến trên khu vực mô phỏng TP Thủ Đức.

---

## 1. Danh sách Endpoint API Mô phỏng (`/api/v1/demo`)

Tất cả payload trả về từ các endpoint demo đều chứa `"is_demo": true` và `"model_version": "demo-scenario"`.

| Method | Path | Mô tả | Tham số Query | Trả về |
|---|---|---|---|---|
| `GET` | `/api/v1/demo/scenarios` | Danh sách kịch bản mô phỏng | Không | JSON danh sách kịch bản |
| `GET` | `/api/v1/demo/map` | GeoJSON bản đồ rủi ro (29 đoạn chính + 4 hẻm) | `scenario` (`none`\|`moderate`\|`heavy`), `horizon` (1..6) | FeatureCollection GeoJSON |
| `GET` | `/api/v1/demo/forecast/{segment_id}` | Dự báo 6 giờ cho 1 đoạn/hẻm | `scenario` | `ForecastOut` JSON |
| `GET` | `/api/v1/demo/route-points` | Các điểm nút có tên để chọn đi/đến | Không | Danh sách điểm chọn |
| `GET` | `/api/v1/demo/route` | Gợi ý đường đi ít rủi ro hơn | `scenario`, `from`, `to`, `horizon` | RouteResult JSON |

---

## 2. Bảng Kịch bản Dữ liệu Giả lập

| Mã Scenario | Nhãn (Label) | Mô tả ngắn | Trọng số ngập & Mức rủi ro cao nhất (1–6h) |
|---|---|---|---|
| `none` | Không mưa | Thời tiết khô ráo, tất cả thông thoáng | Tất cả các đoạn chính (SEG01..29) và hẻm (AL01..04) đều **Xanh (green)**. |
| `moderate` | Mưa vừa | Mưa gia tăng về chiều | SEG01, SEG05: **Vàng (yellow)**<br/>SEG02, SEG06: **Cam (orange)**<br/>AL01: **Vàng (yellow)** *(Kế thừa từ SEG02 Cam)*<br/>AL02: **Cam (orange)** *(Tự ngập)*<br/>AL03, AL04: **Xanh (green)** |
| `heavy` | Mưa nhiều | Mưa lớn kéo dài diện rộng | SEG01, SEG05, AL03: **Cam (orange)**<br/>SEG02, SEG06: **Đỏ (red - Bị chặn)**<br/>AL01: **Đỏ (red - Bị chặn)** *(Kế thừa từ SEG02 Đỏ)*<br/>AL02: **Đỏ (red - Bị chặn)** *(Tự ngập)*<br/>AL04: **Xanh (green)** |

---

## 3. Quy tắc Kế thừa Mức Rủi ro Hẻm (`inherits_from`)

Nếu hẻm có trường `inherits_from` (ví dụ `AL01` nối vào `SEG02` mang `inherits_from`: "SEG02"):

1. Tính mức nguy cơ riêng của hẻm từ xác suất kịch bản (`own_level`).
2. Xác định mức nguy cơ của đoạn đường chính cha (`parent_level`):
   - Nếu `parent_level == "red"` $\rightarrow$ Mức kế thừa `inherited_level = "red"`.
   - Nếu `parent_level == "orange"` $\rightarrow$ Mức kế thừa `inherited_level = "yellow"`.
   - Còn lại $\rightarrow$ Không kế thừa (`inherited_level = "green"`).
3. Mức nguy cơ hiệu lực của hẻm: `effective_level = max(own_level, inherited_level)` theo thứ tự `green` < `yellow` < `orange` < `red`.
4. Nguồn mức: `level_source` = `"own"` nếu `effective_level == own_level`, ngược lại `level_source` = `"inherited:SEGxx"`.
5. Trạng thái bị chặn: `blocked = true` nếu `effective_level == "red"`, ngược lại `false`.

---

## 4. Quy tắc Định tuyến (Dijkstra Algorithm & Dead-End Rules)

### Trọng số Chi phí Cạnh (Edge Cost Multiplier):
$$\text{Cost} = \text{Chiều dài cạnh (m)} \times \text{Multiplier}(\text{risk\_level})$$
- `green`: Multiplier = `1.0`
- `yellow`: Multiplier = `1.4`
- `orange`: Multiplier = `4.0`
- `red`: Multiplier = `Infinity` (Đoạn đường bị chặn, loại khỏi đồ thị tìm đường).

### Quy tắc Hẻm cụt (Dead-End Rule):
Các cạnh thuộc hẻm cụt (`dead_end == true`, gồm `AL01`, `AL02`, `AL04`) chỉ được phép xuất hiện trong tuyến đường **nếu điểm đi (`from`) hoặc điểm đến (`to`) nằm chính trong hẻm cụt đó**. Không cho phép tuyến đường đi qua hẻm cụt rồi quay đầu làm đường tắt.

### Phân loại Trạng thái Kết quả Định tuyến (`status`):
- `ok`: Tuyến đường khuyến nghị đi theo đường ngắn nhất, không có đoạn bị chặn hay nguy cơ cao.
- `detour`: Tuyến đường ngắn nhất bị cản trở (bị chặn Đỏ hoặc nguy cơ Cam), thuật toán đã tìm được tuyến vòng tránh an toàn hơn (ví dụ qua hẻm liên thông AL03).
- `warning`: Điểm đi hoặc điểm đến nằm trong hẻm cụt có nguy cơ ngập (mức Cam/Đỏ), cảnh báo khả năng bị kẹt trong hẻm.
- `unreachable`: Tất cả các đường đi tới đích đều bị chặn bởi các đoạn đường ngập nặng (mức Đỏ). Ứng dụng khuyên người dùng nên hoãn chuyến đi.

---

## 5. Tuyên bố Miễn trừ Tách biệt (Disclaimer)

> *"Tuyển tập dữ liệu và kết quả định tuyến mang tính MÔ PHỎNG trên khu vực thu nhỏ TP Thủ Đức. Không cam kết an toàn tuyệt đối."*
