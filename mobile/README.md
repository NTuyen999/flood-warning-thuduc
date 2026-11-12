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

## Ghi chú

- Nền bản đồ: tile chuẩn của OpenStreetMap (© OpenStreetMap contributors), tự đảo màu khi máy ở chế độ tối. Chỉ phù hợp lưu lượng nhỏ (demo); khi phát hành thật cần dùng nhà cung cấp tile riêng.
- `android:usesCleartextTraffic="true"` chỉ để gọi `http://` lúc dev. Khi backend có HTTPS thì bỏ đi.
- Chưa cấu hình quyền vị trí/ảnh cho iOS (`Info.plist`).
