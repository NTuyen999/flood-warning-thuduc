# Báo cáo giữa kỳ: hiện trạng và hướng đi đồ án flood-warning-thuduc

*Cập nhật: 10/11/2026*

## 1. Đồ án làm được tới đâu

Repo có 9 commit, viết từ 17/10 đến 08/11. Phần ML do Tuyến làm, phần mobile do Tường làm.

| Phần | Trạng thái | Bằng chứng |
|---|---|---|
| Thu thập dữ liệu (Open-Meteo Archive, 2010 → 09/2026, theo giờ) | ✅ Xong | [01_collect_historical.py](ml/src/data/01_collect_historical.py) |
| Kiểm tra dữ liệu, làm sạch, EDA | ✅ Xong | `02`–`04` trong [ml/src/data/](ml/src/data/) |
| Tạo nhãn: tổng mưa 3 giờ ≥ 30 mm, cho các tầm dự báo h1 đến h6 | ✅ Xong | [05_create_labels.py](ml/src/data/05_create_labels.py) |
| Đặc trưng: mưa lũy kế, độ trễ, chênh lệch độ ẩm/áp suất, mã hóa giờ và tháng dạng sin/cos (30 đặc trưng) | ✅ Xong | [feature_list.json](ml/saved_models/final/feature_list.json) |
| Chia dữ liệu theo thời gian: train ≤ 2023, val 2024–2025, test 2026 | ✅ Xong | [07_split_data.py](ml/src/data/07_split_data.py) |
| Baseline, so sánh RF/XGBoost/LightGBM, xử lý lệch lớp (`scale_pos_weight`) | ✅ Xong | `08_baselines.py`, [09_train_models.py](ml/src/models/09_train_models.py) |
| Cross-validation theo thời gian có loại bỏ khoảng nhãn chồng lấn, chọn ngưỡng, hiệu chỉnh xác suất, đánh giá trên test, giải thích bằng SHAP | ✅ Xong | `10`–`16` trong [ml/src/evaluation/](ml/src/evaluation/) |
| 6 mô hình XGBoost cuối (h1 đến h6) kèm bộ hiệu chỉnh | ✅ Xong | [ml/saved_models/final/](ml/saved_models/final/) |
| Dự báo live và API FastAPI `/api/v1/rain-proxy/latest` | 🟡 Bản mẫu nghiên cứu | [19_live_api.py](ml/src/models/19_live_api.py) |
| App Flutter: bản đồ đoạn đường, biểu đồ dự báo, màn giải thích, báo cáo, lịch sử | 🟡 Có giao diện, **chạy toàn dữ liệu mock** | [api.dart](mobile/lib/data/services/api.dart) |
| Nối app với API thật, dữ liệu ngập thật, triển khai | ❌ Chưa làm | |

**Điểm mạnh:** quy trình ML làm khá bài bản. Dữ liệu chia theo thời gian, cross-validation có loại bỏ khoảng nhãn chồng lấn để tránh rò rỉ, ngưỡng được chọn trên tập validation, xác suất được hiệu chỉnh, có baseline để so sánh, có SHAP. Code cũng tự ghi rõ giới hạn của mình (API trả `actual_flood_labels_available: False`).

## 2. Những điểm chưa ổn, xếp từ nặng đến nhẹ

