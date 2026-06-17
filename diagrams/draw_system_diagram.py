"""
draw_system_diagram.py
======================================================================
Bộ công cụ vẽ sơ đồ (Graphviz) cho đồ án AMC — thiết kế để DÙNG LÂU DÀI.

File chia 2 tầng rõ rệt:
  • ENGINE  (phần "máy")  — thư viện dựng nhãn/cạnh, ÍT KHI cần sửa.
  • DIAGRAMS (phần nội dung) — mỗi sơ đồ là một hàm khai báo gọn, SỬA Ở ĐÂY.

----------------------------------------------------------------------
CHẠY
  python draw_system_diagram.py                 # dựng TẤT CẢ sơ đồ
  python draw_system_diagram.py phy_link_flow   # chỉ dựng 1 sơ đồ (nhanh)
  python draw_system_diagram.py a b             # dựng vài sơ đồ

Mỗi sơ đồ xuất các định dạng trong FORMATS (mặc định: chỉ .svg) + .dot nguồn.

----------------------------------------------------------------------
THÊM / SỬA SƠ ĐỒ (xem ví dụ ở mục DIAGRAMS bên dưới)
  • Một KHỐI:   d.block("id", "Tiêu đề", "dòng phụ", ["dòng 1", "dòng 2"], role="tx")
                ("dòng phụ" = tên class Sionna/mô tả; HIỆN/ẨN bằng cờ SHOW_SUB)
  • Một CẠNH:   d.edge("a", "b", "nhãn", kind="data")
  • Hàng ngang: with d.same() as row:  row.block(...);  row.block(...)
  • Cụm khung:  with d.cluster("Nhãn cụm", "#7a5cc0") as c:  c.block(...)
  • Khối "giai đoạn sau" (viền xám đứt): thêm planned=True vào block(...)
  • Thêm sơ đồ mới: viết hàm build_xxx() trả về Diagram, rồi đăng ký vào DIAGRAMS.

QUY TẮC AN TOÀN (để KHÔNG bị lỗi render)
  • Nội dung khối truyền dạng LIST từng dòng (đừng nhét <BR/> trong một chuỗi).
  • Ký tự '&' tự được escape -> cứ gõ "A & B" bình thường.
  • TRÁNH gõ '<' hoặc '>' literal trong text; dùng glyph: ≤ ≥ → (không dùng < > -->).
  • Công thức dùng helper: SUB("2"), SUP("2"), I("nghiêng"), B("đậm"), MONO("code").
  • Glyph an toàn đã kiểm chứng: → × · ≤ ≥ ² √ ≠ η π  (TRÁNH ∈, ⇒ — font thiếu).
======================================================================
"""

import os
import re
import sys
import subprocess
from contextlib import contextmanager

# ╔══════════════════════════════════════════════════════════════════╗
# ║ CONFIG — chỉnh nhanh ở đây                                         ║
# ╚══════════════════════════════════════════════════════════════════╝
FONT = "Arial"          # font đủ dấu tiếng Việt (Segoe UI / Tahoma cũng được)
FORMATS = ["svg"]       # định dạng xuất: thêm "pdf" (luận văn) / "png" (preview)
DPI = "300"             # độ phân giải PNG (svg/pdf là vector nên không phụ thuộc)
SHOW_SUB = False        # hiện dòng phụ (tên class Sionna / mô tả) dưới tiêu đề?
                        #   False = ẩn (gọn); True = hiện lại. Dữ liệu vẫn giữ trong source.

# Bảng màu nền khối theo VAI TRÒ (role) — đổi 1 chỗ, áp toàn bộ sơ đồ.
ROLES = {
    "tx":   "#cfe8ff",  # xanh : phía phát (TX)
    "ch":   "#ffd6d6",  # đỏ   : kênh truyền
    "rx":   "#d8f5d0",  # lá   : phía thu (RX)
    "util": "#fff3c4",  # vàng : đo lường / đánh giá
    "note": "#eef5ff",  # xanh nhạt : định nghĩa / ghi chú
    "off":  "#e7e0ff",  # tím  : khối OFFLINE (oracle + huấn luyện ML)
    "on":   "#ffe3c2",  # cam  : khối ONLINE (quyết định runtime)
}

