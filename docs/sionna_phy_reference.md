# Sionna 2.0 PHY — Bản đồ API đầy đủ (cho đồ án AMC)

> Crawl toàn bộ `https://nvlabs.github.io/sionna/phy/` (2026-06-20): ~287 trang lá + 21 tutorial.
> Bản **2.0.1**, nền **PyTorch** (mọi thứ là `torch.Tensor`). Đánh dấu **[AMC]** = liên quan trực tiếp link adaptation.

---

## 0) QUICK MAP — dùng gì cho từng pha đồ án

**Mẫu kiến trúc then chốt (xương sống của mọi experiment):**
```
mc_fun(batch_size, ebno_db) -> (b, b_hat)      # hợp đồng chung
   ├── SingleLinkChannel  (subclass) ──► chính là một mc_fun
   ├── sim_ber(mc_fun, ebno_dbs, batch_size, max_mc_iter, ...) -> (ber, bler)
   └── PlotBER().simulate(mc_fun, ...) / .add(...)   # vẽ + so sánh đường cong
```
- **Block 02 Kênh:** `sionna.phy.channel.AWGN(x, no)`; `TDL`/`FlatFadingChannel` (+Doppler qua `min_speed/max_speed`); `ebnodb2no(ebno_db, num_bits_per_symbol, coderate)`. ZF: dùng `sionna.phy.mimo.zf_equalizer` (chạy được SISO, K=1) — **khỏi tự code**.
- **Block 03 Demapper+BER:** `Demapper(demapping_method, hard_out=False)` (LLR mềm) / `hard_out=True`; `compute_ber`, `hard_decisions`.
- **Block 04 Đường cong:** `sim_ber` + `PlotBER` (Monte-Carlo có sẵn — **khỏi tự viết vòng lặp**).
- **Lớp AMC:** *action* = **MCS index** → `decode_mcs_index(mcs_index, table_index∈{1,2,3,4}) -> (modulation_order, target_coderate)`; *metric* = `compute_bler`; *tín hiệu ACK/NACK* = `tb_crc_status` từ `TBDecoder`/`PUSCHReceiver`; *kênh* = `TDL` + quét tốc độ.
- **Runner device-agnostic + tái lập:** `sionna.phy.config.seed / .precision / .device`; tự viết khối bằng cách subclass `Block` (build()+call(), là `torch.nn.Module`).

**Gotchas quan trọng (đã kiểm chứng):**
- `Constellation` ở 2.0 **KHÔNG còn arg `trainable`** (bản cũ có). Muốn chòm sao học được → bọc `points` bằng `torch.nn.Parameter` thủ công (xem tutorial Autoencoder).
- `RayleighBlockFading` = **block fading i.i.d.** (hằng trong 1 block, độc lập giữa các block) → không có Doppler/tương quan thời gian. Cho AMC dùng **`TDL`/`CDL`** (time-correlated, "channel aging").
- `ebnodb2no`: `N0 = (10^(ebno/10) · coderate · num_bits_per_symbol)^-1` với Es=1.
- LDPC5G/Polar5G: **có rate-matching + HARQ** (rv 0–3) → đúng cho code-rate adaptation. `LDPCBPDecoder` generic thì KHÔNG rate-matched.

---

## 1) Channel — `sionna.phy.channel`

