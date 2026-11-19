# Hướng dẫn Sử dụng Ứng dụng Cảnh báo Mưa lớn TP Thủ Đức

Ứng dụng di động hỗ trợ người dân và người di chuyển tại TP Thủ Đức theo dõi nguy cơ mưa lớn trong 1–6 giờ tới, chia sẻ thông tin ngập nước thời gian thực và thử nghiệm tính năng gợi ý đường đi trên chế độ mô phỏng.

---

## 1. Màn hình Bản đồ Nguy cơ

Màn hình chính hiển thị bản đồ trực quan vùng TP Thủ Đức với các tuyến đường chính được tô màu theo 4 mức nguy cơ:

- **Xanh lá (Thấp):** Khả năng mưa lớn < 10%. Đường xá an toàn, khô ráo.
- **Vàng (Trung bình):** Khả năng mưa lớn 10% – 30%. Có thể có mưa, nên chú ý quan sát.
- **Cam (Cao):** Khả năng mưa lớn 30% – 60%. Cân nhắc thay đổi thời gian đi hoặc chuyển lộ trình.
- **Đỏ (Rất cao):** Khả năng mưa lớn ≥ 60%. Dễ xảy ra mưa lớn gây ngập, bị cản trở di chuyển nghiêm trọng.

### Ký hiệu đường xá trên bản đồ:
- **Đường nét liền dày:** Tuyến đường chính.
- **Đường nét đứt mảnh:** Tuyến hẻm phụ (chỉ hiển thị ở Chế độ mô phỏng).
- **Biểu tượng dấu cấm đỏ/tròn:** Ký hiệu Hẻm cụt.
- **Đường viền đỏ sẫm:** Đoạn đường/hẻm bị BỊ CHẶN (mức Đỏ).

---

## 2. Xem Chi tiết Dự báo và Màn "Vì sao?"

Tại màn hình **Chi tiết Dự báo** của một đoạn đường:
1. **Thông tin thời tiết:** Hiển thị nhiệt độ, độ ẩm, lượng mưa và tốc độ gió hiện tại.
2. **Biểu đồ dự báo 6 giờ:** Hiển thị xác suất mưa lớn cho 6 giờ tiếp theo.
3. **Màn hình "Tại sao cảnh báo?" (Giải thích SHAP):** Chạm vào một cột giờ bất kỳ trên biểu đồ hoặc bấm nút **Vì sao?**. Màn hình sẽ liệt kê các yếu tố thời tiết đóng góp vào mức nguy cơ (thanh màu đỏ làm tăng nguy cơ, thanh màu xanh làm giảm nguy cơ).

---

## 3. Gửi Báo cáo Ngập từ Cộng đồng

Khi bạn đang lưu thông trên đường và phát hiện tình trạng ngập hoặc khô ráo:

1. Nhấn nút **Báo cáo** (hoặc icon dấu cộng trên bản đồ).
2. **Bước 1 - Chọn tình trạng:** Không ngập / Ngập nhẹ / Ngập nặng.
3. **Bước 2 - Chọn vị trí:** Mặc định app lấy vị trí GPS hiện tại hoặc chạm bản đồ để ghim vị trí.
4. **Bước 3 - Ảnh & Ghi chú (tùy chọn):** Chụp ảnh thực tế, nhập mô tả ngắn.
5. Nhấn **Gửi báo cáo**.

---

## 4. Chế độ Mô phỏng & Gợi ý Đường đi (Demo Features)

### Cách bật Chế độ Mô phỏng:
1. Nhấn icon **(i) Về dự báo này** ở góc trên bên phải màn hình.
2. Bật công tắc **Chế độ mô phỏng & Gợi ý đường đi**.
3. Khi bật, thanh banner màu cam/tím xuất hiện ở đầu màn hình: `"ĐANG XEM DỮ LIỆU MÔ PHỎNG – không phải dự báo thật"`.

### Thử nghiệm 3 Kịch bản Thời tiết:
Trên thanh chọn kịch bản ở đầu bản đồ:
- **Không mưa:** Mọi tuyến đường và hẻm đều thông thoáng (màu Xanh).
- **Mưa vừa:** Xuất hiện nguy cơ Vàng/Cam trên Kha Vạn Cân & Tô Ngọc Vân.
- **Mưa nhiều:** Khu vực Kha Vạn Cân 2 và Hẻm cụt AL01, AL02 bị ngập Đỏ (Bị chặn).

### Sử dụng Tính năng Gợi ý Đường đi:
1. Nhấn nút Floating Action Button **Chỉ đường** (hình la bàn góc dưới bên phải).
2. Chọn **Điểm đi** (ví dụ: *P1 - Đầu Kha Vạn Cân*) và **Điểm đến** (ví dụ: *J2 - Ngã giao hẻm tắt*).
3. Chọn kịch bản thời tiết muốn thử nghiệm.
4. Kết quả hiển thị:
   - **Tuyến đường khuyến nghị (nét liền xanh dương):** Tuyến đường ít rủi ro nhất.
   - **Tuyến đường ngắn nhất bị cản trở (nét đứt xám):** Tuyến đường ngắn nhất nhưng gặp đoạn ngập lụt.
   - **Thẻ trạng thái:** `Tuyến thông suốt`, `Đường vòng tránh ngập`, `Cảnh báo hẻm ngập`, hoặc `Không thể di chuyển`.
   - **Thông số:** Quãng đường (m/km), thời gian ước tính (phút), các lời khuyên và tuyên bố miễn trừ trách nhiệm mô phỏng.

---

## 5. Thay đổi Máy chủ Kết nối (Dành cho Demo)

1. Nhấn icon **(i) Về dự báo này** -> Mục **Cấu hình máy chủ** -> chọn **Thay đổi**.
2. Nhập địa chỉ URL máy chủ (ví dụ: `http://192.168.1.10:8000`).
3. Nhấn **Kiểm tra kết nối** -> **Lưu**.
