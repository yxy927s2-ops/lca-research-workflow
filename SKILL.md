---
name: lci-process-flowchart-17
description: Help LCA researchers answer three questions from collected literature — what data is in it, which data can and should be used, and how to build their own accounting model from it — through a confirmed framework paper, flow-by-flow formula tracing and user review, then a frozen Excel foreground inventory with a conditional Brightway2 modeling-interface handoff. One integrated skill for the full LCA research workflow (lifecycle model building and paper writing) with routed sub-functions — flowchart drawing from frozen inventories (available); parameter optimization, background-database import, LCIA computation, GSA uncertainty analysis, scientific figures, paper writing, model review, peer review (planned, not yet built). Use for literature-to-Excel work. Do not use for LCIA/LCC computation, automatic cross-paper averaging, or one-shot image generation.
---

# LCA 科研全流程：文献 → 清单 → 模型 → 论文

## 总目标与结构

本 skill 围绕一个总目标服务：**对产品构建生命周期模型，并在此基础上开展科研论文写作**。总目标下集成 11 个功能模块（路由表见下）。本文件是总纲＋路由，只在此层定义共享纪律；各功能的具体步骤、检查清单和脚本用法全部在其必读 references 中，**按路由只读所需部分，不整包加载**。

本文件分三层：功能路由表（选功能）→ 跨功能不可变纪律（所有功能共享）→ 各功能路由条目（每个功能一段：状态、阶段链、必读清单）。功能状态分三档：**已有**（可完整执行）、**规划中**（有分支叙述、细则未建）、**未建**（仅有定义，不得执行）。

## 功能路由表

| # | 功能 | 状态 | 触发场景 | 入口／前置 | 必读 |
| --- | --- | --- | --- | --- | --- |
| F0 | 文献搜索 | skill 外 | 用户自行检索后上传资料 | — | — |
| F1 | 文献数据整理 | 已有（主入口） | 从收集的文献到可审核、可冻结的 Excel 前景清单 | 用户上传的原始文献（一手文件） | data-workflow、source-and-candidates、excel-schema、data-framework；做核算再读 data-inventory、calculation-audit；交付汇报读 data-capability-handoff |
| F2 | 基于流程的清单图 | 已有 | 把冻结清单绘制为可编辑的原生 `.drawio` | 冻结 Excel（本 skill 产出，或外部来源但须达同等质量门槛） | figure-workflow 及其中列出的绘图细则；首例同类课题加读 case-drawing-spi-siegrist2026、machine-pipeline-design |
| F3 | 模型参数优化 | 规划中 | 在框架文献流程模型上，借鉴参数选取文献池对参数做符合研究需求的优化 | F1 冻结 Excel＋参数选取文献池 | 暂无独立细则（范式三分类与分配/替代关注口径见 data-workflow；入口决策点为建模路线决策） |
| F4 | 背景数据库接入 | 未建 | ecoinvent 等背景数据库的对接与接口声明 | F1 背景接口字段；F3 后启动 | — |
| F5 | LCIA 模型运算 | 未建 | Brightway 等矩阵计算，产出环境影响结果 | F3／F4 产出 | — |
| F6 | GSA 不确定性分析 | 未建 | 参数不确定性的传播分析 | F3 参数分布；F5 后启动 | — |
| F7 | 科研绘图 | 未建 | 论文配图（清单流程图以外的图） | 各功能交付物 | — |
| F8 | 论文写作 | 未建 | 论文起草 | 各功能交付物 | — |
| F9 | 模型审查 | 未建 | 模型自查／评审前检查 | F3–F6 产出 | — |
| F10 | 论文审稿 | 未建 | 评审意见回复与稿件修改 | F8 稿件＋审稿意见 | — |

## 路由规则

1. 每次工作先按用户意图在路由表中定位唯一功能行，只加载该行的必读文档；其他功能的细则不读。
2. 状态为「未建」的功能：如实告知用户它在路线图中但尚未实现，**不得自行发挥、不得假装已执行**；用户坚持要做时，按当前能力说明能做什么、不能做什么，由用户决定。
3. 功能间流转以交付物为门槛：F1→冻结 Excel；F2→`.drawio`；F3→经优化的参数集；F4→背景库接入声明；F5→LCIA 结果；F6→GSA 结果。下游功能不得绕过上游交付物直接启动。
4. F2 支持**外部冻结清单直接启动**（用户跳过 F1 拿别处清单来画图），但必须达到同等数据质量门槛：来源可溯、候选与采用分离、经用户确认并冻结。门槛未达，先退回 F1 标准的整理与确认。
5. F0 文献搜索由用户进行，skill 不代搜；资料上传后按 F1 流程开展工作。
6. F1、F2 的交付物不含 LCIA／LCC 核算结果；F5 未建成之前，任何功能不得计算 LCIA／LCC。

