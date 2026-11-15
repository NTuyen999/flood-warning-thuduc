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

## Ghi chú

- Nền bản đồ: mặc định dùng Esri World Street Map (`https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}`) với fallback CARTO. Có thể tùy chỉnh qua `--dart-define=TILE_URL=...` và `--dart-define=TILE_ATTRIBUTION=...`. Tự đảo màu khi máy ở chế độ tối. Nguồn bản đồ hiện tại chỉ phù hợp cho đồ án/demo; khi phát hành sản phẩm thật cần mua bản quyền hoặc chọn dịch vụ tile riêng.
- `android:usesCleartextTraffic="true"` chỉ để gọi `http://` lúc dev và demo LAN. Khi triển khai bản sản phẩm có HTTPS thì phải bỏ đi.
- Chưa cấu hình quyền vị trí/ảnh cho iOS (`Info.plist`).
