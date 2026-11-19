# Kịch bản Demo Ứng dụng Mobile Cảnh báo Mưa lớn TP Thủ Đức

Kịch bản demo ngắn gọn dành cho buổi báo cáo / thuyết trình đồ án (thời lượng 5–7 phút).

---

## 1. Chuẩn bị trước Demo (Checklist 2 phút)

- [ ] **Backend:** Đã chạy `uvicorn app.main:app --host 0.0.0.0 --port 8000` (hoặc chạy qua `run_demo.bat`).
- [ ] **Mạng Wi-Fi:** Máy tính và điện thoại thật cùng kết nối chung một mạng Wi-Fi LAN.
- [ ] **Ứng dụng Mobile:** Đã mở ứng dụng trên điện thoại (hoặc máy ảo Android).
- [ ] **Cấu hình máy chủ:** Vào icon **(i) Về dự báo này** -> **Cấu hình máy chủ** -> Nhập IP máy tính (ví dụ `http://192.168.1.10:8000`) -> Bấm **Kiểm tra kết nối** -> Kết nối OK.

---

## 2. Kịch bản Trình diễn Chức năng Chính (5 phút)

### Bước 1: Tổng quan Bản đồ Rủi ro Mưa lớn (1.5 phút)
- **Thao tác:** Mở app tại tab **Bản đồ**.
- **Lời thoại gợi ý:**
  > *"Xin chào thầy cô và các bạn. Đây là ứng dụng di động Cảnh báo nguy cơ mưa lớn tại TP Thủ Đức. Ngay khi mở app, bản đồ hiển thị các đoạn đường chính của Thủ Đức được tô màu theo 4 mức nguy cơ: Xanh (Thấp), Vàng (Trung bình), Cam (Cao), và Đỏ (Rất cao). Bổ sung vào đó là các ghim đánh dấu báo cáo thời gian thực từ cộng đồng người đi đường."*
- **Thao tác phụ:** Bấm chuyển các nút thời gian **+1h, +2h, ... +6h**.

---

### Bước 2: Xem Chi tiết Dự báo Tuyến đường & SHAP ("Vì sao?") (1.5 phút)
- **Thao tác:** Chạm vào đoạn đường *Võ Văn Ngân* -> Bấm **Xem dự báo** -> Bấm **Vì sao?**.
- **Lời thoại gợi ý:**
  > *"Khi chạm vào đoạn đường, ứng dụng hiển thị mức nguy cơ cao nhất trong 6 giờ tới kèm thời tiết hiện tại. Màn hình 'Vì sao?' giải thích chi tiết yếu tố thời tiết nào đang làm tăng nguy cơ (thanh màu đỏ) và yếu tố nào đang làm giảm nguy cơ (thanh màu xanh) theo mô hình SHAP."*

---

### Bước 3: Gửi Báo cáo Cộng đồng & Xem Lịch sử (2 phút)
- **Thao tác:** Chạm nút **Báo cáo** -> Chọn **Ngập nhẹ** -> Chọn ảnh -> Bấm **Gửi báo cáo** -> Chuyển tab **Cộng đồng**.
- **Lời thoại gợi ý:**
  > *"Người đi đường có thể gửi báo cáo tình trạng ngập thực tế kèm ảnh chụp và vị trí GPS. Báo cáo lập tức hiển thị trên bản đồ và tab Cộng đồng, tự động hết hạn sau 6 giờ để tránh làm nhiễu dữ liệu."*

---

## 3. Kịch bản Trình diễn Chế độ Mô phỏng & Gợi ý Đường đi (2 phút)

