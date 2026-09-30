# 绘图规格字段

## 工作表角色

| 角色 | 工作表 | 必要性 |
| --- | --- | --- |
| project | `项目说明` | 必需 |
| candidates | `候选数据` | 采用值追溯必需，不直接生成图形 |
| processes | `模型过程` | 必需 |
| parameters | `模型参数` | 代表值追溯必需 |
| flows | `模型流与公式` | 必需 |
| checks | `核算检查` | 数据功能冻结必需 |
| decisions | `问题与决策` | 有未决项时必需 |
| mapping | `绘图确认` | 绘图功能必需 |

同一角色出现多个候选时不得按位置猜测。

## metadata

记录项目编号、产品系统、功能单位、系统边界、目标建模模式、数据库类型、冻结清单版本、来源工作簿及其内容 SHA-256 指纹、语言和目标用途。指纹覆盖相关表格的值、公式及计算缓存，不因重新打包 XLSX 或样式变化而失效。模板不预填 ALCA/CLCA；从用户确认后的 Excel 读取：

- `modeling_mode: attributional` 或 `consequential`
- `allocation_policy` 与 `substitution_status` 记录实际研究政策，不从来源论文或数据库名自动推断
- `value_scenario: representative`

## containers

容器只表示产品系统和功能车间。主线、支线和回流是节点或边的属性，不新增层级。车间顺序来自已确认流程顺序。

## nodes

每个节点至少包含：

`node_id`、`process_id`、`parent_process_id`、`workshop_id`、`name`、`sequence`、`granularity`、`internal_operations`、`branch_role`、`source_refs`、`include`、`expand_mode`、`display_label`、`style_role`、`provenance`。

- 默认一个 `model_process` 对应一个主节点。
- `internal_operations` 默认作为节点内说明，不自动产生拓扑。
- `expand_mode` 只能是 `as_modelled`、`expand_confirmed`、`collapse_confirmed`。
- 设备级展开必须有来源连接或用户确认，不能仅根据参数名产生。

## edges

每条边至少包含：

`edge_id`、`flow_id`、`name`、`category`、`value_type`、`source_node_id`、`target_node_id`、`representative_value`、`display_value`、`unit`、`basis`、`sign_convention`、`method_use_status`、`branch_role`、`visual_role`、`route_class`、`visual_group_id`、`include`、`display_label`、`provenance`。

- 正式图默认只显示 `physical_material`、`physical_energy` 和经确认的 `environment_exchange`。
- `allocated_burden` 与 `substitution_candidate` 均不得作为物理流边 include；后者可用经确认的接口注释表达。
- 负号按方向解释后，图示数值使用非负绝对值。
- 代表值必须来自冻结工作簿，不能在绘图规格中重新计算另一套数值。
- `display_value` 只控制显示精度，不得回写或替代 `representative_value`。
- `route_class` 使用 `main_horizontal`、`input_vertical`、`output_vertical`、`branch_orthogonal` 或 `recycle_outer`。
- 科学 `edges.edge_id` 固定为 `edge_` + `flow_id`，只标识 Excel 流；实际 Draw.io 箭头 ID 由 `display_edges.edge_id` 登记，手工编辑后可以不同，但必须重新核对。
- `visual_group_id` 只允许组合目标过程相同、方向相同且类别兼容的外部输入；各成员仍保留独立 edge 和 flow ID。

展开已确认的内部操作时，`edges` 保留 Excel 科学过程端点。每条画成定量箭头的流在 `display_edges` 登记 `flow_id`、实际 `edge_id`、展示端点和独立 `label_node_id`，检查操作节点的父过程与科学端点一致。操作间只有顺序/物料名称而无独立量时，使用 `topology_edges` 登记实际箭头、端点、物料名和来源证据，不能填入杜撰的数值。仅有模块总量、无法证明归属单一操作的流，在 `module_annotations` 登记 `flow_id`、所属过程与 `node_id`，并以 `numeric_labels` 登记独立数值对象；同一科学流恰好选择一种定量呈现方式。`operation_io` 逐操作记录 `operation_id`、`drawing_node_id`、简短目的及输入/输出的箭头 ID；绿框内不重复写“入/出”清单。验收见 `expanded-operation-qa.md`。

## visual_groups

视觉组不拥有科学事实。每组至少包含：

`visual_group_id`、`group_type`、`target_node_id`、`member_flow_ids`、`display_items`、`layout_role`。

- `member_flow_ids` 必须与 edges 中的成员一一对应。
- `display_items` 逐项显示流名称、显示值和单位，不得只给合计值。
- 一个视觉组不得跨越多个目标过程，也不得混合环境排放与外部投入。

## operation_coverage、balances 与 summary_tables

- `operation_coverage` 保存必要操作、出现次数、证据、Draw.io 节点和覆盖状态；它用于发现漏画，不新增计算过程。
- `balances` 保存核算范围、类型、输入、输出、残差、证据性质和图中显示状态；不同平衡类型分别记录。
- `summary_tables` 保存表格角色、列定义、成员流、合计规则、显示精度和 Draw.io 对象前缀。表格只引用 edges 或 balances，不能维护另一套数值。
- 每个 `summary_tables` 项至少包含 `table_id`、`table_role`、`columns`、`row_source_ids`、`total_policy` 和 `drawing_id_prefix`。列结构和对齐按 `summary-table-design.md`。
- 真实表格的格子 ID 按 `<drawing_id_prefix>-header-<列序号>` 与 `<drawing_id_prefix>-row-<行序号>-<列序号>` 命名，序号从 0 开始；最终检查会核对每个预期格子，不能用一个大文本框伪装表格。

## style 与 layout

样式和布局不属于科学事实。保存调色板、字体、字号、节点角色、边角色、页面方向、车间顺序、节点间距、层间距、目标尺寸和支线路由原则。端口、坐标和 Draw.io ID 仅在生成图时产生。

布局至少记录：`main_axis`、`input_layer`、`branch_layer`、`route_defaults`、`port_defaults`、`bend_budget` 和 `label_clearance`。颜色主题可以为空；端口和折弯规则不可为空。

## qa

必须包括：ID 唯一、端点有效、过程覆盖、物理流筛选、方法负担排除、代表值存在、单位存在、流映射覆盖、视觉组成员一致、端口方向一致、折弯预算、中心对齐、冻结版本一致、数据功能确认、绘图功能确认、无重复视觉流、渲染碰撞检查和最终尺寸可读性。

绘图功能还必须记录五个关卡，以及表格结构、数字对齐、编号一致、颜色语义和灰度可读性。QA 只能由对应检查产生，不能为了通过验证直接手填 `true`。

任一科学 QA 为 false 时不得生成正式图；渲染 QA 为 false 时不得交付。正式规格检查必须传入冻结 Excel，逐流核对 ID、端点、代表值、单位、基准和显示决定。结构验证器只能证明它实际检查的字段与图元；`qa` 布尔值不是实图无重叠的证据，仍须单独渲染复检。
