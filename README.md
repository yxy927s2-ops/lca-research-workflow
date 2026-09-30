# lca-research-workflow

**English | [中文](README.zh.md)**

An integrated research-workflow skill for life cycle assessment (LCA) researchers, covering the full path from **literature → inventory → model → paper**. The skill itself lives in `lci-process-flowchart-17/`.

> Note: the workflow documents under `references/` and `SKILL.md` are currently written in Chinese; an English translation is planned as the workflow matures.

## What problem this solves

Every LCA study starts with the same grind: systematically extracting data from a handful of core papers. Is this paper's inventory complete? Can its functional unit be converted to my study? How are co-products handled? Which parameters can be inherited, and which need new sources? These judgments are scattered, error-prone, and a single mistake forces rework of everything downstream. This skill engineers the critical path from literature to inventory: **the AI does per-paper screening, dimension-by-dimension comparison, and first-pass structuring, while the human only gates decisions** — every trade-off is logged, traceable, and re-runnable.

The workflow follows one main line: starting from user-selected literature, screening and scoring pick a framework paper → the framework's process model is used to delimit the system boundary and extract data flow by flow → after quality checks, everything is frozen into a structured Excel inventory → a machine pipeline compiles and renders the frozen inventory into a process-based life cycle inventory diagram → which serves as the trusted data foundation for subsequent LCA modelling and paper writing. The overarching goal is **to build a life cycle model of a product and to write research papers on that basis**. Core design principles: candidate vs. adopted separation (original literature values and study-adopted values are kept in separate columns and never mixed), per-flow traceability (every data row can answer "which paper, which table"), user gate confirmation (three decision points — framework confirmation, freeze confirmation, modelling-interface adjudication — require explicit user approval), machine re-runnability (structuring and drawing are backed by scripts and validators, not one-off manual work), and mandatory visual acceptance for figures.

**Implemented today**: F1 literature data structuring, F2 process-based inventory diagrams (both validated end-to-end on two real paper projects: soy protein isolate SPI, and whey protein WPI). **On the roadmap**: F3 model parameter optimisation, F4 background database integration (ecoinvent etc.), F5 LCIA computation (Brightway matrix calculations), F6 GSA uncertainty analysis, F7 scientific figure drawing, F8 paper writing, F9 model review, F10 peer review response. F3–F10 are registered and defined in `SKILL.md`; no function may overstep before it is built (e.g., nothing in the skill may compute LCIA/LCC before F5 exists).

## Overall architecture

The overall architecture of the full research workflow (author-maintained master; source file `assets/SKILL逻辑架构.drawio`, editable with draw.io; per-function execution details are in `references/data-workflow.md` and `references/figure-workflow.md`):

![Overall architecture](assets/SKILL逻辑架构.png)

## Feature routing

See the routing table in `SKILL.md` for details. Quick index:

- **F1 Literature data structuring** (implemented, main entry): answers three questions — ① what data do these papers contain? ② which data can be used, and which should be used? ③ how should the study model be built from them? Delivers a frozen Excel inventory; when conditions are met, a Brightway2 modelling-interface mapping is attached (mapping only, no computation).
- **F2 Process-based inventory diagram** (implemented): renders a frozen inventory into a modular process flow diagram (three module groups in a row: input-flow boxes → unit operations → output-flow boxes, plus three summary tables underneath). Inputs are not limited to inventories produced by this skill, but must meet the same data-quality bar (traceable sources, candidate/adopted separation, user-confirmed and frozen).
- **F3 Model parameter optimisation** (planned): optimises parameters on the framework paper's process model, drawing on the parameter-selection literature pool. Details not yet built; the paradigm three-way classification and allocation/substitution handling conventions are in `references/data-workflow.md`, and the modelling-route decision is in the F3 entry of `SKILL.md`.
- **F4–F10** (not built): background database integration (ecoinvent etc.), LCIA computation (Brightway matrix calculations), GSA uncertainty analysis, scientific figure drawing, paper writing, model review, peer review response. Registered in `SKILL.md`; must not be executed before they are built.

**Out of scope** (current version): LCIA/LCC computation (forbidden anywhere in the skill before F5 exists), cross-paper automatic averaging, one-shot image generation.

## Case results (F2 deliverables)

The two figures below are end-to-end deliverables of this skill on two real paper projects (process-based foreground inventory diagrams; all data from public literature — see the README in each case directory):

**Soy protein isolate (SPI)**, framework paper Siegrist et al. (2026):

![SPI case result](examples/spi-siegrist2026/figure-spi-siegrist2026-final.png)

**Whey protein concentrate (WPI)**, framework paper Guyomarc'h et al. (2024):

![WPI case result](examples/wpi-guyomarch2024/figure-wpi-guyomarch2024-final.png)

## Repository structure