| Symbol | Args chính | Mục đích | AMC |
|---|---|---|---|
| `AWGN` | `()`; call `(x, no)` | Cộng nhiễu phức, phương sai `no` | **[AMC]** núm SNR |
| `TDL` | `(model, delay_spread, carrier_frequency, num_sinusoids=20, min_speed=0., max_speed=None, num_rx_ant=1, num_tx_ant=1)` | Tapped-delay-line (sum-of-sinusoids), **time-correlated** | **[AMC]** `min/max_speed`→Doppler; channel aging |
| `CDL` | `(model, delay_spread, carrier_frequency, ut_array, bs_array, direction='downlink', ut_velocity=None, min_speed=0., max_speed=0.)` | Clustered-delay-line, geometry/array | **[AMC]** Doppler qua speed; time dim |
| `UMi/UMa/RMa` | `(carrier_frequency, ut_array, bs_array, direction, ...)` | Mô hình hệ thống 3GPP (đô thị/nông thôn) | [AMC] mobility qua `set_topology(ut_velocities=...)` |
| `FlatFadingChannel` | `(num_tx_ant, num_rx_ant, spatial_corr=None, return_channel=False)`; `(x,no)` | Flat fading + AWGN | **[AMC]** SNR/H flat; i.i.d. nếu không corr |
| `GenerateFlatFadingChannel` / `ApplyFlatFadingChannel` | gen `(batch_size)` / apply `(x,h,no)` | Tách bước sinh/áp H | [AMC] gen H |
| `RayleighBlockFading` | `(num_rx, num_rx_ant, num_tx, num_tx_ant)`; `(batch, num_time_steps, fs)` | Rayleigh 1-tap **block-fading i.i.d.** | **[AMC]** baseline (bẫy i.i.d.) |
| `OFDMChannel`/`GenerateOFDMChannel`/`ApplyOFDMChannel`/`cir_to_ofdm_channel` | `(channel_model, resource_grid, ...)` | Kênh miền tần số (1 tap/subcarrier) | [AMC-OFDM] per-subcarrier H |
| `TimeChannel` + Generate/Apply + `cir_to_time_channel`, `time_to_ofdm_channel` | `(channel_model, bandwidth, num_time_samples, ...)` | Kênh đa tap miền thời gian (chọn lọc tần số) | [later] wideband |
| `PanelArray/Antenna/AntennaArray` | hình học anten TR38901 | — | N |
| Channel utils | `subcarrier_frequencies, time_lag_discrete_time_channel, deg_2_rad, rad_2_deg, wrap_angle_0_360, drop_uts_in_sector, relocate_uts, set_3gpp_scenario_parameters, gen_single_sector_topology[_interferers], exp_corr_mat, one_ring_corr_mat` | helper topology/correlation | `gen_..._interferers`→SINR [AMC] |
| Optical: `SSFM, EDFA, time_frequency_vector` | sợi quang | — | N (không phải vô tuyến) |
| Discrete: `BinarySymmetricChannel(BSC), BinaryErasureChannel(BEC), BinaryZChannel, BinaryMemorylessChannel` | `(return_llrs, bipolar_input, llr_max)`; `(x, pb)` | kênh bit-level | N |

`CIRDataset(cir_generator, batch_size, num_rx, num_rx_ant, num_tx, num_tx_ant, num_paths, num_time_steps)` — bọc CIR đo/RT làm `ChannelModel` (xem tutorial CIR Dataset / RT). `ChannelModel` = base trừu tượng trả `(a, tau)`.

---

## 2) Mapping — `sionna.phy.mapping`

| Symbol | Args chính | Mục đích | AMC |
|---|---|---|---|
| `Constellation` | `(constellation_type, num_bits_per_symbol, points=None, normalize=False, center=False)` | Chòm sao (qam/pam/custom). **KHÔNG có `trainable` ở 2.0** | **[AMC]** |
| `Mapper` | `(constellation_type=None, num_bits_per_symbol=None, constellation=None, return_indices=False)` | bit→symbol | **[AMC]** |
| `Demapper` | `(demapping_method∈{app,maxlog}, ..., constellation=None, hard_out=False)` | symbol→LLR (mềm) / hard | **[AMC]** |
| `SymbolDemapper` | `(..., hard_out=False)` | symbol→logits/hard symbol | [AMC] |
| `BinarySource` | `()` | bit ngẫu nhiên 0/1 | **[AMC]** |
| `SymbolSource`/`QAMSource`/`PAMSource` | `(constellation_type, num_bits_per_symbol, return_indices, return_bits)` | nguồn symbol gộp | [AMC] |
| `qam`/`pam` | `(num_bits_per_symbol, normalize=True)` | dựng mảng điểm | [AMC] |
| `LLRs2SymbolLogits, SymbolLogits2LLRs, SymbolLogits2Moments, SymbolInds2Bits, PAM2QAM, QAM2PAM, pam_gray` | chuyển đổi soft-info | — | N (cho iterative/LDPC) |

`Demapper`: mặc định LLR mềm (`hard_out=False`); `app` (chính xác) vs `maxlog` (xấp xỉ).

---

## 3) Signal — `sionna.phy.signal`  (cái "đường ống" TX)

