# Đánh giá Tính năng "Tuyến đường An toàn" (Optional Feature - MB11)

Tài liệu giải thích lý do kỹ thuật chưa triển khai tính năng tìm tuyến đường an toàn (tránh điểm ngập) trong phiên bản hiện tại và đề xuất thiết kế tối thiểu cho giai đoạn sau.

---

## 1. Lý do Chưa Triển khai trong Phiên bản Hiện tại

1. **Backend chưa có Routing Engine:**
   - Hệ thống backend hiện tại sử dụng PostgreSQL + PostGIS lưu trữ các đoạn đường chính (`road_segments`) dạng danh sách đoạn phẳng (flat segment list), **chưa xây dựng đồ thị mạng lưới giao thông (Road Network Graph)** với các đỉnh (nodes) và cạnh (edges).
   - Không có công cụ tìm đường như pgRouting, OSRM hoặc GraphHopper để thực hiện thuật toán Dijkstra/A* tìm đường đi giữa 2 điểm bất kỳ.

2. **Dữ liệu Mô hình ML Đồng nhất trên Mọi Đoạn đường:**
   - Mô hình XGBoost ML hiện tại sử dụng 1 điểm đầu vào thời tiết chung cho toàn bộ khu vực TP Thủ Đức (10.85, 106.77).
   - Do đó, mọi đoạn đường trong cùng một mốc giờ đều có **xác suất rủi ro mưa lớn giống hệt nhau** từ mô hình ML.
   - Nếu tìm "tuyến ít rủi ro hơn", thuật toán sẽ chỉ có thể dựa hoàn toàn vào các báo cáo ngập từ cộng đồng (`report_summary`), vốn mang tính thời điểm, rải rác và không đại diện cho toàn bộ mạng lưới giao thông. Việc khẳng định một tuyến đường là "an toàn" trong điều kiện dữ liệu này là **không đủ cơ sở khoa học và thiếu an toàn cho người dùng**.

---

## 2. Thiết kế Tối thiểu Nếu Triển khai trong Tương lai

Nếu hệ thống được nâng cấp trong tương lai, kiến trúc tối thiểu cho tính năng tìm đường tránh ngập bao gồm:

### A. Phía Backend:
- Cài đặt extension **pgRouting** trên PostgreSQL/PostGIS.
- Chuyển GeoJSON các đoạn đường thành đồ thị mạng lưới giao thông (`road_network_vertices_pgr` & `road_network_edges`).
- Định nghĩa hàm trọng số cạnh (Edge Weight Cost):
  $$\text{Cost} = \text{Chiều dài (m)} \times \left(1 + w_1 \cdot \text{Xác suất rủi ro ML} + w_2 \cdot \text{Trọng số ngập cộng đồng}\right)$$
- Cung cấp REST API: `GET /api/v1/route?start_lat=...&start_lon=...&end_lat=...&end_lon=...` trả về GeoJSON danh sách các đoạn đường tối ưu.

### B. Phía Mobile App:
- Thêm giao diện chọn "Điểm đi" và "Điểm đến" trên bản đồ.
- Hiển thị tuyến đường gợi ý bằng `PolylineLayer` nét đứt hoặc màu xanh dương riêng biệt.

---

## 3. Tuyên bố Miễn trừ Tách biệt (Disclaimer)

> **CẢNH BÁO QUAN TRỌNG:**
> Ứng dụng **KHÔNG CAM KẾT AN TOÀN TUYỆT ĐỐI** trên bất kỳ tuyến đường nào được gợi ý. Thông tin dự báo nguy cơ mưa lớn và báo cáo ngập từ cộng đồng chỉ mang tính chất tham khảo hỗ trợ quyết định di chuyển. Người lái xe phải luôn quan sát tình hình giao thông thực tế tại hiện trường và tuân thủ hướng dẫn của lực lượng chức năng.
