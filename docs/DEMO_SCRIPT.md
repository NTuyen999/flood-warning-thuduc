# Kịch bản Demo Ứng dụng Mobile Cảnh báo Mưa lớn TP Thủ Đức

Kịch bản demo ngắn gọn dành cho buổi báo cáo / thuyết trình đồ án (thời lượng 5–7 phút).

---

## 1. Chuẩn bị trước Demo (Checklist 2 phút)

- [ ] **Backend:** Đã chạy `uvicorn app.main:app --host 0.0.0.0 --port 8000` (hoặc chạy qua `run_demo.bat`).
- [ ] **Mạng Wi-Fi:** Máy tính và điện thoại thật cùng kết nối chung một mạng Wi-Fi LAN.
- [ ] **Ứng dụng Mobile:** Đã mở ứng dụng trên điện thoại (hoặc máy ảo Android).
- [ ] **Cấu hình máy chủ:** Vào icon **(i) Về dự báo này** -> **Cấu hình máy chủ** -> Nhập IP máy tính (ví dụ `http://192.168.1.10:8000`) -> Bấm **Kiểm tra kết nối** -> Kết nối OK.

---

## 2. Kịch bản Trình diễn (5–7 phút)

### Bước 1: Tổng quan Bản đồ Rủi ro Mưa lớn (1.5 phút)
- **Thao tác:** Mở app tại tab **Bản đồ**.
- **Lời thoại gợi ý:**
  > *"Xin chào thầy cô và các bạn. Đây là ứng dụng di động Cảnh báo nguy cơ mưa lớn tại TP Thủ Đức. Ngay khi mở app, bản đồ hiển thị các đoạn đường chính của Thủ Đức được tô màu theo 4 mức nguy cơ: Xanh (Thấp), Vàng (Trung bình), Cam (Cao), và Đỏ (Rất cao). Bổ sung vào đó là các ghim đánh dấu báo cáo thời gian thực từ cộng đồng người đi đường."*
- **Thao tác phụ:** Bấm chuyển các nút thời gian **+1h, +2h, ... +6h**.
- **Lời thoại:**
  > *"Người dùng có thể chọn xem dự báo cho từng giờ tới hoặc xem tổng thể 6 giờ để chủ động sắp xếp lịch trình di chuyển."*

---

### Bước 2: Xem Chi tiết Dự báo Tuyến đường (1.5 phút)
- **Thao tác:** Chạm vào một đoạn đường tô màu đỏ/cam (ví dụ: *Võ Văn Ngân* hoặc *Kha Vạn Cân*) -> Bấm **Xem dự báo** (hoặc chuyển sang tab **Tuyến đường** -> Chọn đường).
- **Lời thoại gợi ý:**
  > *"Khi chạm vào đoạn đường Võ Văn Ngân, ứng dụng hiển thị mức nguy cơ cao nhất trong 6 giờ tới, kèm thông tin thời tiết thời gian thực từ Open-Meteo như nhiệt độ, độ ẩm và lượng mưa. Bên dưới là biểu đồ 6 cột đại diện cho xác suất mưa lớn theo từng giờ."*

---

### Bước 3: Giải thích Nguyên nhân SHAP ("Vì sao?") (1 phút)
- **Thao tác:** Chạm vào cột có xác suất cao nhất trên biểu đồ (hoặc bấm nút **Vì sao?**).
- **Lời thoại gợi ý:**
  > *"Điểm đặc biệt của hệ thống là khả năng giải thích dự báo thông qua mô hình SHAP. Ứng dụng chỉ ra rõ những yếu tố thời tiết nào đang làm tăng nguy cơ (thanh màu đỏ) như lượng mưa tích lũy 3 giờ qua, và yếu tố nào đang làm giảm nguy cơ (thanh màu xanh). Lưu ý rằng đây là quan hệ đóng góp thống kê của mô hình học máy, không phải quan hệ nhân quả tuyệt đối."*

---

### Bước 4: Gửi Báo cáo Cộng đồng Thời gian thực (1.5 phút)
- **Thao tác:** Chạm nút **Báo cáo tại đây** (hoặc nút floating **Báo cáo** trên bản đồ) -> Chọn mức ngập **Ngập nhẹ** -> Chụp/Chọn 1 tấm ảnh -> Nhập ghi chú *"Nước ngập nhẹ qua mắt cá"* -> Bấm **Gửi báo cáo**.
- **Lời thoại gợi ý:**
  > *"Bên cạnh dự báo mô hình ML, thông tin từ cộng đồng đóng vai trò rất quan trọng. Người đi đường có thể gửi báo cáo tình trạng ngập thực tế kèm ảnh chụp và vị trí GPS. Báo cáo này sẽ ngay lập tức xuất hiện trên bản đồ để cảnh báo cho những người di chuyển sau."*

---

### Bước 5: Tab Cộng đồng và Thời hạn Báo cáo (1 phút)
- **Thao tác:** Chuyển sang tab **Cộng đồng**. Chuyển bộ lọc giữa **Còn hiệu lực** và **Tất cả**.
- **Lời thoại gợi ý:**
  > *"Tại tab Cộng đồng, danh sách báo cáo được xếp theo thời gian mới nhất. Các báo cáo tự động hết hạn sau 6 giờ để đảm bảo bản đồ không bị nhiễu bởi tin cũ. Người dùng có thể nhấn vào ảnh để phóng to xem chi tiết."*

---

## 3. Phương án Dự phòng khi Gặp Sự cố (Troubleshooting Guide)

| Sự cố phát sinh | Nguyên nhân | Cách xử lý nhanh tại chỗ |
|---|---|---|
| **Máy ảo Android vị trí ở Mỹ** | Định vị GPS mặc định của Emulator nằm ở Mỹ làm app báo "ngoài TP Thủ Đức". | 1. Dùng thao tác chạm tay trên bản đồ để chọn ghim vị trí trong Thủ Đức.<br/>2. Chạy lệnh: `adb emu geo fix 106.7718 10.8505`. |
| **Không kết nối được Backend / Lỗi mạng** | IP LAN bị đổi, Firewall chặn cổng 8000, hoặc chưa bật uvicorn. | 1. Kiểm tra lại uvicorn đang chạy `--host 0.0.0.0`.<br/>2. Kiểm tra `ipconfig` lấy đúng IP LAN.<br/>3. Mở icon **(i) Về dự báo này** -> **Cấu hình máy chủ** -> Nhập IP mới -> Bấm **Kiểm tra kết nối** & **Lưu**. |
| **Gửi báo cáo báo lỗi 409 (Trùng lặp)** | Đã có báo cáo cùng mức ngập ở vị trí này trong 30 phút qua. | Giải thích cho hội đồng: *"Ứng dụng có cơ chế chống rác (spam) và trùng lặp. Khi phát hiện báo cáo tương tự gần kề, server trả về 409 và app nhẹ nhàng ghi nhận mà không làm phiền người dùng."* |
| **Nền bản đồ không tải được tile** | Mạng bị chặn OpenStreetMap. | App đã mặc định dùng nguồn **Esri World Street Map** kèm fallback **CARTO** nên hoạt động mượt mà trên mọi mạng. |
