# Danh mục Kịch bản Kiểm thử QA trên Thiết bị Thật (Mobile)

Tài liệu hướng dẫn thiết lập môi trường kiểm thử và danh mục các test case dành cho ứng dụng **Cảnh báo mưa lớn TP Thủ Đức** trên thiết bị di động Android thật.

---

## 1. Thông tin Thiết bị Kiểm thử

| Thông tin | Giá trị |
|---|---|
| **Tên thiết bị (Model)** | Samsung SM-A736B (hoặc điền thiết bị thực tế) |
| **Phiên bản Android** | Android 16 (API 36) |
| **Địa chỉ IP máy chủ LAN** | `http://192.168.x.x:8000` |
| **Ngày thực hiện test** | YYYY-MM-DD |
| **Người thực hiện** | |

### Minhten & Ảnh chụp màn hình kiểm thử
*(Thêm ảnh chụp thực tế trên thiết bị khi nghiệm thu tại đây)*
- [ ] Ảnh 1: Màn hình bản đồ nguy cơ mưa lớn trên điện thoại thật
- [ ] Ảnh 2: Màn hình kiểm tra kết nối Máy chủ API
- [ ] Ảnh 3: Màn hình gửi báo cáo ngập thành công kèm ảnh
- [ ] Ảnh 4: Màn hình giải thích yếu tố SHAP ("Vì sao?")

---

## 2. Hướng dẫn Cấu hình Môi trường Test

### Bước 1: Khởi động Backend trên Máy tính
Mở PowerShell tại thư mục `backend/` và chạy uvicorn lắng nghe mọi giao diện mạng LAN (`0.0.0.0`):
```powershell
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Bước 2: Cho phép Qua Windows Firewall
Nếu điện thoại không kết nối được máy tính, mở PowerShell với quyền Administrator để mở cổng 8000:
```powershell
New-NetFirewallRule -DisplayName "FastAPI 8000" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

### Bước 3: Lấy Địa chỉ IP LAN của Máy tính
```powershell
ipconfig
```
Tìm địa chỉ **IPv4 Address** của card Wi-Fi (ví dụ: `192.168.1.10`).

### Bước 4: Chạy App trên Điện thoại qua ADB
Lấy ID thiết bị kết nối qua Wi-Fi hoặc USB:
```powershell
adb devices
```
Chạy ứng dụng (đặt ID thiết bị trong dấu nháy kép nếu chứa khoảng trắng hoặc ký tự đặc biệt):
```powershell
cd mobile
flutter run -d "<device-id>" --dart-define=API_URL=http://192.168.1.10:8000
```
*(Mẹo: Bạn cũng có thể mở app, vào góc trên bên phải icon **(i) Về dự báo này** -> **Cấu hình máy chủ** -> Nhập URL IP LAN và bấm **Kiểm tra kết nối**).*

---

## 3. Bảng Kịch bản Kiểm thử (Test Cases)

