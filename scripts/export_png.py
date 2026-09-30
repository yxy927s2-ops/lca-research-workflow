# -*- coding: utf-8 -*-
"""视觉验收：调用 draw.io 桌面版无头导出 PNG。

用法:
    python export_png.py <input.drawio> [--output out.png] [--scale 2]

退出码 0 表示导出成功。draw.io 桌面版常见安装位置自动探测，
也可用环境变量 DRAWIO_EXE 指定。
"""
import argparse
import os
import subprocess
import sys

CANDIDATES = [
    os.environ.get("DRAWIO_EXE", ""),
    r"D:\文件-\draw.io\draw.io.exe",
    r"C:\Program Files\draw.io\draw.io.exe",
    r"C:\Program Files (x86)\draw.io\draw.io.exe",
    os.path.expanduser(r"~\AppData\Local\Programs\draw.io\draw.io.exe"),
]


def find_drawio() -> str:
    for p in CANDIDATES:
        if p and os.path.isfile(p):
            return p
    raise SystemExit(
        "未找到 draw.io 桌面版。请安装后重试，或用 DRAWIO_EXE 环境变量指定路径。")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--output", default=None)
    ap.add_argument("--scale", type=float, default=2.0)
    args = ap.parse_args()
    exe = find_drawio()
    out = args.output or os.path.splitext(args.input)[0] + ".png"
    r = subprocess.run(
        [exe, "-x", "-f", "png", "--scale", str(args.scale), "-o", out, args.input],
        capture_output=True, text=True, timeout=300)
    if not os.path.isfile(out):
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit("导出失败: " + args.input)
    print("EXPORTED:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
