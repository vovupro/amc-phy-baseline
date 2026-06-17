# AMC PHY Baseline

Nền tảng cho đồ án **AI-Assisted Modulation/Coding Adaptation (AMC)**.

Giai đoạn 1: xây dựng và **hiểu** một PHY link single-carrier bằng Python + Sionna
(BPSK/QPSK/16-QAM, kênh AWGN + Rayleigh phẳng, perfect CSI). Chưa có LDPC, chưa có
OFDM, chưa có ML — những khối đó sẽ thêm ở các giai đoạn sau.

## Cấu trúc

```
amc-phy-baseline/
├── diagrams/                  # bộ công cụ vẽ sơ đồ hệ thống (Graphviz)
│   ├── draw_system_diagram.py # script sinh sơ đồ (sửa nội dung ở mục DIAGRAMS)
│   ├── amc_system_overview.svg
│   ├── phy_link_flow.svg
│   └── channel_and_snr_detail.svg
└── src/                       # code PHY link (đang phát triển)
```

## Sơ đồ

Sinh lại sơ đồ:

```bash
cd diagrams
python draw_system_diagram.py              # dựng tất cả
python draw_system_diagram.py phy_link_flow # chỉ dựng một sơ đồ
```

Yêu cầu: Graphviz (`dot`) + `pip install graphviz`. Mở file `.svg` bằng trình duyệt.

## Trạng thái

- [x] Sơ đồ kiến trúc hệ thống + chi tiết kênh/SNR
- [ ] Code PHY link (nguồn bit → mapper → kênh → equalizer → demapper → BER)
- [ ] Đường cong BER vs SNR (mô phỏng + lý thuyết)
- [ ] Lớp quyết định AMC (oracle, ML, online) — giai đoạn sau