| Symbol | Args chính | Mục đích | SC |
|---|---|---|---|
| `RootRaisedCosineFilter` | `(span_in_symbols, samples_per_symbol, beta, window=None, normalize=True)` | RRC (matched TX/RX), `beta`=roll-off | **[SC]** |
| `RaisedCosineFilter` | `(span_in_symbols, samples_per_symbol, beta, ...)` | RC pulse shaping | [SC] |
| `SincFilter`/`CustomFilter`/`Filter` | filter cơ bản | — | [SC] |
| `Upsampling`/`Downsampling` | `(samples_per_symbol, axis=-1)` | chèn/bỏ mẫu (TX/RX) | **[SC]** |
| `convolve` | `(inp, ker, padding, axis)` | tích chập (matched filter) | [SC] |
| `empirical_psd`/`empirical_aclr` | đo phổ/rò băng | chẩn đoán | [SC] |
| `fft`/`ifft` | DFT chuẩn hoá | (OFDM) | N |
| Windows: `Hann/Hamming/Blackman/Custom` | cửa sổ | thiết kế filter | N |

---

## 4) FEC — `sionna.phy.fec`  (mã hoá kênh — pha code-rate adaptation)

- **LDPC:** `LDPC5GEncoder(k, n, num_bits_per_symbol=None, bg=None)` (+`rv` 0–3) — **5G, rate-matching tích hợp** **[AMC]**; `LDPC5GDecoder(encoder, cn_update='boxplus-phi', num_iter=20, return_infobits=True, harq_mode=False)` — tự gỡ rate-match + HARQ soft-combine **[AMC]**; `LDPCBPDecoder(pcm, ...)` generic (KHÔNG 5G rate-match); node updates: `vn_update_sum, cn_update_{minsum,offset_minsum,phi,tanh}`; callbacks: `DecoderStatistics/EXIT/WeightedBP`.
- **Polar:** `Polar5GEncoder(k, n, channel_type='uplink')` + `Polar5GDecoder(enc, dec_type='SC', list_size=8)` (rate-match+CRC) **[AMC]**; generic `PolarEncoder/PolarSCDecoder/PolarSCLDecoder/PolarBPDecoder`; utils `generate_5g_ranking, generate_polar_transform_mat, generate_rm_code, generate_dense_polar`.
- **Convolutional:** `ConvEncoder(gen_poly, rate=0.5, constraint_length=3, rsc, terminate)`, `ViterbiDecoder`, `BCJRDecoder`; utils `polynomial_selector, Trellis`. (fixed-rate)
- **Turbo:** `TurboEncoder(rate=1/3, interleaver_type='3GPP')`, `TurboDecoder(num_iter=6)`; `puncture_pattern` (đạt rate đích) **[AMC]**.
- **CRC:** `CRCEncoder(crc_degree, k)`, `CRCDecoder` (→ ACK/NACK).
- **Interleaving:** `RowColumn/Random/Turbo3GPP Interleaver`, `Deinterleaver`. **Scrambling:** `Scrambler/Descrambler/TB5GScrambler`.
- **Utils:** `load_parity_check_examples, alist2mat, load_alist, generate_reg_ldpc, make_systematic, gm2pcm, pcm2gm, verify_gm_pcm`; EXIT: `plot_exit_chart, get_exit_analytic, plot_trajectory`; `GaussianPriorSource` (LLR giả lập all-zero), `bin2int/int2bin/int_mod_2/llr2mi/j_fun/j_fun_inv`.

---

## 5) Utils — `sionna.phy.utils`  (xương sống experiment)

