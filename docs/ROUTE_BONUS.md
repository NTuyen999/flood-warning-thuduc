# Tính năng "Gợi ý Tuyến đường ít Rủi ro hơn" (Route Recommendation - Demo Scope)

Tài liệu chi tiết việc cài đặt tính năng gợi ý tuyến đường tránh ngập lụt trên mạng lưới mô phỏng TP Thủ Đức.

---

## 1. Trạng thái Cài đặt & Phạm vi Thực hiện

Tính năng gợi ý đường đi đã được cài đặt **hoàn chỉnh ở phạm vi mô phỏng (Demo Simulation Scope)**:

1. **Backend Routing Engine:** Xây dựng router định tuyến Dijkstra (`/api/v1/demo/route`) dựa trên ma trận trọng số đa yếu tố (chiều dài $\times$ hệ số mức nguy cơ).
2. **Mạng lưới Mô phỏng (Demo Network):** Tạo mạng lưới giao thông thu nhỏ gồm 29 đoạn đường chính và 4 hẻm phụ (gồm hẻm cụt ngập tràn từ đường chính, hẻm cụt tự ngập, hẻm liên thông đường vòng và hẻm cụt an toàn).
3. **Ứng dụng Mobile:** Thêm màn hình **Gợi ý đường đi** ([route_screen.dart](file:///D:/HK5_2026/NT120/Project/mobile/lib/features/route/route_screen.dart)), vẽ tuyến đường khuyến nghị (nét liền xanh) và tuyến đường ngắn nhất bị cản trở (nét đứt xám), hiển thị trạng thái badge (`ok`, `detour`, `warning`, `unreachable`).

---

## 2. Các Giới hạn Kỹ thuật Cần Nêu rõ khi Báo cáo

- **Đồ thị mô phỏng thu nhỏ:** Mạng lưới giao thông hiện tại là đồ thị giả lập 11 nút / 11 cạnh trên khu vực Kha Vạn Cân, chưa phải đồ thị giao thông toàn bộ TP Thủ Đức.
- **Dữ liệu đầu vào ML đồng nhất:** Mô hình XGBoost ML hiện tại lấy 1 điểm tọa độ thời tiết cho cả khu vực, do đó xác suất dự báo trên các đoạn đường chính thuần túy đến từ mô hình ML là đồng nhất. Các kịch bản mưa (`none`, `moderate`, `heavy`) được thiết lập để giả định sự khác biệt nguy cơ giữa các đoạn.
- **Hình học hẻm:** Các hẻm AL01–AL04 là dữ liệu giả lập nhằm minh họa quy tắc kế thừa ngập lụt (`inherits_from`) và xử lý hẻm cụt (`dead_end`), không phải vị trí hẻm thực tế.

---

## 3. Thuật toán và Quy tắc Trọng số Định tuyến

$$\text{Cost} = \text{Length (m)} \times \text{Multiplier}(\text{risk\_level})$$

- `green` (<10%): Multiplier = `1.0`
- `yellow` (10-30%): Multiplier = `1.4`
- `orange` (30-60%): Multiplier = `4.0`
- `red` (≥60%): Multiplier = `Infinity` (Đoạn đường bị chặn, loại khỏi đồ thị).
- **Quy tắc Hẻm cụt:** Cạnh hẻm cụt chỉ được phép duyệt qua nếu điểm đi hoặc điểm đến nằm trong chính hẻm đó.

---

## 4. Tuyên bố Miễn trừ Tách biệt (Disclaimer)

> **CẢNH BÁO QUAN TRỌNG:**
> Ứng dụng **KHÔNG CAM KẾT AN TOÀN TUYỆT ĐỐI** trên bất kỳ tuyến đường nào được gợi ý. Thông tin dự báo nguy cơ mưa lớn và gợi ý đường đi trên chế độ mô phỏng chỉ mang tính chất tham khảo hỗ trợ quyết định di chuyển. Người lái xe phải luôn quan sát tình hình giao thông thực tế tại hiện trường và tuân thủ hướng dẫn của lực lượng chức năng.