## 跨功能不可变纪律（共享层）

- **候选与采用分离**：候选值与采用值分开登记；候选不等于采用；不自动平均或改写作者模型；GSA 可使用经审查、可比且条件标明的候选，不自动把多个数拟合成一个分布。
- **科学事实唯一事实源**：Excel 是科学数值与计算追溯的唯一事实源；图、文、说明不得新增或改写科学事实。`PASS`、证据支持、用户确认和独立交叉验证是不同状态，不得以手填"通过"冒充实际复核。
- **来源版本纪律（S1.3）**：多版本按文件内部标识＋关键单元格内容指纹判定权威版；文件名与下载日期不构成版本证据。**中间处理版隔离**：一手原始文件是唯一直接取数基准；用户自制的处理版／衍生版只能参考，其数值进入清单前必须由一手原始值核验并回指原始证据。
- **忠实保存来源分布**：`FIXED`、`UNIFORM`、`TRIANGLE` 等仅在来源明确时归一；未知记 `UNSPECIFIED`；代表值按 data-inventory 规则确定，不能一律称 median；派生流按同一代表情景重算。
- **物理流与负担处理分开**：记录来源是 ALCA 还是 CLCA、是否已有分配／替代；禁止把分配负担和替代收益当物料流，或对已分配值再次抵扣。背景数据库信息是模型元数据，不等于前景物理过程。
- **用户闸门**：功能一决策点——框架确认（闸门 A）、冻结确认（闸门 B）、建模接口判定（闸门 C）；功能三决策点——建模路线决策（范式三分类）。均必须由用户确认；确认前保持草稿；用户否决时记录理由并按规则返工，不自行换路线。
- **能源完整性主动核查**：冻结前逐项核对电力／热等能源数据是否齐全、来自哪一层文件；缺项列入汇报缺口清单，不得以"图上没画"或"用户没问"为由跳过。
- **多副本纪律**：工作区副本与用户侧文件（`.drawio`、Excel）随时可能分叉。任何"改后同步给对方"之前先比对内容指纹；不一致时以用户侧为基准拉入工作区再改；改用户侧文件前先备份其当前版本到工作区；含空格／中文路径用 Python shutil 复制，不用 shell 命令。
- **返工总则**：任何验证失败按对象 ID 定位对应环节，修订后重新检查受影响下游，不只改表面文字；涉及科学值时必须先更新数据功能（F1），不能只改下游产物；复查仍有问题立即向用户报告，不自动宣布退出或通过。

## 功能一「文献数据整理」路由（已有，主入口）

回答三个问题：① 文献里有什么数据？② 哪些能用、哪些应该用？③ 据此怎么把课题模型建起来？交付可审核、可冻结的 Excel 前景清单；满足条件时附 Brightway2 结构映射说明（只映射，不计算）。

**阶段链**：S1.1 研究需求三问（功能单位／系统边界／ALCA 还是 CLCA；三问未定不开工；**不存在直通（不分配/不替代）情形**——若判断课题无需处理联产品负担，视为错误信号，核对文献实际做法并如实汇报）→ S1.2 文献审查＋C1 整链清单判断 → S1.3 多版本核验 → S1.4／C2 划分完整清单池与参数选取池 → S2.1–S2.3＋框架确认（闸门 A：维度比对打分推荐框架，确认时登记范式三分类；只定结构不抓参数；骨架继承快速路径）→ d_c3 框架数据完善性 → S3.1–S3.4 界定模型（边界缩小菱形、最小有证据黑箱、覆盖度矩阵）→ D1／S3.5–S3.7 逐流取数与公式递归溯源 → QC（物料平衡／记录完整／覆盖度＋能源完整性主动核查，不以代数闭合冒充独立验证）→ S4.1＋冻结确认（闸门 B：汇报必含数据支撑能力结论，不能只交文件或笼统称"已完成"）→ S4.2 输出待补参数清单并冻结（`scripts/validate_workbook.py <workbook> --freeze`；冻结交付物＝基于框架文献的生命周期清单（未作处理版）：忠实原始记录层，未分配、未替代、未做 LCIA）→ 建模接口判定（闸门 C：满足多源采用／自有决策／自有方法口径三者其一→S4.3 建模接口说明；否则仅交付冻结清单）。

**当前适用范围**：一次运行锚定一篇框架文献（完整清单池选定），参数候选可来自多篇来源；先做熟单框架文献＋少量参数来源（1–2 篇场景）。多文献参数合成（GSA 分布）、多产品系统并存、多框架对比属 F6 及后续能力，不在本版自动展开。

