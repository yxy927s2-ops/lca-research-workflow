#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

from drawing_bridge import PHYSICAL, audit_spec


TOP_LEVEL_KEYS = {
    "schema_version",
    "spec_id",
    "metadata",
    "confirmations",
    "containers",
    "nodes",
    "edges",
    "display_edges",
    "topology_edges",
    "module_annotations",
    "numeric_labels",
    "operation_io",
    "visual_groups",
    "operation_coverage",
    "balances",
    "summary_tables",
    "style",
    "layout",
    "qa",
}

ROUTE_CLASSES = {
    "main_horizontal",
    "input_vertical",
    "output_vertical",
    "branch_orthogonal",
    "recycle_outer",
}

def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"Drawing spec not found: {path}")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")


def duplicate_values(values):
    seen = set()
    duplicates = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def validate(spec, allow_draft=False, workbook=None):
    errors = []
    warnings = []

    missing = sorted(TOP_LEVEL_KEYS - set(spec))
    if missing:
        errors.append("Missing top-level keys: " + ", ".join(missing))
    if spec.get("schema_version") != "0.8":
        errors.append("schema_version must be '0.8' for this Skill version.")

    nodes = spec.get("nodes", [])
    edges = spec.get("edges", [])
    containers = spec.get("containers", [])
    visual_groups = spec.get("visual_groups", [])
    operation_coverage = spec.get("operation_coverage", [])
    balances = spec.get("balances", [])
    summary_tables = spec.get("summary_tables", [])
    display_edges = spec.get("display_edges", [])
    topology_edges = spec.get("topology_edges", [])
    annotations = spec.get("module_annotations", [])
    numeric_labels = spec.get("numeric_labels", [])
    operation_io = spec.get("operation_io", [])
    if not all(isinstance(value, list) for value in (nodes, edges, containers, visual_groups, operation_coverage, balances, summary_tables)):
        errors.append("containers, nodes, edges, visual_groups, operation_coverage, balances, and summary_tables must be arrays.")
        return errors, warnings
    if not all(isinstance(value, list) for value in (display_edges, topology_edges, annotations, numeric_labels, operation_io)):
        errors.append("display_edges, topology_edges, module_annotations, numeric_labels, and operation_io must be arrays.")
        return errors, warnings

    metadata = spec.get("metadata", {})
    if metadata.get("value_scenario") != "representative":
        errors.append("metadata.value_scenario must be 'representative'.")
    mode = metadata.get("modeling_mode")
    if not allow_draft and mode not in {"attributional", "consequential"}:
        errors.append("metadata.modeling_mode must be attributional or consequential for a final spec.")
    if not allow_draft:
        for key in ("functional_unit", "system_boundary", "inventory_version", "source_workbook", "source_content_sha256"):
            if not metadata.get(key):
                errors.append(f"metadata.{key} is required for a final spec.")

    node_ids = [item.get("node_id") for item in nodes]
    empty_node_rows = [str(index + 1) for index, value in enumerate(node_ids) if not value]
    if empty_node_rows:
        errors.append("Nodes missing node_id at array positions: " + ", ".join(empty_node_rows))
    node_duplicates = duplicate_values([value for value in node_ids if value])
    if node_duplicates:
        errors.append("Duplicate node_id values: " + ", ".join(node_duplicates))

    edge_ids = [item.get("edge_id") for item in edges]
    empty_edge_rows = [str(index + 1) for index, value in enumerate(edge_ids) if not value]
    if empty_edge_rows:
        errors.append("Edges missing edge_id at array positions: " + ", ".join(empty_edge_rows))
    edge_duplicates = duplicate_values([value for value in edge_ids if value])
    if edge_duplicates:
        errors.append("Duplicate edge_id values: " + ", ".join(edge_duplicates))

    valid_endpoints = set(value for value in node_ids if value) | {"EXT_IN", "EXT_OUT"}
    for edge in edges:
        edge_id = edge.get("edge_id") or "<missing edge_id>"
        source = edge.get("source_node_id")
        target = edge.get("target_node_id")
        if edge.get("include", True) and source not in valid_endpoints:
            errors.append(f"{edge_id}: invalid source_node_id {source!r}.")
        if edge.get("include", True) and target not in valid_endpoints:
            errors.append(f"{edge_id}: invalid target_node_id {target!r}.")
        if source == "EXT_OUT":
            errors.append(f"{edge_id}: EXT_OUT cannot be a source endpoint.")
        if target == "EXT_IN":
            errors.append(f"{edge_id}: EXT_IN cannot be a target endpoint.")
        if edge.get("include", True) and edge.get("representative_value") is None:
            errors.append(f"{edge_id}: included edge is missing representative_value.")
        if edge.get("include", True) and (not isinstance(edge.get("representative_value"), (int, float)) or isinstance(edge.get("representative_value"), bool)):
            errors.append(f"{edge_id}: included edge needs a numeric representative_value.")
        if edge.get("include", True) and not edge.get("unit"):
            errors.append(f"{edge_id}: included edge is missing unit.")
        if edge.get("include", False) and edge.get("value_type") not in PHYSICAL:
            errors.append(f"{edge_id}: method burden/substitution records cannot be drawn as physical-flow edges.")
        if edge.get("include", True):
            if not edge.get("flow_id"):
                errors.append(f"{edge_id}: included edge is missing flow_id.")
            if not edge.get("visual_role"):
                errors.append(f"{edge_id}: included edge is missing visual_role.")
            route_class = edge.get("route_class")
            if not allow_draft and route_class not in ROUTE_CLASSES:
                errors.append(f"{edge_id}: route_class must be one of {sorted(ROUTE_CLASSES)}.")

    flow_ids = {edge.get("flow_id") for edge in edges if edge.get("flow_id")}
    included_flow_ids = [edge.get("flow_id") for edge in edges if edge.get("include", True) and edge.get("flow_id")]
    repeated_flows = duplicate_values(included_flow_ids)
    if repeated_flows:
        errors.append("Included flow_id values occur on multiple edges: " + ", ".join(repeated_flows))
    if not allow_draft:
        drawn_flows = [item.get("flow_id") for item in display_edges]
        noted_flows = [item.get("flow_id") for item in annotations]
        if duplicate_values([fid for fid in drawn_flows + noted_flows if fid]):
            errors.append("A scientific flow must have exactly one quantitative presentation.")
        if set(drawn_flows + noted_flows) != set(included_flow_ids):
            errors.append("display_edges and module_annotations must cover every included scientific flow exactly once.")
        label_ids = {item.get("node_id") for item in numeric_labels}
        for item in display_edges:
            if not item.get("edge_id") or not item.get("source_node_id") or not item.get("target_node_id"):
                errors.append(f"display_edges {item.get('flow_id')}: missing actual edge ID or endpoint.")
            if not item.get("label_node_id") and item.get("label_policy") != "omit_unambiguous_internal":
                errors.append(f"display_edges {item.get('flow_id')}: independent label or explicit internal-omission policy required.")
            if item.get("label_node_id") and item["label_node_id"] not in label_ids:
                errors.append(f"display_edges {item.get('flow_id')}: unknown independent label node.")
        for item in annotations:
            if not item.get("process_id") or not item.get("node_id"):
                errors.append(f"module_annotations {item.get('flow_id')}: missing process or node ID.")
            if not any(n.get("flow_id") == item.get("flow_id") and n.get("node_id") == item.get("node_id") for n in numeric_labels):
                errors.append(f"module_annotations {item.get('flow_id')}: missing linked numeric label.")
        for item in topology_edges:
            if not all(item.get(key) for key in ("edge_id", "source_node_id", "target_node_id", "material_label", "evidence_ref")):
                errors.append(f"topology_edges {item.get('edge_id')}: endpoint, material label and evidence are required.")
            if not item.get("label_node_id") and item.get("label_policy") != "omit_unambiguous_internal":
                errors.append(f"topology_edges {item.get('edge_id')}: independent label or explicit internal-omission policy required.")
            if item.get("representative_value") is not None:
                errors.append(f"topology_edges {item.get('edge_id')}: cannot invent a quantitative value.")
        actual_edge_ids = [item.get("edge_id") for item in display_edges + topology_edges]
        if duplicate_values([eid for eid in actual_edge_ids if eid]):
            errors.append("Draw.io edge IDs must be unique across display_edges and topology_edges.")
        op_ids = [item.get("drawing_node_id") for item in operation_io]
        if duplicate_values([oid for oid in op_ids if oid]):
            errors.append("operation_io contains duplicate drawing_node_id values.")
        shown_ids = {item.get("drawing_node_id") for item in operation_coverage if item.get("status") == "shown"}
        if shown_ids != set(op_ids):
            errors.append("operation_io must cover every shown operation exactly once.")
        for item in operation_io:
            if not item.get("purpose"):
                errors.append(f"operation_io {item.get('drawing_node_id')}: purpose is required.")
            if not item.get("input_edge_ids") or not item.get("output_edge_ids"):
                errors.append(f"operation_io {item.get('drawing_node_id')}: input and output edge references are required.")
            unknown = set(item.get("input_edge_ids", []) + item.get("output_edge_ids", [])) - set(actual_edge_ids)
            if unknown:
                errors.append(f"operation_io {item.get('drawing_node_id')}: unknown edge IDs {sorted(unknown)}.")
    group_ids = [group.get("visual_group_id") for group in visual_groups]
    group_duplicates = duplicate_values([value for value in group_ids if value])
    if group_duplicates:
        errors.append("Duplicate visual_group_id values: " + ", ".join(group_duplicates))
    for group in visual_groups:
        group_id = group.get("visual_group_id") or "<missing visual_group_id>"
        members = group.get("member_flow_ids", [])
        if not group.get("visual_group_id"):
            errors.append("A visual group is missing visual_group_id.")
        if not isinstance(members, list) or not members:
            errors.append(f"{group_id}: member_flow_ids must be a non-empty array.")
            continue
        missing_members = sorted(set(members) - flow_ids)
        if missing_members:
            errors.append(f"{group_id}: unknown member_flow_ids: {', '.join(missing_members)}.")
        target_ids = {
            edge.get("target_node_id")
            for edge in edges
            if edge.get("flow_id") in members
        }
        if len(target_ids) > 1:
            errors.append(f"{group_id}: grouped flows must share one target_node_id.")

    balance_ids = {item.get("balance_id") for item in balances if item.get("balance_id")}
    table_ids = [item.get("table_id") for item in summary_tables]
    table_duplicates = duplicate_values([value for value in table_ids if value])
    if table_duplicates:
        errors.append("Duplicate table_id values: " + ", ".join(table_duplicates))
    if not allow_draft:
        required_roles = {"total-input", "total-output", "total-energy"}
        actual_roles = [item.get("table_role") for item in summary_tables]
        if len(actual_roles) != 3 or set(actual_roles) != required_roles:
            errors.append("Final figure requires exactly three summary tables: total-input, total-output, total-energy.")
    valid_row_sources = flow_ids | balance_ids
    for table in summary_tables:
        table_id = table.get("table_id") or "<missing table_id>"
        if not table.get("table_id"):
            errors.append("A summary table is missing table_id.")
        columns = table.get("columns")
        if not isinstance(columns, list) or len(columns) < 2:
            errors.append(f"{table_id}: columns must contain at least two column definitions.")
        sources = table.get("row_source_ids")
        if not isinstance(sources, list) or not sources:
            errors.append(f"{table_id}: row_source_ids must be a non-empty array.")
        else:
            unknown_sources = sorted(set(sources) - valid_row_sources)
            if unknown_sources:
                errors.append(f"{table_id}: unknown row_source_ids: {', '.join(unknown_sources)}.")
        if not table.get("total_policy"):
            errors.append(f"{table_id}: total_policy is required.")
        if not table.get("drawing_id_prefix"):
            errors.append(f"{table_id}: drawing_id_prefix is required.")

    layout = spec.get("layout", {})
    for key in ("route_defaults", "port_defaults", "bend_budget"):
        if not allow_draft and not layout.get(key):
            errors.append(f"layout.{key} is required for a non-draft drawing spec.")

    confirmations = spec.get("confirmations", {})
    for phase in ("data", "figure"):
        status = confirmations.get(phase, {}).get("status")
        if status not in {"draft", "confirmed", "reopen"}:
            errors.append(f"confirmations.{phase}.status must be draft, confirmed, or reopen.")
        if not allow_draft and status != "confirmed":
            errors.append(f"confirmations.{phase}.status is not confirmed.")

    if not allow_draft and not nodes:
        errors.append("No nodes are present in a non-draft drawing spec.")
    if not allow_draft and not edges:
        errors.append("No edges are present in a non-draft drawing spec.")
    if not allow_draft and not operation_coverage:
        errors.append("Final spec needs explicit operation_coverage, including repeated internal operations.")
    if not allow_draft and operation_coverage:
        covered = {item.get("process_id") for item in operation_coverage}
        required = {item.get("process_id") for item in nodes if item.get("include", True)}
        if required - covered:
            errors.append("operation_coverage omits model processes: " + ", ".join(sorted(required - covered)))
        for item in operation_coverage:
            if item.get("status") == "missing":
                errors.append(f"operation_coverage has unresolved missing item: {item.get('operation_id')}")
    if allow_draft and (not nodes or not edges):
        warnings.append("Draft spec has empty nodes or edges; structural checks are limited.")

    if not allow_draft:
        if workbook is None:
            errors.append("Final spec requires --workbook to compare scientific fields against the frozen Excel.")
        else:
            errors.extend(audit_spec(spec, workbook))
        warnings.append("Scientific field comparison and structural validation do not prove rendered readability; inspect the actual diagram.")

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Validate an LCI Draw.io drawing specification.")
    parser.add_argument("spec", type=Path, help="Path to drawing-spec JSON")
    parser.add_argument("--allow-draft", action="store_true", help="Allow draft confirmation states and empty object arrays")
    parser.add_argument("--workbook", type=Path, help="Frozen Excel used for a final scientific-field comparison")
    args = parser.parse_args()

    try:
        spec = load_json(args.spec)
        errors, warnings = validate(spec, allow_draft=args.allow_draft, workbook=args.workbook)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"FAILED: {len(errors)} validation error(s).", file=sys.stderr)
        return 1

    print(f"PASS: drawing specification is structurally valid: {args.spec}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
