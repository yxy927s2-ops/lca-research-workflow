#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从验收案例图提取版式模板（geometry + 结构件样式/文字）。

输出 layout JSON：
  canvas: 页面尺寸
  cells:  {规格节点 id: {x, y, w, h, parent, style}}   — 内容件的坐标载体
  text:   {结构件 id: 文字}                            — 图例/注释等常量措辞（案例已审定）

内容件（操作/输入输出框/能耗框/标签/三张总表/模块框）的 id 先按 map 翻成
规格 id；结构件（title/subtitle/PR-* 模块标题/legend-*/figure-note/
source-note）保留原 id 并带走文字。图例组会被展平成绝对坐标、parent=1。

用法：
  python extract_layout.py <案例图.drawio> --map <layout-spi-map.json> \
      --output <layout-spi.json>
"""
import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

STRUCT_PREFIXES = ("title", "subtitle", "figure-note", "source-note",
                   "PR-", "legend-", "total-")


def strip_html(value):
    return " ".join(re.sub(r"<[^>]+>", " ", html.unescape(value or "")).split())


def main():
    ap = argparse.ArgumentParser(description="Extract a layout template from an approved case drawio")
    ap.add_argument("drawio", type=Path)
    ap.add_argument("--map", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    id_map = json.loads(args.map.read_text(encoding="utf-8"))["map"]  # spec_id -> case_id
    edge_map = json.loads(args.map.read_text(encoding="utf-8")).get("edges", {})  # spec_edge_id -> case_edge_id
    rev = {v: k for k, v in id_map.items()}

    root = ET.parse(args.drawio).getroot()
    model = root.find(".//mxGraphModel")
    if model is None:
        raise SystemExit("mxGraphModel missing")

    geo = {}
    meta = {}
    for c in model.findall(".//mxCell"):
        g = c.find("mxGeometry")
        if c.get("vertex") == "1" and g is not None:
            cid = c.get("id")
            geo[cid] = (float(g.get("x", 0) or 0), float(g.get("y", 0) or 0),
                        float(g.get("width", 0) or 0), float(g.get("height", 0) or 0))
            meta[cid] = {"style": c.get("style") or "",
                         "text": strip_html(c.get("value") or ""),
                         "parent": c.get("parent") or "1"}

    def parent_offset(pid):
        """容器链的绝对偏移（拐点坐标系 = 边 parent 所在容器）。"""
        x = y = 0.0
        seen = set()
        cur = pid
        while cur in geo and cur not in seen:
            seen.add(cur)
            gx, gy, _, _ = geo[cur]
            x += gx
            y += gy
            cur = meta[cur]["parent"]
        return x, y

    edges = {}
    for c in model.findall(".//mxCell"):
        if c.get("edge") != "1":
            continue
        cid = c.get("id")
        spec_eid = next((k for k, v in edge_map.items() if v == cid), None)
        if spec_eid is None:
            continue
        g = c.find("mxGeometry")
        # 只取 <Array as="points"> 里的真拐点；忽略 sourcePoint/targetPoint，
        # 并把容器相对坐标换算为绝对坐标（渲染时边统一挂根层）。
        points = []
        arr = g.find("Array") if g is not None else None
        if arr is not None:
            ox, oy = parent_offset(c.get("parent") or "1")
            for p in arr.findall("mxPoint"):
                points.append([round(float(p.get("x", 0) or 0) + ox, 1),
                               round(float(p.get("y", 0) or 0) + oy, 1)])
        src = rev.get(c.get("source"), c.get("source"))
        tgt = rev.get(c.get("target"), c.get("target"))
        edges[spec_eid] = {"source": src, "target": tgt,
                           "style": c.get("style") or "", "points": points}

    def absolute(cid):
        x, y, w, h = geo[cid]
        seen = {cid}
        p = meta[cid]["parent"]
        while p in geo and p not in seen:
            seen.add(p)
            px, py, _, _ = geo[p]
            x += px
            y += py
            p = meta[p]["parent"]
        return x, y, w, h

    cells, text = {}, {}
    for cid in geo:
        is_struct = cid.startswith(STRUCT_PREFIXES) or cid in ("M1", "M2", "M3")
        spec_id = rev.get(cid, cid if is_struct else None)
        if spec_id is None:
            continue
        x, y, w, h = geo[cid]
        parent = meta[cid]["parent"]
        if parent not in ("1", "M1", "M2", "M3"):
            parent = "1"  # 图例组等展平为绝对坐标
            x, y, w, h = absolute(cid)
        entry = {"x": round(x, 1), "y": round(y, 1), "w": round(w, 1), "h": round(h, 1),
                 "parent": parent, "style": meta[cid]["style"]}
        if is_struct and cid not in ("M1", "M2", "M3"):
            if meta[cid]["text"]:
                text[spec_id] = meta[cid]["text"]
        cells[spec_id] = entry

    layout = {
        "canvas": {"pageWidth": float(model.get("pageWidth", "0")),
                   "pageHeight": float(model.get("pageHeight", "0"))},
        "cells": cells,
        "text": text,
        "edges": edges,
    }
    args.output.write_text(json.dumps(layout, ensure_ascii=False, indent=1) + "\n",
                           encoding="utf-8")
    print(f"LAYOUT: {len(cells)} cells ({sum(1 for k in cells if k in id_map)} mapped), "
          f"{len(text)} structural texts, {len(edges)} routed edges")


if __name__ == "__main__":
    main()
