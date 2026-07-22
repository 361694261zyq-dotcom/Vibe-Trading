# Vibe-Trading HKUDS Image-Led Deck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deliver a six-slide Chinese Vibe-Trading presentation that preserves the HKUDS base from slide 3 of `自制.pptx`, changes only each top-left title, and uses one fully image-generated infographic as each slide body.

**Architecture:** Clone the user deck so its original HKU slide master and `标题和内容` layout stay intact, replace its slide list with six slides created from that layout, and insert one generated PNG under the red rule on every slide. Generate each complete infographic—including Chinese, numbers, and English labels—with the built-in `image_gen` tool using the user reference image as style guidance; never add or repair body text locally. Keep prompts, generated assets, build code, verification, renders, and delivery evidence in an isolated ignored workspace.

**Tech Stack:** Built-in `image_gen`, Python 3.12, python-pptx, Pillow for crop/resize only, LibreOffice headless, Poppler, Office Open XML validator.

---

## File map

- Create `build/ppt/hkuds_image_deck/prompts/prompt_manifest.json`: exact title, content, and image-generation prompt for all six slides.
- Create `build/ppt/hkuds_image_deck/assets/reference_style.png`: read-only copy of the user-provided style reference.
- Create `build/ppt/hkuds_image_deck/assets/generated/slide_01.png` through `slide_06.png`: final fully generated body images.
- Create `build/ppt/hkuds_image_deck/work/content.py`: immutable slide titles, expected facts, source hashes, image paths, and body image rectangle.
- Create `build/ppt/hkuds_image_deck/work/build_deck.py`: clone the HKUDS template package, remove old slides, add six layout-backed slides, set titles, remove body placeholders, and insert one image per slide.
- Create `build/ppt/hkuds_image_deck/work/verify_deck.py`: verify page count, titles, picture count/position, unchanged master visuals, expected image hashes, source isolation, and package integrity.
- Create `build/ppt/hkuds_image_deck/README.md`: exact rebuild, render, and validation commands.
- Create `build/ppt/hkuds_image_deck/delivery_manifest.json`: output hash, source hashes, image-generation provenance, validation results, and visual fixes.
- Create `docs/2026-07-23_session03_hkuds_image_deck.md`: living session evidence and handoff.
- Output `build/ppt/hkuds_image_deck/Vibe-Trading_HKUDS克制图解版_2026-07-23.pptx`.
- Deliver `/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS克制图解版_2026-07-23.pptx`.

### Task 1: Freeze source integrity and exact six-slide contract

**Files:**
- Create: `build/ppt/hkuds_image_deck/work/content.py`
- Create: `build/ppt/hkuds_image_deck/prompts/prompt_manifest.json`
- Create: `build/ppt/hkuds_image_deck/assets/reference_style.png`
- Create: `docs/2026-07-23_session03_hkuds_image_deck.md`

- [ ] **Step 1: Record source hashes and copy only the style reference**

Run:

```bash
shasum -a 256 \
  "/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/自制.pptx" \
  "/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading中文短版_Motivation-Challenges-Solution_2026-07-23.pptx" \
  "/var/folders/hm/3sq1qdfn66l2wkbq99_qmxh80000gn/T/codex-clipboard-e01ca1af-c830-4814-8f07-a4f7e02e4108.png"
```

Expected hashes are `b748ca...7215`, `88b7c7...f6c`, and `ea3371...e0e0`. Copy only the PNG into the isolated asset directory; do not edit either PPTX.

- [ ] **Step 2: Define the immutable slide titles and image rectangle**

Create `content.py` with exactly these titles:

```python
TITLES = (
    "Vibe-Trading",
    "项目简介",
    "Motivation：为什么需要",
    "Challenges：为什么困难",
    "Solution：如何解决",
    "Outcome：交付什么",
)

BODY_RECT = (0.30, 1.12, 9.40, 4.08)
```

The module must also store the two source paths and known source hashes, the six generated-image paths, and the final build/delivery paths.

- [ ] **Step 3: Write six exact image prompts**

Every prompt must identify `reference_style.png` as a style reference, request a restrained academic infographic on a warm-white background, use dark-brown fine lines with muted olive/dusty-rose/HKU-red accents, and prohibit photography, 3D, neon, gradients, watermarks, and extra text. Every prompt must ask for a centered wide `2.3:1` composition with generous blank top/bottom margins so local processing only crops/resizes and never adds text.

The prompts must require these verbatim body labels:

```text
Slide 1: 自然语言问题 / AGENT RUNTIME / 数据 / 工具 / SWARM / 回测 / 证据资产 /
         从“生成答案”走向“交付证据” / 88 Skills / 462 Alphas /
         23 Data Sources / 30 Swarm Presets
Slide 2: INPUT / 定义研究 / RUNTIME / 编排计算 / DELIVERY / 证据闭环 /
         问题与材料 / 假设与边界 / 数据与工具 / BACKTEST / SWARM /
         RUN CARD / 问题 → Agent Runtime → Data & Tools → Backtest & Swarm → Artifacts
Slide 3: 流畅回答 / 看起来合理 / 来源未必清楚 / 条件难以复现 /
         可验证研究 / 能够被检查 / 假设与来源显式 / 结果与警告可追溯 /
         观点 → 假设 / 图表 → 证据 / 一次回答 → 研究资产
Slide 4: 数据挑战 / 多市场异构与时间边界 / 研究挑战 / 前视偏差与过拟合 /
         协作挑战 / 多角色逻辑难统一 / 执行挑战 / 研究、模拟与实盘必须隔离 /
         输入 → 运行 → 证据 / 任何一环失真都会改变结论
Slide 5: AGENT RUNTIME / SWARM / RUN CARD & ARTIFACTS /
         取证 → 研究 → 组合 → 验证 → 连接 /
         RESEARCH & BACKTEST → STOP / PAPER → SIMULATED ACCOUNT → END /
         LIVE → STRUCTURAL GUARD → MANDATE · KILL · AUDIT → BROKER
Slide 6: 一句问题 / “比较 BTC 动量策略，并解释收益、回撤与风险。” /
         VIBE-TRADING / RUN CARD / METRICS / TRADES / WARNINGS /
         75 / 78 Agent Tools / 54 MCP Tools / 8 Engines + Options /
         12 Broker Connectors / 示例回测，非投资建议
```

- [ ] **Step 4: Validate the prompt contract**

Run a Python check that loads the manifest, asserts six unique slide IDs, confirms every required label is present in its prompt, and rejects any prompt containing `460+`, `20+`, `每次交易均需 Mandate 确认`, `GitHub Stars`, or `Forks`.

### Task 2: Generate six complete body infographics

**Files:**
- Create: `build/ppt/hkuds_image_deck/assets/generated/slide_01.png`
- Create: `build/ppt/hkuds_image_deck/assets/generated/slide_02.png`
- Create: `build/ppt/hkuds_image_deck/assets/generated/slide_03.png`
- Create: `build/ppt/hkuds_image_deck/assets/generated/slide_04.png`
- Create: `build/ppt/hkuds_image_deck/assets/generated/slide_05.png`
- Create: `build/ppt/hkuds_image_deck/assets/generated/slide_06.png`

- [ ] **Step 1: Generate one image per prompt with the built-in tool**

Call built-in `image_gen` six times, once per slide, with `reference_style.png` labeled as a style reference. Save every selected result into `assets/generated/`; do not leave project-bound images only in the default generated-image directory.

- [ ] **Step 2: Inspect all six generated images at original resolution**

Check style match, visual hierarchy, body-copy density, obvious hallucinated extra text, clipped elements, relationship direction, and presence of the required numeric anchors. Do not locally add, replace, erase, or repaint any text.

- [ ] **Step 3: Perform the required image-generation fix cycle**

For each blocking image, make one targeted regeneration request that repeats all exact labels and changes only the cited issue. Replace the selected build asset with the regenerated whole image; never patch its pixels or overlay text.

- [ ] **Step 4: Normalize canvas geometry without altering content**

Use Pillow only to crop blank outer margins and resize the complete image to a common `2300 × 1000` PNG canvas. Cropping must not intersect generated content; no drawing or text APIs are allowed.

### Task 3: Build the six-slide HKUDS deck from the real template

**Files:**
- Create: `build/ppt/hkuds_image_deck/work/build_deck.py`
- Create: `build/ppt/hkuds_image_deck/Vibe-Trading_HKUDS克制图解版_2026-07-23.pptx`

- [ ] **Step 1: Clone the user PPTX and preserve its master/layout**

Open `自制.pptx` with `python-pptx`. Remove all existing slide IDs from the cloned presentation, retain its slide masters/layouts/theme/media, and use layout index `1` (`标题和内容`) for every new slide.

- [ ] **Step 2: Create six slides and set only the left title**

For each title, add a slide from layout index `1`, set the title placeholder text, and copy the direct title font/color settings from source slide 3. Remove empty content placeholders from the slide XML so the only slide-level objects are the title placeholder and body picture.

- [ ] **Step 3: Insert exactly one body image per slide**

Insert the matching generated PNG at `BODY_RECT`. Preserve aspect ratio inside that rectangle with white surrounding space where needed; do not crop generated content and do not add captions, footers, page text, or labels.

- [ ] **Step 4: Save metadata and the first build**