**必读**：`references/data-workflow.md`（步骤表＋返工规则）、`source-and-candidates.md`、`excel-schema.md`、`data-framework.md`（核心对象、五级数据层级、可采用标准）；逐流取数与核算再读 `data-inventory.md`、`calculation-audit.md`；交付汇报读 `data-capability-handoff.md`。执行流程图 `assets/数据功能工作流_执行版.drawio` 与文本规则一致（文本优先）。

## 功能二「基于流程的清单图」路由（已有）

把冻结清单绘制为模块化、可编辑的原生 `.drawio`（默认单页：上方分模块流程化单元操作＋下方总输入／总输出／总能源三表）。**默认走 v15 全机器流水线，AI 只处理两处判断（分类规则、注释措辞）**：编译器 v2（`build_figure_spec.py`）→ 渲染器（`render_figure.py`，版式模板／自动排版两模式）→ 结构验证（`validate_drawio_layout.py --final`）→ 视觉验收（`export_png.py --scale 1` 亲自分区放大逐区查看，结构 PASS 与视觉 PASS 分开结论）。同时按五关人审关口推进：内容蓝图→无色版式→内容复检→视觉优化→技术检查。脚本只证明结构与映射，不证明画对了。

**必读**：`references/figure-workflow.md`（含入口门槛、五关、机器流水线命令与视觉验收纪律）；按其中关卡加载 `drawing-spec.md`、`drawing-spec-fields.md`、`drawing-data-mapping.md`、`content-coverage-and-balance.md`、`expanded-operation-qa.md`、`summary-table-design.md`、`layout-routing.md`。首例之后的同类课题加读实战模板 `case-drawing-spi-siegrist2026.md` 与设计说明 `machine-pipeline-design.md`；版式模板三件套与管线校准基准在 `examples/spi-siegrist2026/`。第二个金标准案例（范式不同判例：文 ALCA→课 CLCA＋边界裁剪＋用户手排版基准，冻结簿与验收图成对）在 `examples/wpi-guyomarch2024/`。

**交付与边界**：默认只交付原生 `.drawio`。科学事实、公式或代表值改变→解除冻结回 F1；仅排版改变留在本功能。用户已确认过程级量配合操作级拓扑的，绘图时不得重新争论采用数值。

## 功能三至十一定义（未建，仅登记）

- **F3 模型参数优化**（规划中）：在基于框架文献的流程模型上，借鉴参数选取文献池，对参数做符合研究需求的优化。前置：F1 冻结 Excel。**入口决策点为建模路线决策（须用户确认）**：复用功能一的范式三分类——同属 CLCA→重新考虑边际供应商选择；同属 ALCA→重新考虑是否为有代表性的一般模型；不同（文 ALCA→课 CLCA／文 CLCA→课 ALCA）→课题的替代接口／边际供应商或分配因子从零重建，文献的分配/替代做法仅作对照留档（口径见 `data-workflow.md` 范式三分类节）。无独立细则。
- **F4 背景数据库接入**：ecoinvent 等背景数据库的接入与前景／背景接口声明。前置：F1 背景接口字段；模型参数确定后（F3）。
- **F5 LCIA 模型运算**：用 Brightway 等做矩阵计算，产出生命周期环境影响结果。前置：F3／F4。建成前任何功能不得计算 LCIA／LCC。
- **F6 GSA 不确定性分析**：参数不确定性的传播分析（含多文献参数合成分布）。前置：F3 参数分布定义；F5 结果。
- **F7 科研绘图**：论文配图（清单流程图以外的生命周期相关图）。前置：相关功能交付物。
- **F8 论文写作**：论文起草。前置：各功能交付物。
- **F9 模型审查**：模型自查与评审前检查。前置：F3–F6 产出。
- **F10 论文审稿**：评审意见回复与稿件修改。前置：F8 稿件与审稿意见。

## 工具与维护

- 创建、读取或修改 Excel 时使用 Spreadsheets Skill；梳理活动／流与可分离性时使用 `lca-data-organizer`；创建或修改流程图时使用 Draw.io Skill。`diagram-design` 可辅助连线、标签、图例和视觉验收，但其删减节点／拆图原则不能覆盖用户要求的完整流程化清单，HTML／SVG 也不能代替原生 `.drawio`。辅助 Skill 不覆盖本 Skill 的功能边界和用户确认边界。
- 新功能落地时：为其建独立 reference 细则（步骤表＋返工规则＋交付条件），在本文件路由表中将状态改为「已有」并登记必读清单；功能脚本入 `scripts/`，样式与模板入 `assets/`／`examples/`。
- 修改本 Skill 时先保留当前版本，再以两位数字递增；新版本经验证后把旧版完整移入项目 `历史文件/`。文件夹名与 frontmatter `name` 一致；不得覆盖历史版本。