# Kiểu CẠNH theo LOẠI (kind) — gom style/màu vào một nơi.
KINDS = {
    "data":    dict(color="#333333"),                          # luồng dữ liệu chính
    "offline": dict(color="#7a5cc0", style="dashed"),          # tiêu chí / duyệt offline
    "online":  dict(color="#d08a2c", style="dashed"),          # vòng quyết định online
    "input":   dict(color="#b03030", style="dashed", arrowhead="vee"),  # đầu vào phụ (no)
    "csi":     dict(color="#3a7d34", style="dashed", arrowhead="vee"),  # CSI -> equalizer
    "invis":   dict(style="invis"),                            # chỉ để ép layout
}

# Graphviz cài qua winget -> thêm vào PATH để tìm dot.exe dù PATH chưa refresh.
_GVBIN = r"C:\Program Files\Graphviz\bin"
if os.path.isdir(_GVBIN):
    os.environ["PATH"] = _GVBIN + os.pathsep + os.environ["PATH"]
_DOT = os.path.join(_GVBIN, "dot.exe") if os.path.isdir(_GVBIN) else "dot"

import graphviz


# ╔══════════════════════════════════════════════════════════════════╗
# ║ ENGINE — phần "máy", ÍT KHI cần sửa                                ║
# ╚══════════════════════════════════════════════════════════════════╝

# --- escape & các helper inline cho text trong nhãn HTML ---
_AMP = re.compile(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9A-Fa-f]+);)")


def esc(s):
    """Escape ký tự '&' lạc (không escape các entity đã đúng). Giữ nguyên
    các thẻ <...> để helper SUB/I/MONO vẫn hoạt động."""
    return _AMP.sub("&amp;", str(s))


def B(s):    return f"<B>{s}</B>"                       # đậm
def I(s):    return f"<I>{s}</I>"                       # nghiêng
def SUB(s):  return f"<SUB>{s}</SUB>"                   # chỉ số dưới
def SUP(s):  return f"<SUP>{s}</SUP>"                   # chỉ số trên


def MONO(s, size="9.5", color=None):
    """Đoạn chữ monospace (Consolas) — dùng cho tên hàm / code."""
    c = f' COLOR="{color}"' if color else ""
    return f'<FONT FACE="Consolas" POINT-SIZE="{size}"{c}>{s}</FONT>'


def _slug(s):
    return re.sub(r"[^0-9A-Za-z]+", "_", s).strip("_").lower()[:40] or "c"


def _label(title, sub, body):
    """Nhãn khối chuẩn: tiêu đề (giữa, đậm) + dòng phụ mono xám + đệm +
    từng dòng nội dung (trái, có padding -> thoáng, không dồn sát)."""
    rows = ""
    show_sub = bool(sub) and SHOW_SUB          # dòng phụ chỉ hiện khi SHOW_SUB=True
    if title:
        rows += (f'<TR><TD ALIGN="CENTER"><FONT POINT-SIZE="11.5">{B(esc(title))}'
                 f'</FONT></TD></TR>')
    if show_sub:
        rows += (f'<TR><TD ALIGN="CENTER"><FONT FACE="Consolas" POINT-SIZE="8.5" '
                 f'COLOR="#777777">{esc(sub)}</FONT></TD></TR>')
    # Hàng đệm CHỈ khi thật sự có dòng phụ (để tách nó với nội dung).
    # Khi không có dòng phụ -> tiêu đề nằm sát nội dung, không hở khoảng thừa.
    if show_sub and body:
        rows += '<TR><TD HEIGHT="8"> </TD></TR>'
    for line in body:
        rows += (f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="10">{esc(line)}'
                 f'</FONT></TD></TR>')
    return ('<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">'
            + rows + '</TABLE>>')