1. **Mô hình dự báo mưa lớn, chưa phải dự báo ngập.** Nhãn chỉ là "mưa ≥ 30 mm trong 3 giờ". Trong code không có dữ liệu ngập, mực nước hay thủy triều nào. Chính code cũng tự gọi kết quả là `heavy_rain_proxy_not_observed_street_flooding` ([17_predict.py:488](ml/src/models/17_predict.py#L488)). Trong khi đó, tên đề tài và app lại nói về "nguy cơ ngập".
2. **Cả mô hình chỉ dùng một điểm tọa độ (10.85, 106.77).** File [locations.py](ml/src/locations.py) khai báo 9 điểm TD01–TD09 nhưng không chỗ nào dùng tới. Ngoài ra, ô lưới của Open-Meteo khá thô nên gần như cả TP Thủ Đức chỉ nằm trong một ô. Vì thế app hiển thị nguy cơ "theo từng đoạn đường" là chưa có cơ sở từ mô hình.
3. **App và mô hình chưa nối với nhau.** App chạy bằng `MockApiService()`. Hai bên cũng không khớp định dạng dữ liệu: app cần `getRoadSegments()` và `getForecast(segmentId)` theo từng đoạn đường, còn API chỉ trả xác suất mưa cho một điểm.
4. **Dữ liệu "thực đo" thực chất là dữ liệu mô hình.** Lúc train dùng dữ liệu tái phân tích từ Archive API, lúc chạy live lại dùng Forecast API ([18_build_live_features.py:56](ml/src/features/18_build_live_features.py#L56)). Hai nguồn này có thể lệch phân phối nhau, và chưa có số liệu mưa trạm thực đo nào để đối chứng.
5. **Không có kết quả đánh giá trong repo.** Thư mục `/ml/outputs/` và `/data/` đều nằm trong `.gitignore`, nên chưa có số liệu PR-AUC, F1 hay Brier. Cần chạy lại `15_evaluate_test.py` để lấy số liệu cho slide.
6. **Ngưỡng 30 mm/3h chưa có nguồn dẫn.** Cần trích dẫn quy chuẩn hoặc tài liệu tham khảo, hoặc giải thích vì sao chọn mức đó.
7. **Kỹ thuật:** chưa có unit test nào cho ML, còn mobile chỉ có một bài test khởi động mặc định. README chỉ có 2 dòng và chưa hướng dẫn chạy pipeline. Tên module bắt đầu bằng số nên phải nạp bằng `importlib`.

## 3. Hướng đi đề xuất cho nửa sau

1. **Chọn một cách định vị đề tài.**
   - **Cách A (ít rủi ro):** đổi tên đề tài thành "cảnh báo mưa lớn 1–6 giờ, làm chỉ báo sớm cho nguy cơ ngập".
   - **Cách B:** bổ sung dữ liệu ngập thật để có nhãn ngập, ví dụ danh sách điểm ngập của Sở Xây dựng hoặc tin tức có ngày giờ cụ thể. Sau đó ghép xác suất mưa lớn với độ nhạy ngập tĩnh của từng điểm (cao độ DEM, điểm ngập trước đây) để ra nguy cơ theo đoạn đường.
2. Viết `HttpApiService` gọi API FastAPI thật, và thống nhất định dạng dữ liệu giữa app với API.
3. Dùng tới 9 điểm trong `locations.py`, hoặc bỏ hẳn nếu không dùng.
4. Đưa bảng kết quả trên tập test 2026 vào báo cáo, so sánh với baseline (dự báo bằng trung bình theo mùa, và dự báo "giờ tới giống giờ này").
5. Triển khai thử backend (Render hoặc Railway) và viết README hướng dẫn chạy.

## 4. Câu hỏi giảng viên có thể hỏi

- **"Mô hình dự báo ngập ở đâu?"** Giai đoạn này mới dự báo mưa lớn làm tín hiệu thay thế. Kế hoạch là ghép thêm độ nhạy ngập theo điểm (xem mục 3.1).
- **"Có bị rò rỉ dữ liệu không?"** Dữ liệu chia theo thời gian, cross-validation loại bỏ khoảng nhãn chồng lấn, đặc trưng chỉ dùng mưa đến giờ t, còn nhãn tính từ t+1 trở đi.
- **"Lệch lớp xử lý thế nào?"** Dùng `scale_pos_weight` và chọn ngưỡng tối ưu trên tập validation, không dùng ngưỡng 0.5.
- **"Dữ liệu lấy từ đâu, có đáng tin không?"** Open-Meteo, là dữ liệu tái phân tích chứ không phải số đo trạm. Nên tự nêu hạn chế này trước khi bị hỏi.

## Phạm vi kiểm tra

Chưa chạy pipeline nên chưa có số liệu đánh giá thật, chưa chạy app Flutter, và chưa đọc kỹ từng file đánh giá.