**Metrics:** `compute_ber(b,b_hat)`, **`compute_bler(b,b_hat)`** (block = last dim, lỗi nếu ≥1 bit khác) **[AMC]**, `compute_ser`, `count_block_errors`, `count_errors`, `hard_decisions(llr)`.
**SNR:** **`ebnodb2no(ebno_db, num_bits_per_symbol, coderate, resource_grid=None)`** → `N0=(10^(ebno/10)·r·M)^-1` (Es=1). `db_to_lin/lin_to_db/dbm_to_watt/watt_to_dbm`.
**Monte-Carlo (block 04):**
- **`sim_ber(mc_fun, ebno_dbs, batch_size, max_mc_iter, soft_estimates=False, num_target_bit_errors=None, num_target_block_errors=None, target_ber=None, target_bler=None, early_stop=True, callback=None) -> (ber, bler)`**. `mc_fun(batch_size, ebno_db) -> (b, b_hat)`. Dừng sớm mỗi điểm SNR khi đạt số lỗi mục tiêu; `callback` trả CONTINUE/NEXT_SNR/STOP.
- **`PlotBER(title)`**: `.add(ebno_db, ber, is_bler, legend)` (đường tham chiếu/lý thuyết), `.simulate(mc_fun, ebno_dbs, batch_size, max_mc_iter, add_bler=False, ...)` (bọc `sim_ber` + lưu + vẽ), `.reset()/.remove()/__call__()`. `plot_ber(snr_db, ber, ...)` vẽ rời.
- **`SingleLinkChannel(num_bits_per_symbol, num_info_bits, target_coderate)`** — **link single-carrier/single-stream trừu tượng**, call `(batch_size, ebno_db)->(bits,bits_hat)` = đúng hợp đồng `mc_fun` → cắm thẳng vào `sim_ber`. **Khớp pha 1.**
- **`MCSDecoder`** (abstract, không chứa bảng) — call `(mcs_index, mcs_table_index, mcs_category, check_index_validity) -> (modulation_order, coderate)`; bảng thật nằm ở `MCSDecoderNR` (mục 6). `TransportBlock` segment TB→code blocks.
**Random (seeded):** `randint, rand, uniform, normal` (qua `config` RNG). **Linalg:** `inv_cholesky, matrix_pinv`. **Numerics:** `bisection_method, expand_bound`. **Tensors:** `expand_to_rank, flatten_dims, flatten_last_dims, insert_dims, split_dim, gather_from_batched_indices, ...` (helper shape).

---

## 6) 5G NR — `sionna.phy.nr`  (cốt lõi AMC chuẩn 3GPP)

**MCS (action space của AMC):**
- **`decode_mcs_index(mcs_index, table_index=1, is_pusch=True, transform_precoding=False, pi2bpsk=False) -> (modulation_order, target_coderate)`** — bảng TS 38.214. `modulation_order`=bit/symbol (2=QPSK,4=16QAM,6=64QAM,8=256QAM…), coderate∈(0,1).
- **`table_index ∈ {1,2,3,4}`, mcs_index 0–28**: T1=tới 64-QAM, T2=tới 256-QAM, T3=low-SE/64-QAM (coverage), T4=1024-QAM.
- `MCSDecoderNR` — Block bọc `decode_mcs_index` (batched, tensor), `mcs_category` 0=PUSCH/1=PDSCH.
- **`TBConfig(mcs_index, mcs_table, channel_type∈{PUSCH,PDSCH})`** → read-only `target_coderate`, `num_bits_per_symbol` (suy từ MCS). **Đây là nơi đặt MCS.**

**Throughput chain:** `decode_mcs_index` → `calculate_num_coded_bits(mod, num_prbs, num_ofdm_symbols, num_dmrs_per_prb, num_layers)` = G → `calculate_tb_size(mod, coderate, num_coded_bits=G, ...)` = `tb_size` (payload bits) = throughput AMC.

**End-to-end:** `PUSCHTransmitter(pusch_configs)` / `PUSCHReceiver(... return_tb_crc_status=...)` — **`tb_crc_status` = ACK/NACK cho vòng AMC ngoài** **[AMC]**. `TBEncoder/TBDecoder` (CRC+LDPC+rate-match+scramble); `TBDecoder` trả `(b_hat, tb_crc_status)`. `CodedAWGNChannelNR(num_bits_per_symbol, num_info_bits, target_coderate)` — sim coded-AWGN nhanh BLER-vs-SNR mỗi MCS **[AMC]**. `CarrierConfig, LayerMapper/Demapper, PUSCHConfig/DMRS/PilotPattern/Precoder/LSChannelEstimator`, `generate_prng_seq`.

---

## 7) MIMO — `sionna.phy.mimo`  (phần lớn ngoài scope; equalizer tái dùng SISO)