def _kv_label(title, rows, code=None):
    """Nhãn bảng 2 cột căn lề (đại lượng | biểu thức). rows: list các tuple
    (lhs, rhs); phần tử None = hàng đệm. code: dòng monospace ở chân (tuỳ chọn)."""
    out = '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">'
    if title:
        out += (f'<TR><TD COLSPAN="2" ALIGN="CENTER"><FONT POINT-SIZE="12">'
                f'{B(esc(title))}</FONT></TD></TR>'
                '<TR><TD COLSPAN="2" HEIGHT="6"> </TD></TR>')
    for row in rows:
        if row is None:
            out += '<TR><TD COLSPAN="2" HEIGHT="6"> </TD></TR>'
            continue
        lhs, rhs = row
        out += (f'<TR><TD ALIGN="RIGHT"><FONT POINT-SIZE="10.5">{esc(lhs)}</FONT></TD>'
                f'<TD ALIGN="LEFT"><FONT POINT-SIZE="10.5">  {esc(rhs)}</FONT></TD></TR>')
    if code:
        out += ('<TR><TD COLSPAN="2" HEIGHT="6"> </TD></TR>'
                f'<TR><TD COLSPAN="2" ALIGN="CENTER">{MONO(esc(code), color="#1a4f8a")}'
                f'</TD></TR>')
    return out + '</TABLE>>'


class Scope:
    """Bọc một graph/subgraph Graphviz + các phương thức khai báo gọn.
    Dùng chung cho cả sơ đồ gốc, hàng rank=same, và cụm cluster."""

    def __init__(self, g):
        self.g = g

    def block(self, nid, title, sub="", body=(), role="note", planned=False, **attrs):
        """Một khối chữ nhật bo góc. role -> màu nền (xem ROLES).
        planned=True -> viền xám đứt (khối 'giai đoạn sau')."""
        style = "rounded,filled,dashed" if planned else "rounded,filled"
        if planned:
            attrs.setdefault("color", "#888888")
        self.g.node(nid, label=_label(title, sub, body),
                    fillcolor=ROLES.get(role, ROLES["note"]), style=style, **attrs)
        return nid

    def note(self, nid, title="", body=(), color="#b03030", fill="#fff0f0", **attrs):
        """Khối ghi chú dạng 'note' (góc gập), nhấn mạnh bằng màu viền."""
        self.g.node(nid, label=_label(title, "", body), shape="note", style="filled",
                    fillcolor=fill, color=color, fontcolor=color, **attrs)
        return nid

    def kv(self, nid, title, rows, code=None, fill=ROLES["note"], color="#1a4f8a", **attrs):
        """Khối bảng 2 cột căn lề (xem _kv_label)."""
        self.g.node(nid, label=_kv_label(title, rows, code), fillcolor=fill,
                    color=color, **attrs)
        return nid

    def edge(self, a, b, label="", kind="data", **attrs):
        """Một cạnh. kind -> style/màu (xem KINDS). attrs ghi đè được."""
        opts = dict(KINDS.get(kind, {}))
        opts.update(attrs)
        self.g.edge(a, b, label=label, **opts)

    @contextmanager
    def same(self):
        """Nhóm các khối thành một hàng (rank=same)."""
        with self.g.subgraph() as sg:
            sg.attr(rank="same")
            yield Scope(sg)

    @contextmanager
    def cluster(self, label, color="#888888"):
        """Khung gom nhóm (subgraph cluster) có nhãn + màu viền đứt."""
        with self.g.subgraph(name="cluster_" + _slug(label)) as sg:
            sg.attr(label=label, color=color, fontcolor=color, fontname=FONT,
                    fontsize="12", style="rounded,dashed")
            yield Scope(sg)


class Diagram(Scope):
    """Sơ đồ gốc: tạo Digraph, đặt style mặc định + tiêu đề, và .render()."""

    def __init__(self, name, title="", subtitle="", rankdir="TB", fontsize="16", **gattrs):
        g = graphviz.Digraph(name)
        attrs = dict(rankdir=rankdir, bgcolor="white", fontname=FONT,
                     fontsize=fontsize, labelloc="t")
        if title:
            lab = "<" + B(esc(title))
            if subtitle:
                lab += f'<BR/><FONT POINT-SIZE="11" COLOR="#666666">{esc(subtitle)}</FONT>'
            attrs["label"] = lab + "<BR/> >"
        attrs.update(gattrs)
        g.attr(**attrs)
        g.attr("node", fontname=FONT, shape="box", style="rounded,filled", margin="0.22,0.16")
        g.attr("edge", fontname=FONT, fontsize="10", color="#333333", fontcolor="#1a4f8a")
        self.name = name
        super().__init__(g)

    def render(self):
        save(self.g, self.name)


