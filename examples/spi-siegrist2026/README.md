# 案例：Siegrist 2026 大豆分离蛋白（SPI）前景清单与流程图

本目录是 skill 的端到端验收案例：从公开文献数据到冻结 Excel 清单，再到全机器绘制的 Draw.io 流程图。同类课题（植物蛋白加工 LCA 前景清单）以此图为版式与验收基准。

## 数据来源（均为公开渠道）

- 框架文献：Siegrist et al. (2026)，*Sustainable Production and Consumption*——大豆蛋白加工环境影响的参数化 LCA 平台研究（SPI 价值链）。
- 数值出处：论文补充附件（ScienceDirect 随文 mmc 附件：补充说明 Word＋清单 Excel）及作者在 GitHub 公开的代码仓库（代码实际读取的 runtime 数据为权威版；附件存在新旧版本差异，判定过程见 `../../references/case-drawing-spi-siegrist2026.md` 与 `../../references/source-and-candidates.md`）。
- 案例中的全部数值均为上述公开数据，作为教学/验证示例使用。

## 文件清单

| 文件 | 角色 |
| --- | --- |
| `SPI_CLCA前景清单_v4.3_frozen.xlsx` | 数据功能冻结交付：模块化前景清单＋绘图确认表（十二表结构见 `../../references/excel-schema.md`） |
| `drawing-spec-spi-siegrist2026-complete.json` | 编译器 v2 输出的完整绘图规格（冻结工作簿 → 规格的唯一产物） |
| `SPI基于流程的前景清单07.drawio` | 人工绘制的黄金案例图（用户逐轮校对、定稿并保存的版本，版式与内容的验收基准） |
| `SPI基于流程的前景清单_auto_v15.drawio` | 全机器流水线出图（编译器＋渲染器＋版式模板），与黄金图逐格比对通过 |
| `layout-spi-siegrist2026.json` | 版式模板：从黄金图提取的全部格子几何＋样式＋27 条边走线（绝对坐标） |
| `layout-spi-siegrist2026-map.json` | 一次性映射：规格节点 id→黄金图 cell id（提取版式模板用） |
| `figure-style-spi-siegrist2026.json` | 样式手册：框型、颜色、字体、箭头角色常量 |

## 复跑流水线（在 skill 根目录执行）

```bash
# 1. 编译：冻结工作簿 → 完整规格
python scripts/build_figure_spec.py examples/spi-siegrist2026/SPI_CLCA前景清单_v4.3_frozen.xlsx \
    --template assets/drawing-spec-template.json --profile assets/display-profile-default.json \
    --output spec.json
# 2. 渲染：规格 → drawio（版式模板模式）
python scripts/render_figure.py spec.json \
    --style examples/spi-siegrist2026/figure-style-spi-siegrist2026.json \
    --layout examples/spi-siegrist2026/layout-spi-siegrist2026.json \
    --output out.drawio
# 3. 结构验证（必须 PASS）
python scripts/validate_drawio_layout.py out.drawio --spec spec.json \
    --workbook examples/spi-siegrist2026/SPI_CLCA前景清单_v4.3_frozen.xlsx --final
# 4. 视觉验收（必经）：导出 PNG 亲自查看，必须 --scale 1
python scripts/export_png.py out.drawio --scale 1
```

## 验收基线（截至 v15）

- 版式几何：41/41 映射格与黄金图绝对坐标一致；全部 147 格父子结构一致。
- 边：27 条边端点、拐点、线型与黄金图零差异。
- 数值：22 条流标签＋三张总表对齐；能源表 15 格零差异。
- 已登记合法差异 5 处：F11 工艺废水单位统一为 kg（0.6251 kg ↔ 案例图 0.625 L／0.000625 m³）、外部取水框四位小数（16.9800 ↔ 16.98）、总输入/总输出表各 1 格星号口径。
- 已知留白：F24 外部新鲜水作者三处口径不一致（16.5036／16.98／25.852），按用户决定"不锁定、不显示"，图中以步骤加水 25.852 kg 如实呈现（全图唯一实质性留白）。
