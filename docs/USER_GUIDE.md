# Hướng dẫn Sử dụng Ứng dụng Cảnh báo Mưa lớn TP Thủ Đức

Ứng dụng di động hỗ trợ người dân và người di chuyển tại TP Thủ Đức theo dõi nguy cơ mưa lớn trong 1–6 giờ tới và chia sẻ thông tin ngập nước thời gian thực.

---

## 1. Màn hình Bản đồ Nguy cơ

Màn hình chính hiển thị bản đồ trực quan vùng TP Thủ Đức với các tuyến đường chính được tô màu theo mức nguy cơ mưa lớn:

- **Xanh lá (Thấp):** Khả năng mưa lớn < 10%. Đường xá an toàn, khô ráo.
- **Vàng (Trung bình):** Khả năng mưa lớn 10% – 30%. Có thể có mưa, nên chú ý quan sát.
- **Cam (Cao):** Khả năng mưa lớn 30% – 60%. Cân nhắc thay đổi thời gian đi hoặc chuyển lộ trình.
- **Đỏ (Rất cao):** Khả năng mưa lớn ≥ 60%. Dễ xảy ra mưa lớn gây ngập, nên tránh các tuyến đường trũng thấp.

### Thao tác trên bản đồ:
- **Chọn khoảng giờ:** Dùng thanh chọn giờ phía trên (`+1h`, `+2h`, ... `+6h`, hoặc `Cả 6 giờ`) để xem dự báo theo mốc thời gian mong muốn.
- **Xem đoạn đường:** Chạm trực tiếp vào đoạn đường tô màu để xem tên tuyến đường và mức nguy cơ.
- **Vị trí của tôi:** Bấm vào nút định vị góc dưới bên phải để di chuyển bản đồ về vị trí hiện tại.

---

## 2. Xem Chi tiết Dự báo và Màn "Vì sao?"

Tại màn hình **Chi tiết Dự báo** của một đoạn đường:
1. **Thông tin thời tiết:** Hiển thị nhiệt độ, độ ẩm, lượng mưa và tốc độ gió hiện tại.
2. **Biểu đồ dự báo 6 giờ:** Hiển thị xác suất mưa lớn cho 6 giờ tiếp theo.
3. **Màn hình "Tại sao cảnh báo?" (Giải thích SHAP):** Chạm vào một cột giờ bất kỳ trên biểu đồ hoặc bấm nút **Vì sao?**. Màn hình sẽ liệt kê các yếu tố thời tiết đóng góp vào mức nguy cơ (thanh màu đỏ làm tăng nguy cơ, thanh màu xanh làm giảm nguy cơ).

*Lưu ý:* Các chỉ số SHAP thể hiện mức đóng góp thống kê của mô hình học máy từ số liệu thời tiết, không phải quan hệ nguyên nhân - kết quả tuyệt đối.

---

## 3. Gửi Báo cáo Ngập từ Cộng đồng

Khi bạn đang lưu thông trên đường và phát hiện tình trạng ngập hoặc khô ráo, hãy gửi báo cáo để hỗ trợ cộng đồng:

1. Nhấn nút **Báo cáo** (hoặc icon dấu cộng trên bản đồ).
2. **Bước 1 - Chọn tình trạng:**
   - **Không ngập:** Đường khô ráo, di chuyển bình thường.
   - **Ngập nhẹ:** Nước ngập nông (đến mắt cá chân), xe cộ đi lại bình thường.
   - **Ngập nặng:** Nước ngập sâu (tới bánh xe trở lên), nguy cơ chết máy cao.
3. **Bước 2 - Chọn vị trí:** Mặc định app lấy vị trí GPS của bạn. Nếu muốn báo cáo cho nơi khác, hãy chạm vào điểm tương ứng trên bản đồ để cắm ghim.
4. **Bước 3 - Ảnh & Ghi chú (tùy chọn):** Chụp ảnh thực tế hoặc chọn ảnh từ thư viện, nhập thêm mô tả ngắn.
5. Nhấn **Gửi báo cáo**.

---

## 4. Danh sách Cộng đồng và Xử lý Sự cố

### Xem báo cáo từ cộng đồng:
- Chuyển sang tab **Cộng đồng** để xem toàn bộ danh sách báo cáo thời gian thực.
- Các báo cáo tự động hết hạn và ẩn đi sau **6 giờ** để đảm bảo thông tin luôn mới nhất.
- Bấm vào hình ảnh trong báo cáo để phóng to xem hình ảnh chi tiết.

### Thay đổi Máy chủ kết nối (Dành cho Demo / Thử nghiệm):
1. Nhấn icon **(i) Về dự báo này** ở góc trên bên phải màn hình.
2. Tại mục **Cấu hình máy chủ**, chọn **Thay đổi**.
3. Nhập địa chỉ URL máy chủ (ví dụ: `http://192.168.1.10:8000`).
4. Nhấn **Kiểm tra kết nối** để đảm bảo máy chủ hoạt động, sau đó nhấn **Lưu**.