def save(g, name):
    """Xuất sơ đồ ra các định dạng trong FORMATS + .dot (nguồn).
    Gọi thẳng dot.exe qua subprocess (KHÔNG dùng g.render()) để tránh lỗi
    graphviz-python trên Windows: nó decode stderr của dot bằng cp1252 và
    crash khi gặp byte ngoài cp1252."""
    g.attr(dpi=DPI)
    dotfile = name + ".dot"
    with open(dotfile, "w", encoding="utf-8") as f:
        f.write(g.source)
    for fmt in FORMATS:
        r = subprocess.run([_DOT, f"-T{fmt}", dotfile, "-o", f"{name}.{fmt}"],
                           capture_output=True)
        if r.stderr:
            safe = r.stderr.decode("utf-8", "replace").strip().encode("ascii", "replace").decode()
            if safe:
                print(f"  [dot {fmt} warn] {safe}")
        if r.returncode != 0:
            print(f"  [dot {fmt} FAILED rc={r.returncode}]")
    print(f"[OK] {name}: {', '.join(FORMATS)} + dot")


# ╔══════════════════════════════════════════════════════════════════╗
# ║ DIAGRAMS — phần NỘI DUNG, SỬA Ở ĐÂY                                ║
# ╚══════════════════════════════════════════════════════════════════╝