```
lca-research-workflow/        # repository root = skill root
├── SKILL.md                  # hub: routing table + cross-function discipline + per-function entries
├── assets/                   # shared assets
│   ├── workbook-template.xlsx        # data-function workbook template (12 sheets)
│   ├── drawing-spec-template.json    # figure specification template
│   ├── display-profile-default.json  # display profile
│   ├── SKILL逻辑架构.drawio/.png     # overall architecture diagram (author-maintained, embedded above)
│   └── *工作流*.drawio               # data/figure function workflow diagrams
├── scripts/                  # machine pipeline
│   ├── build_figure_spec.py          # compiler v2: frozen workbook → complete spec
│   ├── render_figure.py              # renderer: spec → .drawio (layout-template / auto-layout modes)
│   ├── extract_layout.py             # extract layout template from an accepted case figure (geometry + style + edge routing)
│   ├── validate_workbook.py          # workbook validation / freezing
│   ├── validate_drawing_spec.py      # spec validation
│   ├── validate_drawio_layout.py     # structural validation of finished diagrams (--final)
│   └── export_png.py                 # visual acceptance: headless PNG export via draw.io Desktop
├── references/               # detailed rule documents (data workflow, Excel schema, figure rules, case adjudications; 17 files, in Chinese)
└── examples/
    ├── spi-siegrist2026/     # end-to-end acceptance case (data, spec, golden figure, machine figure, layout template; all public data)
    └── wpi-guyomarch2024/    # WPI golden-standard case (frozen workbook + user-accepted figure; paradigm-mismatch / boundary-trimming adjudication)
```

## Quick start

**Figure function (re-run the SPI case)** — from the skill root:

```bash
python scripts/build_figure_spec.py examples/spi-siegrist2026/SPI_CLCA前景清单_v4.3_frozen.xlsx \
    --template assets/drawing-spec-template.json --profile assets/display-profile-default.json \
    --output spec.json
python scripts/render_figure.py spec.json \
    --style examples/spi-siegrist2026/figure-style-spi-siegrist2026.json \
    --layout examples/spi-siegrist2026/layout-spi-siegrist2026.json --output out.drawio
python scripts/validate_drawio_layout.py out.drawio --spec spec.json \
    --workbook examples/spi-siegrist2026/SPI_CLCA前景清单_v4.3_frozen.xlsx --final
python scripts/export_png.py out.drawio   # visual acceptance: you MUST look at the image; always --scale 1
```

**Data function**: start a workbook from `assets/workbook-template.xlsx` and advance gate by gate following the step table in `references/data-workflow.md` (S1 literature screening → framework confirmation (Gate A) → S3 boundary definition and per-flow extraction → QC + freeze confirmation (Gate B) → modelling-interface adjudication (Gate C)); the 12-sheet Excel structure and fact division of labour are in `references/excel-schema.md`.

**Drawing for a new case**: first use `extract_layout.py` to extract a layout template from that project's accepted case figure (a one-time `layout-*-map.json` node mapping is required); without a template the renderer falls back to fixed-layout auto placement.

## Acceptance discipline

A PASS from structural validation ≠ a correct figure. Before delivering any figure, export a PNG and inspect it visually (`scripts/export_png.py`, always `--scale 1`; scale 2 triggers a drawio headless rasterisation truncation bug; the script auto-detects draw.io Desktop and honours `DRAWIO_EXE`). Hard-won lesson: edge waypoints are container-relative coordinates in case figures — extraction must take only the true waypoints in `<Array as="points">` and convert them to absolute coordinates, otherwise the rendered figure gets cross-diagram diagonal lines that structural validation cannot catch.

## Acknowledgements

- Case data: Siegrist et al. (2026), *Sustainable Production and Consumption* (paper's public supplements and the authors' GitHub data).
- Figure conventions reference the XML generation spec maintained by draw.io's official [`jgraph/drawio-mcp`](https://github.com/jgraph/drawio-mcp) (`xml-reference.md`); visual acceptance relies on headless export from [draw.io Desktop](https://github.com/jgraph/drawio-desktop).

## Version history

- **v17** (current): hub restructuring — `SKILL.md` is now a three-layer structure (feature routing table + immutable cross-function discipline + per-function routing entries); features expanded from 2 to 11 (F3–F10 registered: model parameter optimisation, background database integration, LCIA computation, GSA uncertainty analysis, scientific figure drawing, paper writing, model review, peer review response); rules previously only in `SKILL.md` (explicit boundary-trimming inquiry, proactive energy-completeness checks) moved down into `data-workflow.md`; "direct-pass mode" removed (author's ruling: this situation does not exist — if it appears, treat it as an error and verify); WPI case corrected to a paradigm-mismatch adjudication (paper ALCA → study CLCA: allocation factors dropped, marginal suppliers + by-product substitution instead, logged as Q-19 in the workbook); machine-pipeline operational details (commands, the scale-1 lesson, the waypoint lesson) moved down into `figure-workflow.md`. F1/F2 execution capability unchanged.
- **v15**: full machine pipeline for the figure function (compiler v2 + renderer + layout templates); visual acceptance added; SPI case regression passed (41/41 layout geometry, 27 edges zero-diff, energy table 15 cells identical).
- Earlier versions are archived locally per the skill's multi-copy discipline and are not in this repository.

## Author & contact

**yu**, in **Zhejiang A&F University**.

This repository hosts the **stable public release** of the skill; the latest development version is available on request — open an [Issue](../../issues) or email the author at yxy927s2@gmail.com.

## License

- **Code** (`scripts/` etc.): [MIT License](LICENSE)
- **Documents** (README files, `references/`, `SKILL.md`, workflow diagrams): [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
- **Case data** (frozen workbooks in `examples/`): compiled from the public literature and supplements listed above; usage is subject to the terms of the original publications — Siegrist et al. (2026), *Sustainable Production and Consumption*; Guyomarc'h et al. (2024) (WPI case; see the README in each case directory).