### Bước 4: Chế độ Mô phỏng 3 Kịch bản Thời tiết
- **Thao tác:** Vào icon **(i) Về dự báo này** -> Bật công tắc **Chế độ mô phỏng & Gợi ý đường đi** -> Trở về Bản đồ.
- **Thao tác phụ:** Chuyển đổi giữa 3 kịch bản: **Không mưa**, **Mưa vừa**, **Mưa nhiều**.
- **Lời thoại gợi ý:**
  > *"Để kiểm chứng khả năng phản ứng của hệ thống dưới các điều kiện thời tiết khác nhau, chúng em cung cấp Chế độ mô phỏng với 3 kịch bản: Không mưa, Mưa vừa và Mưa nhiều.
  > Bản đồ mô phỏng bổ sung các tuyến hẻm phụ: nét đứt xanh/vàng/cam/đỏ, có ký hiệu Hẻm cụt. Đáng chú ý, Hẻm cụt AL01 ở kịch bản Mưa nhiều chuyển sang mức Đỏ bị chặn do kế thừa tình trạng ngập tràn từ đường chính Kha Vạn Cân đoạn 2."*

---

### Bước 5: Gợi ý Tuyến đường ít Rủi ro hơn (Route Recommendation)
- **Thao tác:** Chạm icon Floating Action Button **Chỉ đường** (hình la bàn góc dưới bên phải) -> Màn hình **Gợi ý đường đi (Mô phỏng)** mở ra.
- **Thao tác 1 (Đường vòng tránh ngập - Detour):** Chọn Điểm đi **P1 (Đầu Kha Vạn Cân)**, Điểm đến **J2 (Ngã giao hẻm tắt)** ở kịch bản **Mưa nhiều**.
- **Lời thoại:**
  > *"Ở kịch bản Mưa nhiều, đoạn đường chính Kha Vạn Cân 2 bị ngập nặng (mức Đỏ/bị chặn). Thuật toán Dijkstra trọng số nguy cơ đã tự động gợi ý Tuyến đường vòng tránh ngập (màu xanh liền) đi qua Hẻm liên thông 78 (AL03 - mức Cam), né tránh đoạn ngập nặng (nét đứt xám)."*
- **Thao tác 2 (Bị chặn toàn bộ - Unreachable):** Chọn Điểm đi **P1**, Điểm đến **P2 (Cuối Kha Vạn Cân)** ở kịch bản **Mưa nhiều**.
- **Lời thoại:**
  > *"Nếu điểm đến là P2, do toàn bộ lối vào P2 qua Kha Vạn Cân 2 đều bị ngập Đỏ, hệ thống cảnh báo 'Không thể di chuyển' và khuyên người dùng nên hoãn chuyến đi. Tất cả màn hình gợi ý đường đi đều hiển thị rõ tuyên bố miễn trừ trách nhiệm mô phỏng."*

---

## 4. Phương án Dự phòng khi Gặp Sự cố (Troubleshooting Guide)

| Sự cố phát sinh | Nguyên nhân | Cách xử lý nhanh tại chỗ |
|---|---|---|
| **Máy ảo Android vị trí ở Mỹ** | Định vị GPS mặc định của Emulator nằm ở Mỹ làm app báo "ngoài TP Thủ Đức". | 1. Chạm tay trên bản đồ để chọn ghim vị trí trong Thủ Đức.<br/>2. Chạy lệnh: `adb emu geo fix 106.7718 10.8505`. |
| **Không kết nối được Backend / Lỗi mạng** | IP LAN bị đổi, Firewall chặn cổng 8000, hoặc chưa bật uvicorn. | 1. Kiểm tra uvicorn đang chạy `--host 0.0.0.0`.<br/>2. Mở icon **(i) Về dự báo này** -> **Cấu hình máy chủ** -> Nhập IP mới -> Bấm **Kiểm tra kết nối** & **Lưu**. |
| **Gửi báo cáo báo lỗi 409 (Trùng lặp)** | Đã có báo cáo cùng mức ngập ở vị trí này trong 30 phút qua. | Giải thích: *"Hệ thống có cơ chế chống trùng lặp. Server trả 409 và app hiển thị thông báo nhẹ nhàng."* |
| **Bản đồ mô phỏng không hiện hẻm** | Chưa bật công tắc Chế độ mô phỏng. | Mở icon **(i) Về dự báo này** -> Bật **Chế độ mô phỏng & Gợi ý đường đi**. |