def build_amc_system():
    """Sơ đồ 1: toàn cảnh hệ thống AMC (bức tranh lớn)."""
    d = Diagram(
        "amc_system_overview",
        title="Toàn cảnh hệ thống AMC (Adaptive Modulation & Coding)",
        subtitle=("Khung viền XANH ĐẬM = đang xây trong project HIỆN TẠI (baseline PHY) · "
                  "viền XÁM ĐỨT = giai đoạn AMC sau"),
        fontsize="18", nodesep="0.55", ranksep="0.8")

    # --- Hàng định nghĩa bài toán: STATE | ACTION | OBJECTIVE ---
    with d.same() as row:
        row.block("state", "STATE  s  (trạng thái kênh + QoS)", "đo được + yêu cầu", [
            "• SNR profile đa subcarrier: mean/var/min/percentile",
            "• Doppler / coherence time",
            "• độ tin cậy CSI (var của SNR ước lượng)",
            "• QoS: target BLER (~10%), latency budget"], role="note")
        row.block("action", "ACTION  a  (chế độ truyền = MCS)", "không gian hành động", [
            "modulation {BPSK, QPSK, 16QAM}",
            "× code rate {1/2, 2/3, 3/4}",
            "× #iter decoder {5, 10, 20}",
            "→ bảng MCS thu gọn (~9 mode)"], role="note")
        row.block("obj", "OBJECTIVE  (hàm mục tiêu)", "tối ưu có ràng buộc", [
            "max throughput hiệu dụng:",
            "η = R_code × log" + SUB("2") + "(M) × (1 − BLER)",
            "ràng buộc: BLER ≤ target",
            "             runtime ≤ budget"], role="note")

    # --- Môi trường mô phỏng (viền xanh đậm = phần đang xây) ---
    d.block("phy", "PHY LINK SIMULATOR  (môi trường mô phỏng)", "xem chi tiết: phy_link_flow", [
        "Vào: (channel realization, action a)",
        "Ra : BER, BLER, throughput, runtime",
        I("Project hiện tại: bản single-carrier, perfect CSI,"),
        I("chưa LDPC/OFDM — sẽ nâng cấp ở giai đoạn sau")],
        role="rx", color="#1a7d1a", penwidth="3")

    # --- OFFLINE: oracle sinh nhãn -> dataset -> huấn luyện ML ---
    with d.cluster("OFFLINE — sinh nhãn & huấn luyện", "#7a5cc0") as off:
        off.block("oracle", "ORACLE / GENIE (vét cạn)", "bộ sinh nhãn (teacher)", [
            "Với mỗi state s: thử MỌI action a qua simulator,",
            "đo BLER tin cậy (Monte Carlo ≥ N lỗi),",
            "chọn a*(s) = argmax objective",
            "→ đây là LUT tối ưu / upper bound"], role="off", planned=True)
        off.block("data", "DATASET  {(s, a*)}", "nhãn huấn luyện", [
            "cặp trạng thái → hành động tối ưu"], role="off", planned=True)
        off.block("mltrain", "ML POLICY  π(s)", "DT / RandomForest / GBDT (sklearn)", [
            "học ánh xạ s → a*",
            "= bản NÉN & GENERALIZE của oracle",
            "(nhẹ, giải thích được)"], role="off", planned=True)

    # --- ONLINE: bộ quyết định runtime ---
    with d.cluster("ONLINE — vòng quyết định runtime", "#d08a2c") as on:
        on.block("ctrl", "BỘ QUYẾT ĐỊNH + HYSTERESIS", "chống dao động mode", [
            "s_t → π(s_t) → a_candidate",
            "Hysteresis: chỉ đổi mode khi vượt ngưỡng & giữ đủ lâu",
            "→ a_final (mode phát)"], role="on", planned=True)

    # --- Đánh giá & so sánh ---
    d.block("eval", "ĐÁNH GIÁ & SO SÁNH", "3 chính sách", [
        "Fixed-robust (BPSK 1/2) · Fixed-high-TP (16QAM 3/4) · AI-adaptive π",
        "Sản phẩm: BER vs SNR · Throughput vs SNR ·",
        "Runtime/complexity table · Policy map (SNR → mode)"], role="util", planned=True)

    # --- Cạnh: tất cả chảy XUÔI XUỐNG (acyclic) -> không đi chéo ---
    d.edge("action", "phy", "a")
    d.edge("phy", "oracle", "BER/BLER,\nthroughput,\nruntime")
    d.edge("obj", "oracle", "tiêu chí chọn", kind="offline")
    d.edge("state", "oracle", "duyệt theo s", kind="offline")
    d.edge("oracle", "data")
    d.edge("data", "mltrain")
    d.edge("mltrain", "ctrl", "π(s)")
    d.edge("state", "ctrl", "s_t đo online", kind="online")
    d.edge("ctrl", "eval", "AI-adaptive a*", color="#d08a2c")
    d.edge("phy", "eval", "đo 3 chính sách")
    return d


def build_phy_link():
    """Sơ đồ 2: baseline PHY link (dọc cho hẹp bề ngang)."""
    d = Diagram(
        "phy_link_flow",
        title="Baseline PHY Link (single-carrier)  —  luồng phát → thu",
        subtitle=("Cấu hình CỐ ĐỊNH: chưa channel coding · chưa OFDM/MIMO · "
                  "perfect CSI · chưa ML  (nền cho giai đoạn AMC)"),
        rankdir="TB", ranksep="0.5")

    d.block("src", "1. Nguồn bit", "sn.utils.BinarySource", [
        "Sinh bit ngẫu nhiên", "shape [batch, N], b = 0/1"], role="tx")
    d.block("map", "2. Mapper", "sn.mapping.Mapper", [
        "BPSK → pam,1   QPSK → qam,2", "16QAM → qam,4", "Gray code, chuẩn hoá Es=1"], role="tx")
    d.block("chan", "3. Kênh truyền", "AWGN  |  h~CN(0,1)", [
        "AWGN:     y = x + n", "Rayleigh: y = h·x + n", "n ~ CN(0, no)"], role="ch")
    d.block("eq", "4. Cân bằng kênh", "tự viết (ZF 1-tap)", [
        "x_hat = y / h", "perfect CSI (AWGN: h = 1)"], role="rx")
    d.block("demap", "5. Demapper", "sn.mapping.Demapper  hard_out=True", [
        "hard decision, khoảng cách min", "(tính LLR rồi threshold)"], role="rx")
    d.block("ber", "6. Đo BER", "tự đếm + sn.utils.compute_ber", [
        "đếm b ≠ b_hat", "BER = #lỗi / N"], role="util")

    d.edge("src", "map", "bits b")
    d.edge("map", "chan", "symbols x")
    d.edge("chan", "eq", "y nhận")
    d.edge("eq", "demap", "x_hat")
    d.edge("demap", "ber", "b_hat")

    # Đầu vào phụ (noise variance) + CSI cho equalizer
    d.note("no", "no", ["noise variance"])
    d.edge("no", "chan", kind="input", constraint="false")
    d.edge("no", "demap", kind="input", constraint="false")
    d.edge("chan", "eq", "h (CSI)", kind="csi", constraint="false")

    # Ghi chú quy đổi SNR + Monte Carlo
    d.block("snrnote", "", "", [
        MONO("Eb/N0 (dB) — ebnodb2no(ebno_db, num_bits_per_symbol, coderate=1) → no"),
        "Sionna chuẩn hoá Es=1 → no = N0 (tổng phương sai nhiễu PHỨC) = no/2 mỗi chiều thực → trùng N0/2 của sách.",
        "Monte Carlo: dừng khi gặp ≥ 200 lỗi (không cố định số bit), cap ≤ 1e7 bit."],
        role="note", color="#999999")
    d.edge("ber", "snrnote", kind="invis", constraint="false")
    return d


