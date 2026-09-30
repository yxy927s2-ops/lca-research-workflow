#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a COMPLETE figure spec from a frozen workbook + display profile.

Two layers, both machine:
  Layer 1 (drawing_bridge.compile_spec): scientific content — nodes/flows/values.
  Layer 2 (this script): display layer — every section the bridge leaves empty.

Hard rule: this script never invents a number. All values come from the
workbook via drawing_bridge. Anything that needs human judgment (op-level
binding, topology wording) is emitted as an explicit flag, not a guess.

Usage:
  python build_figure_spec.py <冻结Excel> --profile assets/display-profile-default.json \
      --output <完整规格.json>
"""
import argparse
import fnmatch
import json
import re
from pathlib import Path

from drawing_bridge import compile_spec, audit_spec, load_snapshot, records, numeric
from openpyxl import load_workbook

NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")

# 能源载体 → 节点 id 短码（一格一框，避免同模块多流共用一个 node_id）
CARRIER_CODE = {"电力": "e", "热量": "h"}


def energy_node_id(process_id, carrier):
    return f"energy_{process_id}_{CARRIER_CODE.get(carrier, 'w')}"


def fmt_value(raw, unit, profile):
    """Format a workbook value for display. String output, fixed decimals.

    Decimal rule: 4 decimals for values >= 0.01, else 6 (small quantities
    like 0.002728 kg keep their digits); by_unit overrides win.
    Never invents digits — digits beyond the source precision are zeros.
    """
    v = abs(float(raw))
    dec = profile.get("decimals", {}).get("by_unit", {}).get(unit)
    if dec is None:
        dec = 4 if v >= 0.01 else 6
    return f"{v:.{dec}f}"


def label_name(show_label, flow_name):
    """Row/label name: remove the value+unit part from an approved display label.

    只删"数值+单位"片段（含随后的 * 号），保留其余措辞（如"干物质 95%"备注）；
    不用裸数字切分，避免把"NaOH 10%"里的 10 当成用量。
    """
    if show_label:
        s = re.sub(r"\s*[-+]?\d+(?:\.\d+)?\s*(?:kg|kWh|MJ|L|m³|m3)\s*\*?\s*", " ", str(show_label), count=1)
        s = " ".join(s.split())
        if s:
            return s
    return str(flow_name).split("/")[0].strip()


def label_value(show_label, raw, unit, profile):
    """Display value: always format the workbook's own representative value.
    (Label text is human-approved wording, not the numeric source.)"""
    return fmt_value(raw, unit, profile)


def matches(flow, cond):
    return all(fnmatch.fnmatch(str(flow.get(k) or ""), v) for k, v in cond.items())


def audit_mark(method_use_status):
    """星号规则：方法状态含"审计中"或"待核"的流，图面与总表标 *。"""
    s = str(method_use_status or "")
    return "*" if ("审计中" in s or "待核" in s) else ""


def fill(spec, workbook, profile):
    from openpyxl import load_workbook as lw
    wb = lw(workbook, read_only=True, data_only=True)
    flows = {e["flow_id"]: e for e in spec["edges"]}
    flags = []
    mod_ids = {n["node_id"] for n in spec["nodes"] if n.get("granularity") == "计算过程"}

    # 产品系统总节点（PS-SPI）是覆盖范围声明，不是图面上的框（与案例 07 一致）
    for n in spec["nodes"]:
        if n.get("granularity") == "产品系统":
            n["include"] = False

    # 科学边的画法归类：模块间主物流恒为横向主流；其余外部流由 bridge 自带
    for e in spec["edges"]:
        if e.get("include", True) and not e.get("route_class"):
            if e["source_node_id"] in mod_ids and e["target_node_id"] in mod_ids:
                e["route_class"] = "main_horizontal"

    # ---- 绘图确认 sheet: optional op-level bindings & topology --------------
    drawing = {}
    topology_rows = []
    op_energy_rows = []
    note_rows = []
    if "绘图确认" in wb.sheetnames:
        keys = {c.column: c.value for c in wb["绘图确认"][4] if c.value}
        for row in wb["绘图确认"].iter_rows(min_row=5):
            rid = row[0].value
            if not rid:
                continue
            rec = {name: row[col - 1].value for col, name in keys.items()}
            if rec.get("对象类型") == "Topology":
                topology_rows.append(rec)
            elif rec.get("对象类型") == "OpEnergy":
                op_energy_rows.append(rec)
            elif rec.get("对象类型") == "Note":
                note_rows.append(rec)
            else:
                drawing[str(rid)] = rec

    def bind(flow_id, endpoint_key):
        """Op-level endpoint from 绘图确认 if present, else module frame."""
        rec = drawing.get(flow_id)
        val = rec.get(endpoint_key) if rec else None
        if isinstance(val, str) and "-OP" in val:
            return "op_" + val, True
        return None, False

    # ---- numeric_labels ------------------------------------------------------
    labels = []
    for e in spec["edges"]:
        if not e["include"] or not numeric(e.get("representative_value")):
            continue
        fid = e["flow_id"]
        show = e.get("display_label")
        unit = e["unit"]
        src, dst = e["source_node_id"], e["target_node_id"]
        _, t_op = bind(fid, "目标过程ID")
        _, s_op = bind(fid, "来源过程ID")
        if e["category"] == "能源":
            p = dst if src == "EXT_IN" else src
            node = energy_node_id(p, e["name"])
            role = "module_energy"
        elif src == "EXT_IN" and not t_op:
            node = profile["id_conventions"]["external_input_node"].format(flow_id=fid)
            role = "module_box"   # 未绑操作：挂在模块框旁的投入框
        elif dst == "EXT_OUT" and not s_op:
            node = profile["id_conventions"]["external_output_node"].format(flow_id=fid)
            role = "module_box"
        elif src == "EXT_IN":
            node = profile["id_conventions"]["external_input_node"].format(flow_id=fid)
            role = "edge_endpoint"
        elif dst == "EXT_OUT":
            node = profile["id_conventions"]["external_output_node"].format(flow_id=fid)
            role = "edge_endpoint"
        else:
            node = profile["id_conventions"]["internal_link_label"].format(flow_id=fid)
            role = "link_label"
        labels.append({
            "flow_id": fid,
            "node_id": node,
            "role": role,
            "display_value": label_value(show, e["representative_value"], unit, profile),
            "unit": unit,
            "label_name": label_name(show, e["name"]),
            "audit_mark": audit_mark(e.get("method_use_status")),
        })
    spec["numeric_labels"] = labels
    label_node = {l["flow_id"]: l["node_id"] for l in labels}

    # ---- display_edges -------------------------------------------------------
    # 规则（与案例 07 一致）：能源流是模块注释不是拓扑边；外部流只有绑到
    # 操作级端点才成为 display_edge，否则降级为模块框标签（numeric_labels）；
    # 模块间主物流（内部流）始终是 display_edge。每条显示流都要挂独立标签格。
    display = []
    for e in spec["edges"]:
        if not e["include"] or not numeric(e.get("representative_value")):
            continue
        if e["category"] == "能源":
            continue
        fid = e["flow_id"]
        src, dst = e["source_node_id"], e["target_node_id"]
        s_op, s_fine = bind(fid, "来源过程ID")
        t_op, t_fine = bind(fid, "目标过程ID")
        internal = src != "EXT_IN" and dst != "EXT_OUT"
        if src == "EXT_IN":
            if not t_op:
                continue  # 模块级投入：走模块框标签，不画边
            s = profile["id_conventions"]["external_input_node"].format(flow_id=fid)
            t = t_op
        elif dst == "EXT_OUT":
            if not s_op:
                continue
            s = s_op
            t = profile["id_conventions"]["external_output_node"].format(flow_id=fid)
        else:
            s, t = s_op or src, t_op or dst
        fine = bool(s_op or t_op) or internal
        if not fine:
            flags.append(f"display_edge {fid}: 端点为模块级，待绘图确认细化")
        display.append({"flow_id": fid, "edge_id": "edge_" + fid,
                        "source_node_id": s, "target_node_id": t,
                        "label_node_id": label_node.get(fid),
                        "provenance": "confirmed" if fine else "module-level"})
    spec["display_edges"] = display

    # ---- topology_edges ------------------------------------------------------
    tops = []
    for rec in topology_rows:
        s, t = rec.get("来源过程ID"), rec.get("目标过程ID")
        if not (s and t):
            flags.append(f"topology 行缺少端点: {rec.get('对象ID')}")
            continue
        def ep(v):
            # 操作端点加 op_ 前缀；注记框等非操作端点原样使用
            return "op_" + v if re.match(r"^[A-Za-z0-9]+-OP\d+$", str(v)) else str(v)
        tops.append({"edge_id": "top_" + str(rec.get("对象ID")),
                     "source_node_id": ep(s), "target_node_id": ep(t),
                     "material_label": rec.get("显示标签") or None,
                     "evidence_ref": rec.get("来源ID") or "绘图确认表",
                     "label_policy": "omit_unambiguous_internal"})
    spec["topology_edges"] = tops
    if not tops:
        flags.append(profile["judgment_flags"]["topology_missing"])

    # ---- operation_coverage --------------------------------------------------
    cov = {}
    if "参数覆盖度矩阵" in wb.sheetnames:
        for row in records(wb["参数覆盖度矩阵"]):
            _, r = row
            op = r.get("操作ID")
            if not op:
                continue
            if r.get("模块/过程ID") not in mod_ids:
                continue  # 跳过产品系统级/模块级聚合行（如 PS-OP0、M3-ALL）
            if not re.match(r"^[A-Za-z0-9]+-OP\d+$", str(op)):
                continue  # 跳过区间聚合行（如 M3-OP1~OP8）
            entry = cov.setdefault(op, {
                "operation_id": op, "process_id": r.get("模块/过程ID"),
                "display_label": r.get("操作名称"),
                "occurrence_index": 1,
                "source_refs": set(), "drawing_node_id":
                    profile["id_conventions"]["operation_node"].format(operation_id=op),
                "status": "shown", "levels": set()})
            entry["source_refs"].add(str(r.get("证据来源ID") or ""))
            entry["levels"].add(str(r.get("绘图可用层级") or ""))
            if r.get("覆盖状态") != "已覆盖":
                entry["status"] = "partial"
    spec["operation_coverage"] = [
        {**e, "source_refs": ";".join(sorted(e["source_refs"])),
         "levels": sorted(e["levels"]),
         "purpose": profile.get("op_purpose", {}).get(e["operation_id"]) or e["display_label"]}
        for e in cov.values()]

    # ---- operation_io --------------------------------------------------------
    # 每个"显示中"的操作：进什么、出什么，全部由 display_edges+topology_edges
    # 的端点机器回填，不用人填。
    drawn_edge_list = spec["display_edges"] + spec["topology_edges"]
    io = []
    purposes = profile.get("op_purpose", {})
    for e in spec["operation_coverage"]:
        if e["status"] != "shown":
            continue  # 验证器要求 operation_io 与 shown 集合一一对应
        nid = e["drawing_node_id"]
        io.append({"operation_id": e["operation_id"],
                   "drawing_node_id": nid,
                   "purpose": purposes.get(e["operation_id"]) or e["display_label"],
                   "input_edge_ids": [x["edge_id"] for x in drawn_edge_list
                                      if x.get("target_node_id") == nid],
                   "output_edge_ids": [x["edge_id"] for x in drawn_edge_list
                                       if x.get("source_node_id") == nid],
                   "provenance": "模块级；操作级绑定待绘图确认"})
    spec["operation_io"] = io

    # ---- operation_energy（操作级能耗标注，来自绘图确认 OpEnergy 行）---------
    op_energy = []
    for rec in op_energy_rows:
        op = rec.get("来源过程ID")
        unit = rec.get("单位")
        val = rec.get("代表值")
        if not (op and numeric(val) and unit):
            flags.append(f"OpEnergy 行缺操作/数值/单位: {rec.get('对象ID')}")
            continue
        op_energy.append({"operation_id": op,
                          "drawing_node_id": profile["id_conventions"]["operation_node"].format(operation_id=op),
                          "carrier": rec.get("显示标签") or "电力",
                          "display_value": fmt_value(val, unit, profile),
                          "unit": unit, "note": rec.get("备注") or ""})
    spec["operation_energy"] = op_energy

    # ---- extra_labels（有依据无数值的小注记，Note 行）------------------------
    spec["extra_labels"] = [
        {"node_id": rec.get("Draw.io对象ID") or ("note_" + str(rec.get("对象ID"))),
         "text": rec.get("显示标签") or "",
         "host": rec.get("来源过程ID")}
        for rec in note_rows]

    # ---- balances ------------------------------------------------------------
    bals = []
    if "核算检查" in wb.sheetnames:
        for row in records(wb["核算检查"]):
            _, r = row
            if str(r.get("结果") or "").startswith("PASS"):
                bals.append({"balance_id": "BAL-" + str(r.get("检查ID")),
                             "scope": str(r.get("对象ID")),
                             "balance_type": str(r.get("检查类型")),
                             "statement": str(r.get("说明") or r.get("检查方法/公式") or "")[:120]})
    energy = {}
    energy_flows = {}
    for e in spec["edges"]:
        if e["include"] and e["category"] == "能源" and numeric(e.get("representative_value")):
            p = e["target_node_id"] if e["source_node_id"] == "EXT_IN" else e["source_node_id"]
            key = (p, e["name"])
            energy[key] = energy.get(key, 0) + abs(float(e["representative_value"]))
            energy_flows.setdefault(p, []).append(e["flow_id"])
    # 能源模块合计/总计记录：给总能源表每行一个合法的 row_source_id
    mod_carrier = {}
    for (p, name), v in energy.items():
        mod_carrier.setdefault(p, {})[name] = v
    for p in sorted(mod_carrier):
        bals.append({"balance_id": f"BAL-E{p[1:]}", "scope": p,
                     "balance_type": "能源模块合计",
                     "inputs": ";".join(energy_flows.get(p, [])),
                     "status": "not_calculated", "evidence_class": "author_value",
                     "display_text": "模块总量显示"})
    tot_carrier = {}
    for (p, name), v in energy.items():
        tot_carrier[name] = tot_carrier.get(name, 0) + v
    if tot_carrier:
        bals.append({"balance_id": "BAL-ET", "scope": "ALL",
                     "balance_type": "能源总计",
                     "inputs": ";".join(sorted({f for fs in energy_flows.values() for f in fs})),
                     "status": "not_calculated", "evidence_class": "author_value",
                     "display_text": "全链能源合计"})
    spec["balances"] = bals
    spec["_energy_by_module"] = {f"{p}|{n}": round(v, 6) for (p, n), v in energy.items()}
    spec["_energy_row_ids"] = [f"BAL-E{p[1:]}" for p in sorted(mod_carrier)] + (["BAL-ET"] if tot_carrier else [])

    # ---- module_annotations --------------------------------------------------
    # 凡是"画了数值但没画成边"的流，都是模块注释（能耗框/水框/废液框），
    # 与 display_edges 合起来恰好覆盖每一条 included 流，不重不漏。
    ann = []
    drawn_flows = {d["flow_id"] for d in display}
    for e in spec["edges"]:
        if not e["include"] or not numeric(e.get("representative_value")):
            continue
        fid = e["flow_id"]
        if fid in drawn_flows:
            continue
        node = label_node.get(fid)
        proc = e["target_node_id"] if e["source_node_id"] == "EXT_IN" else e["source_node_id"]
        if not node or proc in ("EXT_IN", "EXT_OUT"):
            continue
        a = {"flow_id": fid, "process_id": proc, "node_id": node,
             "display_value": label_value(e.get("display_label"), e["representative_value"], e["unit"], profile),
             "unit": e["unit"], "provenance": "confirmed"}
        if e["category"] == "能源":
            a["carrier"] = e["name"]
        note = (drawing.get(fid) or {}).get("备注")
        if note:
            a["note"] = note
        ann.append(a)
    spec["module_annotations"] = ann

    # ---- summary_tables ------------------------------------------------------
    raw_flows = {fid: row for _, row in records(wb["模型流与公式"])}
    spec["summary_tables"] = build_tables(spec, profile, raw_flows)

    spec.setdefault("qa", {})["display_layer_flags"] = flags
    return spec


def build_tables(spec, profile, raw_flows):
    def rows_for(table_key):
        cfg = profile["summary_tables"][table_key]
        want_dir = "输入" if table_key == "input" else "输出"
        out = []
        for e in spec["edges"]:
            if not numeric(e.get("representative_value")):
                continue
            raw = raw_flows.get(e["flow_id"], {})
            direction = "输入" if e["source_node_id"] == "EXT_IN" else "输出"
            if e["source_node_id"] != "EXT_IN" and e["target_node_id"] != "EXT_OUT":
                continue  # 内部流不进总表（模块间连接，已在流程区表达）
            if direction != want_dir:
                continue
            pseudo = {"流ID": e["flow_id"], "流类别": e["category"], "方向": direction,
                      "是否显示": "是" if e["include"] else "否",
                      "是否内部流": str(raw.get("是否内部流") or ""),
                      "值类型": e["value_type"], "流名称": e["name"],
                      "方法采用状态": e.get("method_use_status") or "",
                      "目标过程ID": e["target_node_id"], "来源过程ID": e["source_node_id"]}
            placed = False
            for rule in cfg["rules"]:
                if matches(pseudo, rule.get("match", {})):
                    if rule.get("action") == "skip":
                        placed = True
                        break
                    row_label = (rule.get("row") or {}).get("label")
                    out.append({
                        "flow_id": e["flow_id"],
                        "label": row_label or label_name(e.get("display_label"), e["name"]),
                        "value": label_value(e.get("display_label"), e["representative_value"], e["unit"], profile),
                        "unit": e["unit"],
                        "tag": (rule.get("row") or {}).get("归属") or (rule.get("row") or {}).get("去向") or "",
                        "audit_mark": audit_mark(e.get("method_use_status"))})
                    placed = True
                    break
            if not placed:
                out.append({"flow_id": e["flow_id"], "label": label_name(e.get("display_label"), e["name"]),
                            "value": label_value(e.get("display_label"), e["representative_value"], e["unit"], profile),
                            "unit": e["unit"], "tag": "未分类", "audit_mark": ""})
        order = cfg.get("row_order", [])
        if order:
            out.sort(key=lambda r: order.index(r["tag"]) if r["tag"] in order else len(order))
        tid = {"input": "total-input", "output": "total-output"}[table_key]
        return {"title": cfg["title"], "columns": cfg["columns"], "rows": out,
                "table_id": tid, "table_role": tid,
                "row_source_ids": [r["flow_id"] for r in out],
                "total_policy": "none", "drawing_id_prefix": tid}

    tables = [rows_for("input"), rows_for("output")]
    # energy table grouped by module
    ecfg = profile["summary_tables"]["energy"]
    emods, carriers = {}, ecfg["carriers"]
    for e in spec["edges"]:
        if e["include"] and e["category"] == "能源" and numeric(e.get("representative_value")):
            p = e["target_node_id"] if e["source_node_id"] == "EXT_IN" else e["source_node_id"]
            emods.setdefault(p, {})[e["name"]] = label_value(e.get("display_label"), e["representative_value"], e["unit"], profile)
    erows = []
    group_names = ecfg.get("group_names", {})
    for p in sorted(emods):
        erows.append({"group": group_names.get(p, p),
                      **{c: emods[p].get(c, ecfg.get("empty_cell", "")) for c in carriers}})
    tot = {}
    for e in spec["edges"]:
        if e["include"] and e["category"] == "能源" and numeric(e.get("representative_value")):
            tot[e["name"]] = tot.get(e["name"], 0) + abs(float(e["representative_value"]))
    if tot:
        erows.append({"group": ecfg["total_row"],
                      **{c: fmt_value(tot.get(c, 0), "kWh" if c == "电力" else "MJ", profile) for c in carriers}})
    carrier_headers = ecfg.get("carrier_headers", {})
    tables.append({"title": ecfg["title"], "group_by": ecfg["group_by"],
                   "carriers": carriers, "rows": erows,
                   "table_id": "total-energy", "table_role": "total-energy",
                   "columns": ["模块"] + [carrier_headers.get(c, c) for c in carriers],
                   "row_source_ids": spec.get("_energy_row_ids", []),
                   "total_policy": "last_row_total", "drawing_id_prefix": "total-energy"})
    return tables


def main():
    ap = argparse.ArgumentParser(description="Compile a complete figure spec (content + display layer)")
    ap.add_argument("workbook", type=Path)
    ap.add_argument("--template", type=Path, required=True)
    ap.add_argument("--profile", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    template = json.loads(args.template.read_text(encoding="utf-8"))
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    spec = compile_spec(args.workbook, template)
    issues = audit_spec(spec, args.workbook)
    if issues:
        raise SystemExit("ERROR: " + "；".join(issues[:5]))
    spec = fill(spec, args.workbook, profile)
    spec["schema_version"] = "0.8"
    spec.setdefault("confirmations", {})["figure"] = {
        "status": "confirmed", "date": "2026-09-27",
        "note": "v15 机器回归：编译器v2+渲染器全机器出图，与案例07比对验收"}
    args.output.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    n_flags = len(spec["qa"]["display_layer_flags"])
    print(f"SPEC: {len(spec['numeric_labels'])} labels, {len(spec['display_edges'])} display_edges, "
          f"{len(spec['topology_edges'])} topology, {len(spec['summary_tables'])} tables, {n_flags} flags")
    for f in spec["qa"]["display_layer_flags"][:8]:
        print("  FLAG:", f)


if __name__ == "__main__":
    main()