| Mã TC | Hạng mục test | Các bước thực hiện | Kết quả mong đợi | Kết quả (Đạt / Không Đạt) | Ghi chú |
|---|---|---|---|---|---|
| **TC01** | Tải bản đồ nguy cơ rủi ro ban đầu | Mở app lần đầu sau khi bật backend | Bản đồ hiển thị các đoạn đường tô màu rủi ro (xanh/vàng/cam/đỏ), có chú giải legend và marker báo cáo. | | |
| **TC02** | Đổi khoảng thời gian dự báo (+1h..+6h) | Chuyển đổi giữa các nút giờ +1h, +2h, ... +6h và "Tất cả" trên bản đồ | Màu sắc các đoạn đường cập nhật tương ứng với mức nguy cơ trong giờ được chọn. | | |
| **TC03** | Chọn đoạn đường trên bản đồ | Chạm vào một đoạn đường bất kỳ trên bản đồ | Xuất hiện card thông tin đoạn đường (Tên đường, mức nguy cơ, số báo cáo ngập). | | |
| **TC04** | Xem chi tiết dự báo tuyến đường | Chạm vào một đoạn đường -> Bấm mở màn hình Dự báo | Hiển thị tóm tắt mức nguy cơ, thời tiết hiện tại từ Open-Meteo, biểu đồ 6 cột theo giờ. | | |
| **TC05** | Xem giải thích yếu tố SHAP ("Vì sao?") | Trong màn Dự báo, chạm vào một cột giờ dự báo | Màn hình "Vì sao?" mở ra với danh sách thanh SHAP (đỏ làm tăng, xanh làm giảm nguy cơ). | | |
| **TC06** | Gửi báo cáo ngập kèm GPS | Về màn Báo cáo, chọn vị trí GPS hiện tại, chọn mức ngập "Ngập nhẹ" -> Bấm "Gửi báo cáo" | Báo cáo gửi thành công, thông báo cảm ơn xuất hiện, bản đồ cập nhật marker mới. | | |
| **TC07** | Gửi báo cáo ngập kèm ảnh từ Camera | Chọn chụp ảnh từ Camera trong màn Báo cáo -> Chụp ảnh -> Bấm gửi | Ảnh tải lên `/uploads` thành công, URL ảnh gắn kèm báo cáo. | | |
| **TC08** | Gửi báo cáo ngập kèm ảnh từ Thư viện | Chọn chọn ảnh từ Thư viện -> Chọn file ảnh -> Bấm gửi | Ảnh được upload thành công và hiển thị trong chi tiết báo cáo. | | |
| **TC09** | Gửi báo cáo trùng lặp (409) | Trong vòng 30 phút gửi 2 báo cáo cùng mức ngập ở cùng vị trí | Server trả lỗi 409, app hiển thị hộp thoại "Đã có người báo cáo" thay vì crash. | | |
| **TC10** | Báo cáo ngoài khu vực TP Thủ Đức (422) | Chọn vị trí ghim ngoài bản đồ Thủ Đức (ví dụ Quận 1) -> Bấm gửi | Server trả lỗi 422, app thông báo "Vị trí nằm ngoài TP Thủ Đức" và giữ nguyên form. | | |
| **TC11** | Từ chối quyền vị trí GPS | Tắt quyền Location của app trong Cài đặt Android -> Mở lại app | App không bị văng, hiển thị thông báo và cho phép người dùng cắm ghim tay trên bản đồ. | | |
| **TC12** | Mất mạng / Backend ngắt kết nối | Tắt Wi-Fi hoặc tắt uvicorn backend -> Bấm "Làm mới" | Hiển thị màn hình lỗi kết nối kèm nút "Thử lại". Bật lại mạng -> Bấm "Thử lại" hoạt động bình thường. | | |
| **TC13** | Dữ liệu cũ (Stale data) | Backend trả dữ liệu có `"stale": true` | Hiển thị banner cảnh báo "Dữ liệu cũ (chậm cập nhật)" ở màn hình bản đồ và dự báo. | | |
| **TC14** | Chế độ tối (Dark Mode) | Chuyển hệ thống Android sang Dark Theme | Bản đồ basemap tự đảo màu tối, giao diện app chuyển sang phông tối tương thích. | | |
| **TC15** | Phông chữ lớn (Accessibility) | Bật Text Size lên 150% - 200% trong Cài đặt Android | Chữ to ra nhưng giao diện tự cuộn/co giãn, không có dải xọc vàng đen báo tràn (RenderFlex overflow). | | |
| **TC16** | Xoay ngang màn hình (Landscape) | Xoay ngang điện thoại ở các màn hình | Bố cục màn hình co giãn hợp lý, các danh sách và form đều cuộn được. | | |
| **TC17** | Vuốt để làm mới (Pull to refresh) | Vuốt kéo xuống ở màn Tuyến đường và Cộng đồng | Vòng quay loading xuất hiện và dữ liệu mới được tải lại từ API. | | |
| **TC18** | Lọc danh sách báo cáo Cộng đồng | Chuyển giữa bộ lọc "Còn hiệu lực" và "Tất cả" | Mặc định chỉ hiện tin trong 6 giờ qua. Chuyển "Tất cả" hiện thêm các tin đã hết hạn. | | |