def build_channel_snr():
    """Sơ đồ 3: chi tiết kênh + quy đổi Eb/N0 -> no."""
    d = Diagram(
        "channel_and_snr_detail",
        title="Chi tiết khối kênh & quy đổi Eb/N0 → no",
        rankdir="TB", fontsize="15", ranksep="0.7", nodesep="0.6")

    with d.same() as row:
        row.block("awgn", "Chế độ AWGN", "sn.channel.AWGN", [
            "y = x + n,  n ~ CN(0, no)", "Không méo biên độ/pha", "Equalizer: bỏ qua (h = 1)"],
            role="ch")
        row.block("rayl", "Chế độ Rayleigh (flat) + AWGN", "h = (randn + j·randn)/√2", [
            "y = h·x + n,  h ~ CN(0,1), E[|h|²]=1", "Mỗi symbol một h mới (fast fading)",
            "Equalizer ZF: x_hat = y / h"], role="ch")

    d.kv("snr", "Quy đổi Eb/N0 → no", [
        ("Es/N0 (lin)", "= (Eb/N0 lin) × num_bits_per_symbol"),
        ("no", "= 1 / (Es/N0 lin)    (Sionna đặt Es = 1)"),
        None,
        ("BPSK", "Es/N0 = Eb/N0 × 1"),
        ("QPSK", "Es/N0 = Eb/N0 × 2"),
        ("16QAM", "Es/N0 = Eb/N0 × 4"),
    ], code="no = sn.utils.ebnodb2no(ebno_db, num_bits_per_symbol, coderate=1)",
        margin="0.25,0.18")

    d.note("trap", "CẠM BẪY — noise enhancement", [
        "Ở SNR cao, |h| có thể rất nhỏ → x_hat = y/h khuếch đại nhiễu.",
        "Đây là lý do BER trên Rayleigh tệ hơn AWGN nhiều dù cùng Eb/N0."])

    d.edge("awgn", "snr", kind="invis")
    d.edge("rayl", "snr")
    d.edge("snr", "trap")
    return d


# Đăng ký sơ đồ: tên -> hàm dựng. Thêm sơ đồ mới = thêm 1 dòng ở đây.
DIAGRAMS = {
    "amc_system_overview":    build_amc_system,
    "phy_link_flow":          build_phy_link,
    "channel_and_snr_detail": build_channel_snr,
}


def main(argv):
    names = argv[1:] or list(DIAGRAMS)
    for n in names:
        if n not in DIAGRAMS:
            print(f"[SKIP] khong co diagram '{n}'. Co: {', '.join(DIAGRAMS)}")
            continue
        DIAGRAMS[n]().render()
    print(f"[DONE] dinh dang {FORMATS}. Dung 1 hinh: python draw_system_diagram.py <ten>")


if __name__ == "__main__":
    main(sys.argv)
