# Bảng So sánh 3 Kịch bản Mô phỏng và Kết quả Định tuyến (Demo Scenarios)

Tài liệu tổng hợp trạng thái các đoạn đường chính, hẻm và kết quả gợi ý tuyến đường theo 3 kịch bản thời tiết giả lập (`none`, `moderate`, `heavy`).

---

## 1. Bảng Trạng thái Đoạn đường và Hẻm theo Kịch bản (Tối đa 1–6 giờ)

| Mã đoạn / Hẻm | Tên đối tượng | Loại (`kind`) | Hẻm cụt (`dead_end`) | Kế thừa (`inherits_from`) | Kịch bản `none` (Không mưa) | Kịch bản `moderate` (Mưa vừa) | Kịch bản `heavy` (Mưa nhiều) |
|---|---|---|---|---|---|---|---|
| **SEG01** | Kha Vạn Cân (đoạn 1) | Đường chính | Không | Không | Xanh (<10%) | Vàng (25%) | Cam (55%) |
| **SEG02** | Kha Vạn Cân (đoạn 2) | Đường chính | Không | Không | Xanh (<10%) | Cam (52%) | **Đỏ (78% - BỊ CHẶN)** |
| **SEG05** | Tô Ngọc Vân (đoạn 1) | Đường chính | Không | Không | Xanh (<10%) | Vàng (24%) | Cam (50%) |
| **SEG06** | Tô Ngọc Vân (đoạn 2) | Đường chính | Không | Không | Xanh (<10%) | Cam (50%) | **Đỏ (75% - BỊ CHẶN)** |
| **AL01** | Hẻm 112 Kha Vạn Cân (Hẻm cụt A) | Hẻm | Có (Cụt) | **SEG02** | Xanh (<10%) | Vàng (Kế thừa từ SEG02 Cam) | **Đỏ (Kế thừa từ SEG02 Đỏ - BỊ CHẶN)** |
| **AL02** | Hẻm 45 Kha Vạn Cân (Hẻm cụt B) | Hẻm | Có (Cụt) | Không | Xanh (<10%) | Cam (52% - Tự ngập) | **Đỏ (70% - Tự ngập - BỊ CHẶN)** |
| **AL03** | Hẻm liên thông 78 (Đường vòng) | Hẻm | Không (Liên thông) | Không | Xanh (<10%) | Xanh (6%) | Cam (42%) |
| **AL04** | Hẻm 60 Kha Vạn Cân (Hẻm cụt D) | Hẻm | Có (Cụt) | Không | Xanh (<10%) | Xanh (3%) | Xanh (4%) |
| **SEG03..04, 07..29** | Các đoạn đường khác | Đường chính | Không | Không | Xanh (<10%) | Xanh (<10%) | Xanh (<10%) |

---

## 2. Kết quả Gợi ý Tuyến đường mẫu (Route Results)

| Điểm đi $\rightarrow$ Điểm đến | Kịch bản `none` | Kịch bản `moderate` | Kịch bản `heavy` | Giải thích quy tắc định tuyến |
|---|---|---|---|---|
| **P1 $\rightarrow$ J2** *(Đầu SEG01 $\rightarrow$ Ngã giao hẻm 78)* | `status: ok`<br/>Đi thẳng đường chính SEG01 & SEG02_1 (502 m, Xanh). | `status: detour`<br/>Đường chính SEG02_1 ở mức Cam. Đi vòng qua hẻm AL03 (Xanh). | `status: detour`<br/>Đường chính SEG02_1 bị BỊ CHẶN (Đỏ). Đi vòng qua hẻm AL03 (Cam, 1445 m). | **Phát hiện đường vòng tránh ngập:** Thuật toán tự động tìm tuyến vòng qua AL03 khi đường chính bị ngập nặng hoặc có rủi ro cao hơn. |
| **P1 $\rightarrow$ P2** *(Đầu SEG01 $\rightarrow$ Cuối SEG02)* | `status: ok`<br/>Đi thẳng qua SEG01 & SEG02 (1302 m, Xanh). | `status: ok` / `detour`<br/>Cảnh báo đoạn SEG02 mức Cam. | `status: unreachable`<br/>Không thể tới nơi. | **Bị chặn toàn bộ:** Đoạn SEG02 bị ngập nặng (Đỏ), mọi tuyến đường tới P2 đều bắt buộc phải qua SEG02. App trả về `unreachable` và khuyên hoãn đi. |
| **P1 $\rightarrow$ H1** *(Đầu SEG01 $\rightarrow$ Cuối Hẻm cụt A)* | `status: ok`<br/>Thông suốt tới H1. | `status: warning`<br/>Hẻm cụt AL01 ngập mức Vàng. | `status: unreachable`<br/>Hẻm cụt AL01 ngập Đỏ (Bị chặn). | **Cảnh báo hẻm cụt:** Hẻm cụt AL01 bị ngập tràn từ đường chính SEG02. Không có đường thoát khác khi vào hẻm cụt này. |
| **P1 $\rightarrow$ H4** *(Đầu SEG01 $\rightarrow$ Cuối Hẻm cụt D)* | `status: ok`<br/>Thông suốt tới H4. | `status: ok`<br/>Thông suốt tới H4. | `status: ok` / `warning`<br/>Hẻm AL04 luôn Xanh. | **Hẻm đối chứng (AL04):** Luôn an toàn ở mọi kịch bản do vị trí địa hình cao. |
