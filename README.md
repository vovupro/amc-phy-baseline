# AMC PHY Baseline

Nền tảng cho đồ án **AI-Assisted Modulation/Coding Adaptation (AMC)**.

Giai đoạn 1: xây dựng và **hiểu** một PHY link single-carrier bằng Python + Sionna
(BPSK/QPSK/16-QAM, kênh AWGN + Rayleigh phẳng, perfect CSI). Chưa có LDPC, chưa có
OFDM, chưa có ML — những khối đó sẽ thêm ở các giai đoạn sau.

## Cấu trúc

```
amc-phy-baseline/
├── diagrams/                  # bộ công cụ vẽ sơ đồ hệ thống (D2)
│   ├── _theme.d2              # bảng màu & lớp style DÙNG CHUNG (sửa 1 chỗ, áp tất cả)
│   ├── build.py              # render *.d2 -> *.svg
│   ├── amc_system_overview.d2 / .svg
│   ├── phy_link_flow.d2 / .svg
│   └── channel_and_snr_detail.d2 / .svg
└── src/                       # code PHY link (đang phát triển)
```

## Sơ đồ

Mỗi sơ đồ là một file `.d2` (sửa trực tiếp); style/màu dùng chung ở `_theme.d2`.
Dựng lại:

```bash
cd diagrams
python build.py                     # dựng tất cả
python build.py phy_link_flow       # chỉ dựng một sơ đồ
```

Yêu cầu: [D2](https://d2lang.com) (`winget install Terrastruct.D2`). Mở `.svg` bằng trình duyệt.

### Thêm sơ đồ mới

1. Tạo `diagrams/<tên>.d2` (KHÔNG bắt đầu bằng `_` — file `_*.d2` chỉ để import).
2. Dòng đầu: `...@_theme` rồi `direction: down`.
3. Tô màu khối bằng `class:` (đừng hard-code `fill`). Danh sách class có sẵn xem ở
   đầu `_theme.d2`: vai trò `tx/ch/rx/util/note/off/on/warn`, khung `g-offline/g-online`,
   cạnh `e-offline/e-online/e-side/e-csi`.
4. Nhãn nhiều dòng: dùng block `` |`md ... `| `` và mỗi ý một bullet `- ...`.
5. `python build.py <tên>`.

> Lưu ý D2: node nhãn markdown chỉ nhận **màu nền** (fill), **bỏ viền** (stroke) —
> nhấn mạnh bằng fill, không bằng viền (chi tiết ở `_theme.d2`).

## Trạng thái

- [x] Sơ đồ kiến trúc hệ thống + chi tiết kênh/SNR
- [ ] Code PHY link (nguồn bit → mapper → kênh → equalizer → demapper → BER)
- [ ] Đường cong BER vs SNR (mô phỏng + lý thuyết)
- [ ] Lớp quyết định AMC (oracle, ML, online) — giai đoạn sau
