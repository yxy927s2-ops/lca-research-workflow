# 操作覆盖与平衡呈现规则

本文件防止“数值存在，但流程节点或核算状态在图中漏掉”。它在坐标布局之前执行。

## 1. 必要操作覆盖表

从冻结 Excel 的模型过程、公式追溯、正文工艺描述和用户已确认流程，编译 `operation_coverage`。每行至少包含：

- `operation_id`：稳定且唯一；
- `process_id` 与顺序号；
- `display_label`；
- `occurrence_index`：同类操作第几次出现；
- `source_refs`：公式、工作表或确认记录；
- `drawing_node_id`；
- `status`：`shown`、`aggregated_explicitly`、`excluded_confirmed` 或 `missing`。

硬门槛：

1. 所有 `shown` 节点必须存在于 Draw.io；
2. `missing` 为零；
3. 离心等重复操作按本案原文/Excel 实际次数逐个显示；SPI 案例为四次，不得沿用通用示例中的“三次”，也不得未经用户同意合并为一个黑箱；
4. 洗涤、沉淀、压榨、闪蒸与喷雾干燥等改变流向或产生输出的操作不得只藏在说明文字里；
5. 因缺少端点证据而不能画成连线的内部回用，不画入正式图；疑点留在 Excel/审核记录，不用“推断/待确认”图面标记掩盖缺证据。

## 2. 平衡状态表

对每个需要呈现的核算建立 `balances`。字段至少包括：

- `balance_id`、`scope`、`balance_type`；
- 输入项、输出项、残差和单位；
- `status`：`closed_algebraic`、`closed_independent`、`open` 或 `not_calculated`；
- `evidence_class` 与图中显示文字。

以下规则只在用户明确要求图中展示平衡摘要时适用；默认将核算状态和差异记录在 Excel/审计材料，不在流程化清单图加“不一致”“未闭合”等审稿式标记：

- `closed_algebraic` 必须写“代数闭合，非独立实测验证”；
- `closed_independent` 才可写“独立验证闭合”；
- `open` 显示残差及未补齐状态，不得虚构损失流使其闭合；
- `not_calculated` 直接写“未核算”，不得用绿色对勾或“平衡”标题暗示已经完成；
- 水平衡、总质量平衡、蛋白平衡和能量合计分别判断。水平衡闭合不代表总质量闭合。

## 3. 可选平衡摘要的最低呈现

若用户要求总览图包含核算，至少展示：

- 核算范围与计量基础；
- 总输入、总输出和残差；
- 平衡状态与证据性质；
- 与整体结论不同的限制，例如“水量代数闭合，但总质量仍有差额”。

详细逐项公式保留在 Excel；图中只放足以避免误读的核算摘要。

## 4. 交付前检查

- `operation_coverage_complete = true`
- `repeat_operation_count_match = true`
- `balance_status_displayed = true`（仅在用户要求图中展示平衡摘要时适用）
- `subbalance_not_overclaimed = true`

任一项失败时，`.drawio` 只能标记为草稿，不能称为完整流程图。