Set title `Vibe-Trading｜HKUDS 克制图解版`, subject `Motivation · Challenges · Solution`, author `HKUDS`, and save to the isolated build path. Expected console result: `built 6 slides from HKUDS layout`.

### Task 4: Verify package, content contract, and source isolation

**Files:**
- Create: `build/ppt/hkuds_image_deck/work/verify_deck.py`
- Create: `build/ppt/hkuds_image_deck/README.md`

- [ ] **Step 1: Implement deterministic structural checks**

Verify exactly six slides, `10 × 5.625 in`, exact title sequence, one body picture on every slide, the body picture fully below the red rule and inside slide bounds, no visible slide-level body text, and six distinct image hashes.

- [ ] **Step 2: Verify the template and sources stayed unchanged**

Recompute source hashes; verify slide master/layout relationships remain present in the output; compare the layout picture and line relationship targets with source slide 3. Fail if the output aliases or modifies either source path.

- [ ] **Step 3: Run package validation**

Run:

```bash
PYTHONPATH=build/ppt/hkuds_image_deck/work .venv/bin/python build/ppt/hkuds_image_deck/work/verify_deck.py
.venv/bin/python /Users/wuhaozhe/.codex/skills/pptx/scripts/office/validate.py build/ppt/hkuds_image_deck/Vibe-Trading_HKUDS克制图解版_2026-07-23.pptx
unzip -tq build/ppt/hkuds_image_deck/Vibe-Trading_HKUDS克制图解版_2026-07-23.pptx
```

Expected: structural JSON reports `status: pass`, Office reports `All validations PASSED!`, and ZIP reports no compressed-data errors.

### Task 5: Render, independently audit, regenerate, and re-verify

**Files:**
- Create: `build/ppt/hkuds_image_deck/preview/first_render/*`
- Create: `build/ppt/hkuds_image_deck/preview/final_render/*`

- [ ] **Step 1: Render all slides with the working Chinese font configuration**

Run LibreOffice with the Miniconda fontconfig, convert the PPTX to PDF, render all six pages at 180 dpi with `pdftoppm`, and build a contact sheet.

- [ ] **Step 2: Run independent visual QA**

Ask a read-only visual QA subagent to inspect all six full-resolution images for template damage, overlap, clipping, insufficient margins, unreadable generated copy, low contrast, inconsistent line weight, and style drift. The main agent separately inspects every slide.

- [ ] **Step 3: Complete at least one fix-and-verify cycle**

Regenerate any problematic body image as a whole through `image_gen`; rebuild and rerender. If the problem is only picture placement or title fit, patch `build_deck.py`; do not change generated body text locally.

- [ ] **Step 4: Re-run every verifier after the final render**

Expected: six rendered pages, all structural/package checks pass, source hashes stay unchanged, and the independent reviewer finds no delivery-blocking issue.

### Task 6: Deliver and close the session

**Files:**
- Create: `build/ppt/hkuds_image_deck/delivery_manifest.json`
- Modify: `docs/2026-07-23_session03_hkuds_image_deck.md`
- Modify: `/Users/wuhaozhe/.claude/projects/-Users-wuhaozhe-PythonProject-pythonProject-Vibe-Trading/memory/project_chinese_master_ppt_20260722.md`
- Modify: `/Users/wuhaozhe/.codex/memories/CODEX_MEMORY.md`

- [ ] **Step 1: Protect the delivery target**

Confirm the target path does not exist. If it exists, create a versioned sibling instead of overwriting it.

- [ ] **Step 2: Copy and verify the final PPTX**

Copy the build output into the desktop folder. Confirm build and delivery SHA-256 values match and both source deck hashes remain unchanged.

- [ ] **Step 3: Record evidence and reusable prompts**

Write the exact output path/hash, source hashes, six final image hashes, built-in image-generation prompt set, validation results, visual QA findings/fixes, and final contact-sheet path into the delivery manifest and session document.

- [ ] **Step 4: Complete local git hygiene**

Run `git status --short --branch`, `git diff --check`, `git log -5 --oneline --decorate`, and `git stash list`. Do not pull, push, stage ignored build artifacts, or perform any remote operation.

## Plan self-review

- Spec coverage: the real HKUDS layout, title-only edits, single generated body image, six-page content map, full image-model text generation, safety correction, verification, visual QA, and source preservation each map to an explicit task.
- Placeholder scan: no unresolved placeholder, implied repeated step, or undefined content label remains.
- Type/path consistency: `TITLES`, `BODY_RECT`, six generated-image paths, output path, and delivery path are defined once in Task 1 and consumed by build/verification tasks.
- Scope: one isolated presentation artifact; no product code, protected Agent core, API, frontend, or remote state changes.
