"""
build.py — render các sơ đồ D2 (*.d2) thành *.svg.
======================================================================
Mỗi sơ đồ là MỘT file .d2 (source thuần D2, sửa trực tiếp). File này chỉ
lo việc render: tìm d2.exe, áp cờ thống nhất, xuất .svg cùng tên.

CHẠY
  python build.py                      # render TẤT CẢ sơ đồ
  python build.py amc_system_overview  # chỉ render 1 sơ đồ (nhanh)
  python build.py a b                  # render vài sơ đồ
Thoát mã 0 nếu mọi sơ đồ OK; mã 1 nếu có file lỗi/không tìm thấy
(để dùng được trong pre-commit hook / CI mà không "xanh giả").

QUY ƯỚC
  • File bắt đầu bằng "_" (vd _theme.d2) chỉ để IMPORT, KHÔNG render.
  • Style/màu dùng chung nằm ở _theme.d2 (sửa 1 chỗ, áp mọi sơ đồ).
  • Cờ render chung ở FLAGS bên dưới. "--scale 1" => SVG có kích thước cố
    định, zoom được như ý (bỏ --scale thì SVG bị co về khung -> kẹt mức zoom).
    Lưu ý: "scale" KHÔNG phải key d2-config hợp lệ trong D2 v0.7.1 nên BẮT
    BUỘC để ở cờ CLI tại đây, không nhét được vào file .d2.
======================================================================
"""

import os
import sys
import glob
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

# D2 cài qua winget -> đường dẫn mặc định; fallback: 'd2' trên PATH.
_D2BIN = r"C:\Program Files\D2\d2.exe"
D2 = _D2BIN if os.path.isfile(_D2BIN) else "d2"

# Cờ render dùng CHUNG cho mọi sơ đồ (đổi 1 chỗ, áp tất cả).
FLAGS = ["--scale", "1", "--pad", "40"]


def sources():
    """Mọi *.d2 trong thư mục này, TRỪ file bắt đầu bằng '_' (chỉ để import)."""
    return sorted(p for p in glob.glob(os.path.join(HERE, "*.d2"))
                  if not os.path.basename(p).startswith("_"))


def render(path):
    """Render 1 file .d2 -> .svg. Trả về returncode của d2 (0 = OK).
    CHẠY d2 với cwd=HERE và truyền tên file TƯƠNG ĐỐI: D2 v0.7.1 phân giải
    import "...@_theme" theo cwd (KHÔNG theo thư mục file), nên phải đặt cwd
    tại thư mục chứa _theme.d2 thì import mới chạy dù gọi build.py từ đâu."""
    name = os.path.splitext(os.path.basename(path))[0]
    r = subprocess.run([D2, *FLAGS, name + ".d2", name + ".svg"],
                       cwd=HERE, capture_output=True)
    # d2 in tiến trình ra stderr; sanitize để không vỡ console cp1252 trên Windows.
    msg = (r.stderr or r.stdout).decode("utf-8", "replace").strip()
    msg = msg.encode("ascii", "replace").decode()
    if r.returncode != 0:
        print(f"[FAIL] {name}: {msg}")
    else:
        print(f"[OK]   {name}.svg")
    return r.returncode


def main(argv):
    names = argv[1:]
    paths = ([os.path.join(HERE, n if n.endswith(".d2") else n + ".d2") for n in names]
             if names else sources())
    failures = 0
    for p in paths:
        if not os.path.isfile(p):
            print(f"[SKIP] khong thay {os.path.basename(p)}")
            failures += 1
            continue
        if render(p) != 0:
            failures += 1
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main(sys.argv)
