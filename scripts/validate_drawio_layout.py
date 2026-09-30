#!/usr/bin/env python3
"""Deterministic preflight checks for a native draw.io mother file."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from validate_drawing_spec import validate as validate_spec


def style_number(style: str, key: str, default: float | None = None) -> float | None:
    match = re.search(rf"(?:^|;){re.escape(key)}=([0-9.]+)(?:;|$)", style or "")
    return float(match.group(1)) if match else default


def absolute_box(cell_id, cells, geometries):
    x, y, w, h = geometries[cell_id]
    parent = cells[cell_id].get("parent")
    seen = {cell_id}
    while parent in geometries and parent not in seen:
        seen.add(parent)
        px, py, _, _ = geometries[parent]
        x += px
        y += py
        parent = cells[parent].get("parent")
    return x, y, w, h


def table_grid_issues(table, cells, geometries):
    prefix = table.get("drawing_id_prefix", "")
    columns = table.get("columns", [])
    row_sources = table.get("row_source_ids", [])
    table_id = table.get("table_id", "<unknown>")
    grid = [[f"{prefix}-header-{col}" for col in range(len(columns))]]
    grid.extend([[f"{prefix}-row-{row}-{col}" for col in range(len(columns))]
                 for row in range(len(row_sources))])
    missing = [cell_id for row in grid for cell_id in row
               if cell_id not in geometries or cells[cell_id].get("vertex") != "1"]
    if missing:
        return [f"summary table grid incomplete: {table_id}, {len(missing)} cells missing"]
    boxes = [[absolute_box(cell_id, cells, geometries) for cell_id in row] for row in grid]
    issues = []
    tolerance = 2.0
    for row_index, row in enumerate(boxes):
        first_y, first_h = row[0][1], row[0][3]
        for col_index, (x, y, w, h) in enumerate(row):
            if abs(y - first_y) > tolerance or abs(h - first_h) > tolerance:
                issues.append(f"summary table {table_id}: row {row_index} has misaligned cells")
                break
            if col_index and abs((row[col_index - 1][0] + row[col_index - 1][2]) - x) > tolerance:
                issues.append(f"summary table {table_id}: row {row_index} has a column gap/overlap")
                break
    for row_index in range(1, len(boxes)):
        previous = boxes[row_index - 1]
        current = boxes[row_index]
        if abs((previous[0][1] + previous[0][3]) - current[0][1]) > tolerance:
            issues.append(f"summary table {table_id}: row {row_index} has a vertical gap/overlap")
        for col_index in range(len(columns)):
            if (abs(previous[col_index][0] - current[col_index][0]) > tolerance or
                    abs(previous[col_index][2] - current[col_index][2]) > tolerance):
                issues.append(f"summary table {table_id}: column {col_index} does not align across rows")
                break
    return issues


def owning_process(cell_id, cells, process_ids):
    """Return the scientific process containing a displayed operation or card."""
    seen = set()
    while cell_id and cell_id not in seen:
        if cell_id in process_ids:
            return cell_id
        seen.add(cell_id)
        cell_id = cells.get(cell_id).get("parent") if cell_id in cells else None
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("drawio", type=Path)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--workbook", type=Path, help="Frozen Excel; required with --final")
    parser.add_argument("--min-font", type=float, default=12.0)
    parser.add_argument("--min-legend-font", type=float, default=14.0)
    parser.add_argument("--final", action="store_true", help="Require workbook/spec linkage and mapped diagram structures")
    args = parser.parse_args()

    if args.final and (not args.spec or not args.workbook):
        print("FAIL: --final requires both --spec and --workbook; a diagram alone cannot prove content coverage")
        return 1

    try:
        root = ET.parse(args.drawio).getroot()
    except (ET.ParseError, FileNotFoundError) as exc:
        print(f"FAIL: cannot read uncompressed Draw.io XML: {exc}")
        return 1
    model = root.find(".//mxGraphModel")
    if model is None:
        print("FAIL: mxGraphModel missing")
        return 1

    page_w = float(model.get("pageWidth", "0") or 0)
    page_h = float(model.get("pageHeight", "0") or 0)
    ids: set[str] = set()
    cells: dict[str, ET.Element] = {}
    geometries: dict[str, tuple[float, float, float, float]] = {}
    boxes: list[tuple[float, float, float, float]] = []
    failures: list[str] = []
    if args.final and (page_w <= 0 or page_h <= 0):
        failures.append("page width and height must be positive for final export checks")

    for cell in root.findall(".//mxCell"):
        cell_id = cell.get("id", "")
        if cell_id in ids:
            failures.append(f"duplicate id: {cell_id}")
        ids.add(cell_id)
        cells[cell_id] = cell
        if cell.get("vertex") != "1":
            continue
        geom = cell.find("mxGeometry")
        if geom is None:
            continue
        x = float(geom.get("x", "0") or 0)
        y = float(geom.get("y", "0") or 0)
        w = float(geom.get("width", "0") or 0)
        h = float(geom.get("height", "0") or 0)
        if w and h:
            geometries[cell_id] = (x, y, w, h)
        value = re.sub(r"<[^>]+>", "", cell.get("value", "")).strip()
        if not value:
            continue
        font = style_number(cell.get("style", ""), "fontSize", 12.0)
        threshold = args.min_legend_font if cell_id.startswith("legend") else args.min_font
        if font is not None and font < threshold:
            failures.append(f"font too small: {cell_id}={font:g}pt < {threshold:g}pt")

    boxes = [(x, y, x + w, y + h) for cell_id in geometries
             for x, y, w, h in [absolute_box(cell_id, cells, geometries)]]
    if boxes and page_w and page_h:
        min_x = min(b[0] for b in boxes)
        min_y = min(b[1] for b in boxes)
        max_x = max(b[2] for b in boxes)
        max_y = max(b[3] for b in boxes)
        width_ratio = (max_x - min_x) / page_w
        height_ratio = (max_y - min_y) / page_h
        if width_ratio < 0.70 or height_ratio < 0.65:
            print(f"REVIEW: canvas utilization width={width_ratio:.1%}, height={height_ratio:.1%}; inspect rendered whitespace")
        if min_x < -2 or min_y < -2 or max_x > page_w + 2 or max_y > page_h + 2:
            failures.append(f"visible vertex exceeds page bounds: ({min_x:g},{min_y:g})-({max_x:g},{max_y:g}) vs {page_w:g}x{page_h:g}")

    if args.spec:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
        spec_errors, spec_warnings = validate_spec(spec, allow_draft=not args.final, workbook=args.workbook)
        failures.extend(f"drawing spec: {message}" for message in spec_errors)
        for warning in spec_warnings:
            print(f"REVIEW: {warning}")
        if args.final:
            scientific_boxes = []
            for node in spec.get("nodes", []):
                if node.get("include", True):
                    node_id = node.get("node_id")
                    if node_id not in cells or cells[node_id].get("vertex") != "1":
                        failures.append(f"model node not drawn as a vertex: {node_id}")
                    elif node_id in geometries:
                        scientific_boxes.append((node_id, absolute_box(node_id, cells, geometries)))
            for left_index, (left_id, (left_x, left_y, left_w, left_h)) in enumerate(scientific_boxes):
                for right_id, (right_x, right_y, right_w, right_h) in scientific_boxes[left_index + 1:]:
                    overlap_w = min(left_x + left_w, right_x + right_w) - max(left_x, right_x)
                    overlap_h = min(left_y + left_h, right_y + right_h) - max(left_y, right_y)
                    if overlap_w > 2 and overlap_h > 2:
                        failures.append(f"model nodes overlap: {left_id} / {right_id}")
            science_edges = [e for e in spec.get("edges", []) if e.get("include", True)]
            display_edges = spec.get("display_edges")
            annotations = spec.get("module_annotations")
            if display_edges is not None and annotations is not None:
                process_ids = {n.get("node_id") for n in spec.get("nodes", [])}
                drawn = {e.get("flow_id"): e for e in display_edges if e.get("flow_id")}
                noted = {a.get("flow_id"): a for a in annotations}
                expected = {e.get("flow_id") for e in science_edges}
                if set(drawn) & set(noted):
                    failures.append("a scientific flow is both an edge and a module annotation")
                if set(drawn) | set(noted) != expected:
                    failures.append("displayed scientific flow set differs from included Excel flows")
                for edge in science_edges:
                    fid = edge.get("flow_id")
                    if fid in drawn:
                        shown = drawn[fid]
                        cell = cells.get(shown.get("edge_id"))
                        if cell is None or cell.get("edge") != "1":
                            failures.append(f"scientific flow edge not drawn: {fid}")
                            continue
                        for attr, key in (("source", "source_node_id"), ("target", "target_node_id")):
                            terminal = shown.get(key)
                            if cell.get(attr) != terminal:
                                failures.append(f"{fid}: actual {attr} differs from display mapping")
                            scientific = edge.get(key)
                            if scientific not in {"EXT_IN", "EXT_OUT"} and owning_process(terminal, cells, process_ids) != scientific:
                                failures.append(f"{fid}: {attr} operation belongs to the wrong scientific process")
                    elif fid in noted:
                        note = noted[fid]
                        process = edge.get("target_node_id") if edge.get("source_node_id") == "EXT_IN" else edge.get("source_node_id")
                        if note.get("process_id") != process or owning_process(note.get("node_id"), cells, process_ids) != process:
                            failures.append(f"{fid}: module annotation belongs to the wrong scientific process")
                        if not any(n.get("flow_id") == fid and n.get("node_id") == note.get("node_id")
                                   for n in spec.get("numeric_labels", [])):
                            failures.append(f"{fid}: module annotation lacks a linked numeric label")
                topology_edges = spec.get("topology_edges", [])
                for shown in display_edges + topology_edges:
                    edge_id = shown.get("edge_id")
                    cell = cells.get(edge_id)
                    if cell is None or cell.get("edge") != "1":
                        failures.append(f"display/topology edge absent: {edge_id}")
                        continue
                    for attr, key in (("source", "source_node_id"), ("target", "target_node_id")):
                        if cell.get(attr) != shown.get(key):
                            failures.append(f"{edge_id}: actual {attr} differs from display mapping")
                    label_id = shown.get("label_node_id")
                    if label_id and (label_id not in cells or cells[label_id].get("vertex") != "1"):
                        failures.append(f"independent arrow label absent: {edge_id} -> {label_id}")
                    if cell.get("value", "").strip():
                        failures.append(f"arrow has embedded text instead of separate label: {edge_id}")
                for item in spec.get("numeric_labels", []):
                    node_id = item.get("node_id")
                    if node_id not in cells or cells[node_id].get("vertex") != "1":
                        failures.append(f"numeric label absent: {node_id}")
                all_drawn_edges = display_edges + topology_edges
                for operation in spec.get("operation_coverage", []):
                    if operation.get("status") == "shown":
                        op_id = operation.get("drawing_node_id")
                        if not any(e.get("target_node_id") == op_id for e in all_drawn_edges):
                            failures.append(f"operation lacks an incoming flow: {op_id}")
                        if not any(e.get("source_node_id") == op_id for e in all_drawn_edges):
                            failures.append(f"operation lacks an outgoing flow: {op_id}")
                for operation in spec.get("operation_io", []):
                    op_id = operation.get("drawing_node_id")
                    op_cell = cells.get(op_id)
                    purpose = operation.get("purpose", "").strip()
                    if op_cell is not None and purpose:
                        visible = html.unescape(re.sub(r"<[^>]+>", "", op_cell.get("value", "")))
                        if purpose not in visible:
                            failures.append(f"operation purpose absent from its box: {op_id}")
                    for edge_id in operation.get("input_edge_ids", []):
                        if not any(e.get("edge_id") == edge_id and e.get("target_node_id") == op_id for e in all_drawn_edges):
                            failures.append(f"operation input mapping is wrong: {op_id} <- {edge_id}")
                    for edge_id in operation.get("output_edge_ids", []):
                        if not any(e.get("edge_id") == edge_id and e.get("source_node_id") == op_id for e in all_drawn_edges):
                            failures.append(f"operation output mapping is wrong: {op_id} -> {edge_id}")
            else:
                for edge in science_edges:
                    edge_id = edge.get("edge_id")
                    cell = cells.get(edge_id)
                    if cell is None or cell.get("edge") != "1":
                        failures.append(f"scientific flow edge not drawn: {edge_id}")
                        continue
                    for attr, endpoint in (("source", edge.get("source_node_id")), ("target", edge.get("target_node_id"))):
                        if endpoint not in {"EXT_IN", "EXT_OUT"} and cell.get(attr) != endpoint:
                            failures.append(f"{edge_id}: Draw.io {attr} terminal differs from spec {endpoint}")
        for op in spec.get("operation_coverage", []):
            if op.get("status") == "missing":
                failures.append(f"operation missing by spec: {op.get('operation_id')}")
            node_id = op.get("drawing_node_id")
            if op.get("status") == "shown" and node_id not in ids:
                failures.append(f"operation node absent: {op.get('operation_id')} -> {node_id}")
        for bal in spec.get("balances", []):
            if bal.get("display_mode") != "figure":
                continue
            if not bal.get("display_node_id") or bal.get("display_node_id") not in ids:
                failures.append(f"balance display absent: {bal.get('balance_id')}")
            if bal.get("status") == "closed_algebraic" and "非独立" not in bal.get("display_note", ""):
                failures.append(f"algebraic balance lacks limitation: {bal.get('balance_id')}")
        for table in spec.get("summary_tables", []):
            prefix = table.get("drawing_id_prefix", "")
            table_id = table.get("table_id", "<missing table_id>")
            matched = {cell_id for cell_id in ids if prefix and cell_id.startswith(prefix + "-")}
            if args.final and not matched:
                failures.append(f"summary table objects absent: {table_id} -> {prefix}-*")
                continue
            if args.final:
                failures.extend(table_grid_issues(table, cells, geometries))

    if failures:
        print("FAIL")
        for item in failures:
            print(f"- {item}")
        return 1
    print("PASS: structural XML, mapped IDs/terminals, selected coverage and font checks. Rendered text/line collisions still need visual review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