- **Equalization [tái dùng SISO]:** **`zf_equalizer(y, h, s) -> (x_hat, no_eff)`** (K=1 = single-antenna chuẩn), **`lmmse_equalizer(y, h, s, whiten_interference=True)`**, `mf_equalizer`, `lmmse_matrix`.
- Detection: `LinearDetector(equalizer, output, demapping_method, ...)`, `MaximumLikelihoodDetector` (num_streams=1→demapper), `KBestDetector/EPDetector/MMSEPICDetector` (đa anten).
- Precoding/StreamManagement: MIMO-specific (ngoài scope). Utils: `complex2real_*`, `whiten_channel` (dimension-agnostic).

---

## 8) OFDM — `sionna.phy.ofdm`  (pha sau)

- `ResourceGrid(num_ofdm_symbols, fft_size, subcarrier_spacing, ...)` **[AMC-OFDM]** cấu trúc per-subcarrier; `ResourceGridMapper/Demapper`, `RemoveNulledSubcarriers`.
- `OFDMModulator(cyclic_prefix_length)` / `OFDMDemodulator(fft_size, l_min, cp)`.
- Pilot: `PilotPattern, EmptyPilotPattern, KroneckerPilotPattern`.
- Channel est: `LSChannelEstimator`, interpolators (`NearestNeighbor/Linear/LMMSE1D/LMMSE`), `SpatialChannelFilter`; **`tdl_time_cov_mat(model, speed, carrier_frequency, ofdm_symbol_duration, num_ofdm_symbols)`**, **`tdl_freq_cov_mat(...)`** **[AMC]** (hiệp phương sai cho LMMSE/dự đoán).
- Equalization: `LMMSEEqualizer/ZFEqualizer/MFEqualizer/OFDMEqualizer`; **`PostEqualizationSINR` / `LMMSEPostEqualizationSINR`** → SINR per [symbol, subcarrier, stream] = **đầu vào CQI/MCS** **[AMC]**.
- Detection: `OFDMDetector(WithPrior)`, `LinearDetector`, `MaximumLikelihoodDetector(WithPrior)`, `KBest/EP/MMSEPIC`.
- Precoding: `RZFPrecoder`, `*PrecodedChannel`.

---

## 9) Framework plumbing (cho experiment runner)

- **`Block`** (`sionna.phy.block.Block`, subclass của `Object` < `torch.nn.Module`): implement **`call(...)`** (tính toán) + tuỳ chọn **`build(*shapes)`** (init lười theo shape, chạy 1 lần). `forward()` có sẵn gọi `call()`. Input tensor tự cast theo precision. Trainable = `torch.nn.Parameter` (thường trong `build()`).
- **`config`** (`sionna.phy.config`): `config.precision='single'/'double'`, `config.device='cuda:0'/'cpu'` (`config.available_devices`), `config.seed=42` (seed mọi RNG). RNG: `config.np_rng`, `config.py_rng`, `config.torch_rng()`. → **đặt seed/precision/device 1 chỗ = runner device-agnostic + tái lập.**
- **Số học compile-safe:** tránh nghịch đảo tường minh — `torch.linalg.solve`, Cholesky (`cholesky_ex` + `solve_triangular`).

---

## 10) Tutorials (relevance cho AMC)

**Beginners (8):** Hello World [⭐ block01+02] · Part1 Getting Started [⭐⭐ link+coding+PlotBER] · Part2 Differentiable [⭐ ML] · Part3 Advanced Link-level [OFDM/CDL/LDPC/MonteCarlo, pha sau] · Part4 Learned Receivers [ML] · Basic MIMO [later] · **Pulse-shaping Basics** [⭐ RRC] · Optical [bỏ].

**Experts (13) — ưu tiên cho AMC:**
- **High:** #1 5G Coding Polar vs LDPC (HARQ, rate) · #3 **BICM** (joint mod+code = đúng cái AMC chọn) · #9 **Autoencoder** (học chòm sao + demapper, pha ML) · #12 **CIR Dataset** (kênh từ data → replay đo/RT để train/eval AMC).
- **Med:** #2 5G NR PUSCH (MCS/TB chuẩn, OFDM) · #4 MIMO-OFDM/CDL · #5 Neural Receiver · #7 OFDM MIMO Detection · #8 Iterative Detection&Decoding · #13 Link-level với RT (SNR theo không gian — testbed AMC).
- **Low:** #6 Realistic MU-MIMO · #10 Weighted BP · #11 Superimposed Pilots.
