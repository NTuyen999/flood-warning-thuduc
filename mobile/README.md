# App Flutter: Cảnh báo mưa lớn Thủ Đức

App lấy toàn bộ dữ liệu từ backend ([../backend/README.md](../backend/README.md)), không còn dữ liệu mock.

## Các màn hình

| Màn | Nội dung | API |
|---|---|---|
| Bản đồ | Đoạn đường tô màu theo nguy cơ, marker báo cáo cộng đồng, chọn giờ +1…+6h, chú giải, vị trí của tôi | `/map/risks`, `/reports` |
| Tuyến đường | Danh sách đoạn đường, tìm theo tên, đoạn có báo cáo ngập xếp trước | (dùng chung dữ liệu bản đồ) |
| Cộng đồng | Báo cáo gần đây, lọc "Còn hiệu lực / Tất cả", xem ảnh | `/reports` |
| Dự báo | Thẻ tóm tắt, thời tiết hiện tại, 6 cột theo giờ thật, báo cáo trên đoạn | `/forecast`, `/weather/current` |
| Vì sao? | Các yếu tố SHAP: thanh đỏ làm tăng, thanh xanh làm giảm nguy cơ | `/explain` |
| Báo cáo | Chọn mức ngập bằng 3 thẻ, ghim vị trí trên bản đồ, ảnh, ghi chú | `/uploads`, `/reports` |

## Chạy

Backend phải chạy trước (`docker compose up -d --wait db` rồi uvicorn, hoặc `run_demo.bat` ở thư mục gốc).

```bash
cd mobile
flutter run                                              # máy ảo Android: gọi http://10.0.2.2:8000
flutter run --dart-define=API_URL=http://192.168.1.10:8000   # điện thoại thật cùng Wi-Fi
```

Với điện thoại thật, chạy backend bằng `--host 0.0.0.0` và thay IP bằng IP máy tính trong mạng LAN.

Trên máy ảo, GPS mặc định ở Mỹ nên app sẽ báo "ngoài TP Thủ Đức". Khi đó chạm vào bản đồ trong màn Báo cáo để đặt ghim, hoặc đặt vị trí máy ảo: `adb emu geo fix 106.7718 10.8505`.

## Kiểm thử

```bash
flutter analyze
flutter test
```

Test dùng backend giả ở tầng HTTP (`FakeBackend` trong [test/widget_test.dart](test/widget_test.dart)), nên chạy qua đúng code gọi API và đọc JSON của app.

## Cấu hình Máy chủ API Linh hoạt

Ngoài việc truyền `--dart-define=API_URL=...` lúc build, người dùng có thể đổi địa chỉ máy chủ trực tiếp khi ứng dụng đang chạy:
1. Nhấn icon **(i) Về dự báo này** ở góc trên bên phải thanh AppBar.
2. Tại mục **Cấu hình máy chủ**, chọn **Thay đổi**.
3. Nhập URL máy chủ mới (ví dụ: `http://192.168.1.10:8000`).
4. Nhấn **Kiểm tra kết nối** để gọi thử GET `/health` (hiển thị thông báo OK + `model_version`, hoặc báo lỗi tiếng Việt).
5. Nhấn **Lưu** để áp dụng ngay mà không cần khởi động lại ứng dụng. URL sẽ được lưu vào `shared_preferences`.

## Build APK Release & Ký Keystore

### Build APK
```bash
# Debug APK
flutter build apk --debug

# Release APK
flutter build apk --release --dart-define=API_URL=http://10.0.2.2:8000
```

### Cấu hình Ký Release (Tùy chọn)
Mặc định nếu không tìm thấy file `android/key.properties`, app sẽ rơi về ký bằng **debug keystore** để thuận tiện demo (có in cảnh báo).

Nếu muốn ký release chính thức:
1. Tạo keystore bằng `keytool`:
   ```bash
   keytool -genkey -v -keystore android/app/upload-keystore.jks -storetype JKS -keyalg RSA -keysize 2048 -validity 10000 -alias upload
   ```
2. Tạo file `android/key.properties` với nội dung:
   ```properties
   storePassword=<mật_khẩu_keystore>
   keyPassword=<mật_khẩu_key>
   keyAlias=upload
   storeFile=app/upload-keystore.jks
   ```
3. Chạy lại `flutter build apk --release`.

*Lưu ý:* Cả `key.properties`, `*.jks` và `*.keystore` đã được liệt kê trong `.gitignore`, tuyệt đối không commit lên Git.

## Xử lý Sự cố Thường gặp

1. **Không kết nối được Backend:**
   - Đảm bảo uvicorn chạy `--host 0.0.0.0`.
   - Kiểm tra IP LAN máy tính (`ipconfig`).
   - Vào màn "Máy chủ" trong app để thử kiểm tra kết nối.
2. **GPS máy ảo báo nằm ngoài TP Thủ Đức:**
   - Chạm tay trên bản đồ để chọn ghim thủ công, hoặc gán tọa độ cho emulator: `adb emu geo fix 106.7718 10.8505`.
3. **Mạng chặn tile bản đồ:**
   - App đã mặc định sử dụng Esri World Street Map và fallback CARTO, hỗ trợ tùy chỉnh qua `--dart-define=TILE_URL=...`.

## Ghi chú

- Nền bản đồ: mặc định dùng Esri World Street Map (`https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}`) với fallback CARTO. Có thể tùy chỉnh qua `--dart-define=TILE_URL=...` và `--dart-define=TILE_ATTRIBUTION=...`. Tự đảo màu khi máy ở chế độ tối. Nguồn bản đồ hiện tại chỉ phù hợp cho đồ án/demo; khi phát hành sản phẩm thật cần mua bản quyền hoặc chọn dịch vụ tile riêng.
- `android:usesCleartextTraffic="true"` chỉ để gọi `http://` lúc dev và demo LAN. Khi triển khai bản sản phẩm có HTTPS thì phải bỏ đi.
- Chưa cấu hình quyền vị trí/ảnh cho iOS (`Info.plist`).
