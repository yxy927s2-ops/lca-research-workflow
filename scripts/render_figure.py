#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""渲染器：完整绘图规格 + 样式手册 → 原生 .drawio。

两种模式：
  默认（无 --layout）：固定户型自动排版——上标题、中流程区（模块框→操作竖列、
      输入左/输出右）、下三张总表+注释。尺寸现算，不抄案例坐标。
  版式模板（--layout layout.json）：几何坐标全部取自验收案例图提取的模板
      （extract_layout.py），文字内容仍全部来自规格——版式一致、数值不抄。

ID 一律用规格里的约定 ID（ext_F01 / op_M3-OP1 / energy_M2_e ...），
验证器据此核对 规格↔图 一致性。

用法：
  python render_figure.py <完整规格.json> --style assets/figure-style-spi.json \
      --output <图.drawio> [--layout assets/layout-spi.json]
"""
import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

XML_HEAD = ('<mxfile host="app.diagrams.net" type="device">'
            '<diagram id="v15auto" name="Page-1"><mxGraphModel dx="1200" dy="600" '
            'grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" '
            'fold="1" page="1" pageScale="1" pageWidth="{pw}" pageHeight="{ph}" '
            'math="0" shadow="0"><root>'
            '<mxCell id="0"/><mxCell id="1" parent="0"/>')
XML_TAIL = '</root></mxGraphModel></diagram></mxfile>'

SHORT_CARRIER = {"电力": "电", "热量": "热"}
NUMERAL = {"1": "Ⅰ", "2": "Ⅱ", "3": "Ⅲ", "4": "Ⅳ", "5": "Ⅴ"}


class Sheet:
    def __init__(self, style_manual):
        self.parts = []
        self.sm = style_manual
        g = style_manual['roles']
        self.op_geo = g['op']['geo']
        self.in_geo = g['input_box']['geo']
        self.out_geo = g['output_box']['geo']
        self.en_geo = g['module_energy']['geo']
        self.cell_geo = g['table_cell']['geo']

    def cell(self, cid, value, style, x, y, w, h, parent='1'):
        self.parts.append(
            f'<mxCell id="{cid}" value="{escape(value)}" style="{escape(style)}" '
            f'vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>')

    def edge(self, eid, source, target, style):
        self.parts.append(
            f'<mxCell id="{eid}" value="" style="{escape(style)}" edge="1" parent="1" '
            f'source="{source}" target="{target}">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>')

    def edge_routed(self, eid, source, target, style, points):
        """带拐点走线的边（版式模板模式；连接方式与验收案例一致）。"""
        arr = ''.join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points)
        inner = f'<Array as="points">{arr}</Array>' if arr else ''
        self.parts.append(
            f'<mxCell id="{eid}" value="" style="{escape(style)}" edge="1" parent="1" '
            f'source="{source}" target="{target}">'
            f'<mxGeometry relative="1" as="geometry">{inner}</mxGeometry></mxCell>')

    def text(self, cid, value, style, x, y, w, h):
        self.cell(cid, value, style + ';', x, y, w, h)

    def xml(self, pw, ph):
        return XML_HEAD.format(pw=pw, ph=ph) + ''.join(self.parts) + XML_TAIL


def box_text(lab):
    """输入/输出/模块框文字：名称 + 数值（加粗）+ 审计星号。"""
    mark = lab.get('audit_mark') or ''
    return f"{lab['label_name']}<br><b>{lab['display_value']} {lab['unit']}{mark}</b>"


def op_text(display_label, purpose, energy_rows, fonts):
    """操作框文字：名称 + 用途 + 操作级能耗行（与案例 07 同款式）。"""
    parts = [f"<b>{display_label}</b>"]
    if purpose and purpose != display_label:
        parts.append(f"<span style='font-size:{fonts['op_body']}px;color:#4D6755'>{purpose}</span>")
    for e in energy_rows:
        short = SHORT_CARRIER.get(e['carrier'], e['carrier'])
        parts.append(f"<span style='font-size:{fonts['op_body']}px;color:#A75E49'>"
                     f"{short} {e['display_value']} {e['unit']}</span>")
    return "<br>".join(parts)


# ---------------------------------------------------------------------------
# 模式一：固定户型自动排版（无版式模板时的通用回退）
# ---------------------------------------------------------------------------
def render(spec, sm):
    sh = Sheet(sm)
    fonts = sm['fonts']
    roles = sm['roles']
    cov = spec['operation_coverage']
    ops_by_mod = {}
    for c in cov:
        ops_by_mod.setdefault(c['process_id'], []).append(c)
    modules = [n for n in spec['nodes'] if n.get('granularity') == '计算过程']
    modules.sort(key=lambda n: str(n.get('sequence')))
    labels_by_flow = {l['flow_id']: l for l in spec['numeric_labels']}
    io_by_op = {o['drawing_node_id']: o for o in spec['operation_io']}
    energy_by_op = {}
    for e in spec.get('operation_energy', []):
        energy_by_op.setdefault(e['drawing_node_id'], []).append(e)

    C = sm['canvas']
    mod_w = roles['module']['geo']['width']
    op_w, op_h = sh.op_geo['width'], sh.op_geo['height']
    margin, gap = C['margin'], C['gap_modules']

    # ---- 顶部标题 -----------------------------------------------------------
    title = spec['metadata'].get('product_name', {}).get('zh') or spec['metadata'].get('product_system', '')
    sh.text('title', f"<b>{title}</b>",
            'text;html=1;fontFamily=Microsoft YaHei;fontSize=30;fontColor=#243747;align=center;',
            margin, 18, 3 * mod_w + 2 * gap, 46)
    sub = f"功能单位：{spec['metadata'].get('functional_unit','')} · 加工前景 · {spec['metadata'].get('inventory_version','')}"
    sh.text('subtitle', escape(sub), roles['subtitle']['style'],
            margin, 66, 3 * mod_w + 2 * gap, roles['subtitle']['geo']['height'])

    # ---- 模块与操作 ---------------------------------------------------------
    op_xy = {}      # drawing_node_id -> (x, y)
    mod_xy = {}
    y0 = 140
    for i, m in enumerate(modules):
        mx = margin + i * (mod_w + gap)
        ops = ops_by_mod.get(m['node_id'], [])
        n = max(len(ops), 1)
        mod_h = 70 + n * (op_h + 40) + 130
        mod_xy[m['node_id']] = (mx, y0, mod_w, mod_h)
        sh.cell(m['node_id'], m['display_label'], roles['module']['style'], mx, y0, mod_w, mod_h)
        oy = y0 + 60
        for c in ops:
            nid = c['drawing_node_id']
            ox = mx + (mod_w - op_w) / 2
            purpose = c.get('purpose') or (io_by_op.get(nid) or {}).get('purpose') or ''
            val = op_text(c['display_label'], purpose, energy_by_op.get(nid, []), fonts)
            # 挂为模块的子单元（坐标相对模块原点），验证器据此判定操作归属
            sh.cell(nid, val, roles['op']['style'], ox - mx, oy - y0, op_w, op_h,
                    parent=m['node_id'])
            op_xy[nid] = (ox, oy)
            oy += op_h + 40
        # 能耗注释框：一格一框，node_id 与规格 module_annotations 一致
        ex = mx + 30
        for a in spec['module_annotations']:
            if a.get('process_id') != m['node_id'] or not a.get('carrier'):
                continue
            val = f"{a['carrier']}输入&nbsp;<br><b>{a['display_value']} {a['unit']}</b>"
            sh.cell(a['node_id'], val, roles['module_energy']['style'],
                    ex - mx, mod_h - 90, sh.en_geo['width'], sh.en_geo['height'],
                    parent=m['node_id'])
            ex += sh.en_geo['width'] + 16

    # ---- 输入/输出框 + 显示边 -------------------------------------------------
    edge_style = roles['edge_display']['style']
    for e in spec['display_edges']:
        s, t = e['source_node_id'], e['target_node_id']
        lab = labels_by_flow.get(e['flow_id'])
        text = box_text(lab) if lab else ''
        if s.startswith('ext_'):
            tx, ty = op_xy.get(t, (mod_xy.get(t, (margin, y0, 0, 0))[:2]))
            bx = tx - sh.in_geo['width'] - 40
            by = ty + (op_h - sh.in_geo['height']) / 2
            sh.cell(s, text, roles['input_box']['style'], bx, by, sh.in_geo['width'], sh.in_geo['height'])
            sh.edge(e['edge_id'], s, t, edge_style)
        elif t.startswith('out_'):
            sx, sy = op_xy.get(s, (0, y0))
            bx = sx + op_w + 40
            by = sy + (op_h - sh.out_geo['height']) / 2
            sh.cell(t, text, roles['output_box']['style'], bx, by, sh.out_geo['width'], sh.out_geo['height'])
            sh.edge(e['edge_id'], s, t, edge_style)
        else:
            sh.edge(e['edge_id'], s, t, edge_style)
    # 内部主流（link_label 角色）在边中点挂小标签
    for l in spec['numeric_labels']:
        if l['role'] != 'link_label':
            continue
        e = next((x for x in spec['display_edges'] if x['flow_id'] == l['flow_id']), None)
        if not e:
            continue
        s, t = e['source_node_id'], e['target_node_id']
        if s in op_xy and t in op_xy:
            (sx, sy), (tx, ty) = op_xy[s], op_xy[t]
        else:
            continue
        g = roles['link_label']['geo']
        text = f"{l['label_name']}<br>{l['display_value']} {l['unit']}{l.get('audit_mark') or ''}"
        sh.cell(l['node_id'], text, roles['link_label']['style'],
                (sx + tx) / 2 + op_w / 2 + 6, (sy + ty) / 2 + op_h / 2 - 10,
                g['width'], g['height'])
    # 模块级投入/产出框（module_box 角色的 numeric_labels，无 display_edge）：
    # 挂为所属模块的子单元，验证器沿 parent 链判定归属
    drawn_boxes = {e['source_node_id'] for e in spec['display_edges']} | \
                  {e['target_node_id'] for e in spec['display_edges']}
    for l in spec['numeric_labels']:
        if l['node_id'] in drawn_boxes or l['role'] != 'module_box':
            continue
        fid = l['flow_id']
        e = next((x for x in spec['edges'] if x['flow_id'] == fid), None)
        if not e:
            continue
        host = e['target_node_id'] if e['source_node_id'] == 'EXT_IN' else e['source_node_id']
        mx, my, mw, mh = mod_xy.get(host, (margin, y0, mod_w, 300))
        hx, hy = mod_xy.get(host, (0, 0, 0, 0))[:2]
        if e['source_node_id'] == 'EXT_IN':
            sh.cell(l['node_id'], box_text(l), roles['input_box']['style'],
                    mx - hx - sh.in_geo['width'] - 30, my + 60 - hy,
                    sh.in_geo['width'], sh.in_geo['height'], parent=host)
        else:
            sh.cell(l['node_id'], box_text(l), roles['output_box']['style'],
                    mx + mw + 30 - hx, my + 60 - hy,
                    sh.out_geo['width'], sh.out_geo['height'], parent=host)

    # ---- 拓扑边 --------------------------------------------------------------
    top_style = roles['edge_topology']['style']
    for e in spec['topology_edges']:
        sh.edge(e['edge_id'], e['source_node_id'], e['target_node_id'], top_style)

    # ---- 三张总表 --------------------------------------------------------------
    tbl_y = max(my + mh for _, (mx, my, mw, mh) in [(m['node_id'], mod_xy[m['node_id']]) for m in modules]) + 80
    col_w = [410, 210, 105, 295]
    x_cursor = margin
    table_ids = {'总输入清单': 'total-input', '总输出清单': 'total-output', '总能源投入': 'total-energy'}
    for tbl in spec['summary_tables']:
        tid = tbl.get('table_id') or table_ids.get(tbl['title'], 'total-' + tbl['title'])
        ncol = len(tbl.get('columns') or (['模块'] + tbl.get('carriers', [])))
        sh.cell(f'{tid}-title', tbl['title'], roles['table_title']['style'],
                x_cursor, tbl_y, sum(col_w[:ncol]), roles['table_title']['geo']['height'])
        ry = tbl_y + roles['table_title']['geo']['height'] + 4
        if 'rows' in tbl and tbl['rows'] and 'label' in tbl['rows'][0]:
            for j, hname in enumerate(tbl.get('columns', [])):
                sh.cell(f'{tid}-header-{j}', hname, roles['table_cell']['style'],
                        x_cursor + sum(col_w[:j]), ry, col_w[j], sh.cell_geo['height'])
            ry += sh.cell_geo['height'] + 1
            for i, r in enumerate(tbl['rows']):
                vals = [r.get('label', ''), str(r.get('value', '')), r.get('unit', ''), r.get('tag', '') + r.get('audit_mark', '')]
                for j, v in enumerate(vals):
                    st = roles['table_cell_alt']['style'] if i % 2 else roles['table_cell']['style']
                    sh.cell(f'{tid}-row-{i}-{j}', str(v), st,
                            x_cursor + sum(col_w[:j]), ry, col_w[j], sh.cell_geo['height'])
                ry += sh.cell_geo['height'] + 1
        else:  # 能源表
            heads = tbl.get('columns') or (['模块'] + tbl['carriers'])
            for j, hname in enumerate(heads):
                sh.cell(f'{tid}-header-{j}', hname, roles['table_cell']['style'],
                        x_cursor + sum(col_w[:j]), ry, col_w[j], sh.cell_geo['height'])
            ry += sh.cell_geo['height'] + 1
            for i, r in enumerate(tbl['rows']):
                vals = [r.get('group', '')] + [str(r.get(c, '')) for c in tbl['carriers']]
                for j, v in enumerate(vals):
                    st = roles['table_cell_alt']['style'] if i % 2 else roles['table_cell']['style']
                    sh.cell(f'{tid}-row-{i}-{j}', str(v), st,
                            x_cursor + sum(col_w[:j]), ry, col_w[j], sh.cell_geo['height'])
                ry += sh.cell_geo['height'] + 1
        x_cursor += sum(col_w[:ncol]) + 60

    # ---- 注释 ------------------------------------------------------------------
    note_y = tbl_y + 60 + max(
        (len(t['rows']) + 2) * (sh.cell_geo['height'] + 1) for t in spec['summary_tables'])
    audit_any = any(l.get('audit_mark') for l in spec['numeric_labels'])
    fig_note = '图中水量除注明外均为 kg（质量口径）。'
    if audit_any:
        fig_note += ' 带 * 的流为审计中值，口径详见冻结清单问题表。'
    sh.cell('figure-note', fig_note, roles['figure_note']['style'],
            margin, note_y, x_cursor, roles['figure_note']['geo']['height'])
    src = f"来源：{spec['metadata'].get('product_system','')}；冻结版本：{spec['metadata'].get('inventory_version','')}"
    sh.cell('source-note', src, roles['source_note']['style'],
            margin, note_y + 40, x_cursor, roles['source_note']['geo']['height'])

    pw = max(x_cursor + margin, 3 * mod_w + 2 * gap + 2 * margin)
    ph = note_y + 110
    return sh.xml(pw, ph)


# ---------------------------------------------------------------------------
# 模式二：版式模板渲染（几何来自验收案例；文字全部来自规格）
# ---------------------------------------------------------------------------
def render_layout(spec, sm, layout):
    sh = Sheet(sm)
    fonts = sm['fonts']
    roles = sm['roles']
    G = layout['cells']
    T = layout.get('text', {})
    labels_by_flow = {l['flow_id']: l for l in spec['numeric_labels']}
    io_by_op = {o['drawing_node_id']: o for o in spec['operation_io']}
    energy_by_op = {}
    for e in spec.get('operation_energy', []):
        energy_by_op.setdefault(e['drawing_node_id'], []).append(e)
    modules = {n['node_id']: n for n in spec['nodes'] if n.get('granularity') == '计算过程'}
    cov_by_id = {c['drawing_node_id']: c for c in spec['operation_coverage']}
    annotation_by_node = {a['node_id']: a for a in spec['module_annotations']}

    def g(cid):
        if cid not in G:
            raise KeyError(f"版式模板缺少格子: {cid}")
        return G[cid]

    def put(cid, value, style, text_from_layout=False):
        e = g(cid)
        sh.cell(cid, value, e.get('style') or style, e['x'], e['y'], e['w'], e['h'],
                parent=e['parent'])

    # ---- 结构件（模板带走样式；文字：常量用模板，标题类用规格）--------------
    for cid in G:
        e = G[cid]
        if cid in modules:
            put(cid, '', roles['module']['style'])  # 模块名由标题格承担（同 07）
        elif cid.startswith('PR-') and cid.endswith('-header'):
            m = modules.get(e['parent'])
            if m:
                num = NUMERAL.get(str(m.get('sequence')), str(m.get('sequence')))
                put(cid, f"<b>{num} {m['display_label']}</b>", '')
        elif cid.startswith('PR-') and cid.endswith('-en'):
            m = modules.get(e['parent'])
            if m and m.get('en_name'):
                put(cid, m['en_name'], '')
        elif cid.startswith('legend-') or cid in ('title', 'subtitle',
                                                    'figure-note', 'source-note'):
            put(cid, T.get(cid, ''), '')

    # ---- 内容件：操作框（含操作级能耗行）-----------------------------------
    for c in spec['operation_coverage']:
        nid = c['drawing_node_id']
        if nid not in G:
            continue
        purpose = c.get('purpose') or (io_by_op.get(nid) or {}).get('purpose') or ''
        put(nid, op_text(c['display_label'], purpose, energy_by_op.get(nid, []), fonts),
            roles['op']['style'])

    # ---- 内容件：数值标签框（输入/输出/模块框/能耗/主流标签）----------------
    drawn_endpoints = {e['source_node_id'] for e in spec['display_edges']} | \
                      {e['target_node_id'] for e in spec['display_edges']}
    for l in spec['numeric_labels']:
        nid = l['node_id']
        if nid not in G:
            continue
        if l['role'] == 'link_label':
            text = f"{l['label_name']}<br>{l['display_value']} {l['unit']}{l.get('audit_mark') or ''}"
            put(nid, text, roles['link_label']['style'])
            continue
        a = annotation_by_node.get(nid)
        if a and a.get('carrier'):
            text = f"{a['carrier']}输入&nbsp;<br><b>{a['display_value']} {a['unit']}</b>"
            if a.get('note'):
                text += (f"<br><span style='font-size:{fonts['note']}px;"
                         f"color:#A75E49'>{a['note']}</span>")
            put(nid, text, roles['module_energy']['style'])
        elif nid in drawn_endpoints or l['role'] == 'module_box':
            style = roles['input_box']['style'] if l['role'] != 'module_box' else None
            e = next((x for x in spec['edges'] if x['flow_id'] == l['flow_id']), None)
            if l['role'] == 'module_box' and e:
                incoming = e['source_node_id'] == 'EXT_IN'
                style = roles['input_box']['style'] if incoming else roles['output_box']['style']
            put(nid, box_text(l), style or roles['input_box']['style'])

    # ---- 内容件：小注记 ------------------------------------------------------
    note_style = ('text;html=1;whiteSpace=wrap;fontFamily=Microsoft YaHei;'
                  'fontSize=17;fontColor=#243747;align=center;')
    for n in spec.get('extra_labels', []):
        if n['node_id'] in G:
            put(n['node_id'], n['text'], note_style)

    # ---- 边（版式模板带拐点走线；缺走线信息时回退直线）----------------------
    edge_style = roles['edge_display']['style']
    top_style = roles['edge_topology']['style']
    LE = layout.get('edges', {})
    for e in spec['display_edges'] + spec['topology_edges']:
        r = LE.get(e['edge_id'])
        if r:
            sh.edge_routed(e['edge_id'], e['source_node_id'], e['target_node_id'],
                           r['style'], r.get('points', []))
        else:
            fb = top_style if e in spec['topology_edges'] else edge_style
            sh.edge(e['edge_id'], e['source_node_id'], e['target_node_id'], fb)

    # ---- 三张总表（几何走模板，文字走规格）----------------------------------
    for tbl in spec['summary_tables']:
        tid = tbl['drawing_id_prefix']
        put(f'{tid}-title', tbl['title'], roles['table_title']['style'])
        for j, hname in enumerate(tbl.get('columns', [])):
            put(f'{tid}-header-{j}', hname, roles['table_cell']['style'])
        is_energy = 'carriers' in tbl and tbl.get('rows') and 'label' not in tbl['rows'][0]
        for i, r in enumerate(tbl['rows']):
            if is_energy:
                vals = [r.get('group', '')] + [str(r.get(c, '')) for c in tbl['carriers']]
            else:
                vals = [r.get('label', ''), str(r.get('value', '')), r.get('unit', ''),
                        r.get('tag', '') + r.get('audit_mark', '')]
            for j, v in enumerate(vals):
                put(f'{tid}-row-{i}-{j}', str(v), roles['table_cell']['style'])

    pw = layout['canvas']['pageWidth']
    ph = layout['canvas']['pageHeight']
    return sh.xml(pw, ph)


def main():
    ap = argparse.ArgumentParser(description="Render a .drawio from a complete figure spec")
    ap.add_argument('spec', type=Path)
    ap.add_argument('--style', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--layout', type=Path, help='版式模板 JSON（extract_layout.py 从验收案例提取）')
    args = ap.parse_args()
    spec = json.loads(args.spec.read_text(encoding='utf-8'))
    sm = json.loads(args.style.read_text(encoding='utf-8'))
    if args.layout:
        layout = json.loads(args.layout.read_text(encoding='utf-8'))
        xml = render_layout(spec, sm, layout)
    else:
        xml = render(spec, sm)
    args.output.write_text(xml, encoding='utf-8')
    n_cells = xml.count('<mxCell id=')
    print(f'RENDERED: {args.output} ({n_cells} cells)')


if __name__ == '__main__':
    main()
