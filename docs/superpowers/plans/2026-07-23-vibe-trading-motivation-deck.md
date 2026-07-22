# Vibe-Trading Chinese Motivation Deck Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and independently deliver a six-slide Chinese Vibe-Trading deck covering project introduction, Motivation, Challenges, Solution, and evidence-backed Outcome.

**Architecture:** Generate a new 16:9 PowerPoint with `python-pptx`, reusing the validated visual primitives and copied assets from `build/ppt/chinese_master/` without modifying either source deck. Keep content, build logic, asset provenance, and verification in an ignored `build/ppt/chinese_motivation_deck/` workspace, then render and visually audit before copying one final PPTX to the desktop delivery folder.

**Tech Stack:** Python 3.12, python-pptx, Pillow, LibreOffice headless, Poppler, MarkItDown, Office Open XML validator.

---

## File map

- Create `build/ppt/chinese_motivation_deck/work/content.py`: immutable six-slide Chinese storyboard and required text contract.
- Create `build/ppt/chinese_motivation_deck/work/build_deck.py`: native-shape renderers for the six layouts; imports the validated master-deck theme without modifying it.
- Create `build/ppt/chinese_motivation_deck/work/verify_deck.py`: deterministic slide-count, title, stale-text, shape-bound, asset, hash, and font-size checks.
- Create `build/ppt/chinese_motivation_deck/assets/asset_manifest.json`: source and role of every reused visual.
- Create `build/ppt/chinese_motivation_deck/README.md`: exact rebuild and QA commands.
- Create `docs/2026-07-23_session02_motivation_deck.md`: living evidence and delivery record.
- Output `build/ppt/chinese_motivation_deck/Vibe-Trading中文短版_Motivation-Challenges-Solution_2026-07-23.pptx`.
- Deliver `/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading中文短版_Motivation-Challenges-Solution_2026-07-23.pptx`.

### Task 1: Freeze source integrity and storyboard contract

**Files:**
- Create: `build/ppt/chinese_motivation_deck/work/content.py`
- Create: `build/ppt/chinese_motivation_deck/assets/asset_manifest.json`
- Create: `docs/2026-07-23_session02_motivation_deck.md`

- [ ] **Step 1: Record source hashes**

Run:

```bash
shasum -a 256 \
  "/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/中文母版.pptx" \
  "/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading中文母版_全功能版_2026-07-22.pptx"
```

Expected: `6c6617...23d6` for the original and `2ac7cf...d25` for the 22-slide master.

- [ ] **Step 2: Define the six-slide contract**

Create a frozen `SlideSpec` dataclass with `number`, `section`, `title`, `subtitle`, `conclusion`, and `required_text`, then define exactly these titles:

```python
TITLES = (
    "Vibe-Trading",
    "项目简介：把自然语言变成金融研究工作流",
    "Motivation：会回答，不等于会研究",
    "Challenges：真正困难的是把整条链做对",
    "Solution：一个内核，贯穿五段研究闭环",
    "Outcome：把一次回答变成可复用的研究资产",
)
```

- [ ] **Step 3: Add asset provenance**

The manifest must reference only read-only copies already under `build/ppt/chinese_master/`: `source_background.jpeg`, `03_research_pipeline.png`, and `17_run_detail.png`. Mark all three as `reused`; do not edit them.

- [ ] **Step 4: Run the contract check**

Run:

```bash
PYTHONPATH=build/ppt/chinese_motivation_deck/work .venv/bin/python -c "from content import SLIDES; assert len(SLIDES) == 6; assert [s.number for s in SLIDES] == list(range(1, 7))"
```

Expected: exit code 0.

### Task 2: Build the six native layouts

**Files:**
- Create: `build/ppt/chinese_motivation_deck/work/build_deck.py`

- [ ] **Step 1: Reuse the validated theme safely**

Add `build/ppt/chinese_master/work` to `sys.path`, import only public visual primitives such as `add_shell`, `add_text`, `add_card`, `add_stat_card`, `add_pill`, `add_circle`, `add_rect`, `add_shape`, and the shared color/font constants. Define a local title function that uses whitespace and typography without the master theme's decorative underline.

- [ ] **Step 2: Render the cover and project introduction**

Cover: research-pipeline hero, Chinese value proposition, and three compact tags. Project introduction: one sentence definition, input→runtime→output flow, and four evidence stats (`88`, `462`, `23`, `30`).

- [ ] **Step 3: Render Motivation and Challenges**

Motivation uses a left/right contrast (`流畅回答` versus `可验证研究`) plus three transformations. Challenges uses four risk cards converging on a central broken-chain gap and includes structural separation for research, paper, and bounded execution.

- [ ] **Step 4: Render Solution and Outcome**

Solution shows `取证 → 研究 → 组合 → 验证 → 连接` over three foundations (`Agent Runtime`, `Swarm`, `Run Card / Artifacts`) and a native safety rail. Outcome shows one question entering the system and four auditable output classes, plus `75 / 78`, `54`, `8 + options`, and `12` proof points.

- [ ] **Step 5: Save with metadata and bounds checks**

Set slide size to 10 × 5.625 inches, author `HKUDS / Codex`, title `Vibe-Trading 中文短版｜Motivation · Challenges · Solution`, and reject any shape outside the slide rectangle before saving.

- [ ] **Step 6: Build the first draft**

Run:

```bash
PYTHONPATH=build/ppt/chinese_motivation_deck/work .venv/bin/python build/ppt/chinese_motivation_deck/work/build_deck.py
```

Expected: `built ... (6 slides)`.

### Task 3: Add deterministic verification

**Files:**
- Create: `build/ppt/chinese_motivation_deck/work/verify_deck.py`
- Create: `build/ppt/chinese_motivation_deck/README.md`

- [ ] **Step 1: Verify native content and layout**

Check: exactly six slides; 10 × 5.625 inches; every expected title; required tokens `88`, `462`, `23`, `30`, `75 / 78`, `54`, `8 + OPTIONS`, `12`; no `26.3K`, `v0.1.10`, `15.4K`, `Lorem`, or `TBD`; no shapes out of bounds; explicit font sizes at least 6 pt.

- [ ] **Step 2: Verify source isolation**

Hard-code the two known source hashes in the verifier and fail if either source deck changes. Fail if the output path aliases either source path.

- [ ] **Step 3: Run structural verification**

Run:

```bash
PYTHONPATH=build/ppt/chinese_motivation_deck/work .venv/bin/python build/ppt/chinese_motivation_deck/work/verify_deck.py
```

Expected: JSON report with `"status": "pass"`, zero errors, and zero warnings.

- [ ] **Step 4: Run content and package checks**

Run:

```bash
.venv/bin/python -m markitdown build/ppt/chinese_motivation_deck/Vibe-Trading中文短版_Motivation-Challenges-Solution_2026-07-23.pptx
.venv/bin/python /Users/wuhaozhe/.codex/skills/pptx/scripts/office/validate.py build/ppt/chinese_motivation_deck/Vibe-Trading中文短版_Motivation-Challenges-Solution_2026-07-23.pptx
unzip -t build/ppt/chinese_motivation_deck/Vibe-Trading中文短版_Motivation-Challenges-Solution_2026-07-23.pptx
```

Expected: all six sections appear; Office validation passes; ZIP has no errors.

### Task 4: Render, audit, fix, and re-verify

**Files:**
- Create: `build/ppt/chinese_motivation_deck/preview/first_render/*`
- Create: `build/ppt/chinese_motivation_deck/preview/final_render/*`

- [ ] **Step 1: Render the first draft with working Chinese fontconfig**

Run LibreOffice with:

```bash
FONTCONFIG_FILE=/Users/wuhaozhe/miniconda3/etc/fonts/fonts.conf \
FONTCONFIG_PATH=/Users/wuhaozhe/miniconda3/etc/fonts \
soffice --headless --convert-to pdf --outdir build/ppt/chinese_motivation_deck/preview/first_render \
  build/ppt/chinese_motivation_deck/Vibe-Trading中文短版_Motivation-Challenges-Solution_2026-07-23.pptx
```

Then render all pages at 150 dpi with `pdftoppm`.

- [ ] **Step 2: Perform independent visual QA**

Ask one read-only visual QA subagent to inspect all six full-resolution slide images for overlap, clipping, weak hierarchy, uneven gaps, low contrast, excess wrapping, and placeholder text. The main agent independently inspects the contact sheet and every full-resolution slide.

- [ ] **Step 3: Apply at least one evidence-driven fix cycle**

Patch only `build_deck.py` or `content.py` with the issues found, rebuild, rerender into `preview/final_render`, and re-inspect affected slides plus the final contact sheet.

- [ ] **Step 4: Rerun every verifier**

Expected: structural verifier, MarkItDown content check, Office validator, ZIP integrity, six-page PDF, and visual inspection all pass after the fix cycle.

### Task 5: Deliver without overwriting and close the session

**Files:**
- Create: `build/ppt/chinese_motivation_deck/delivery_manifest.json`
- Modify: `docs/2026-07-23_session02_motivation_deck.md`
- Modify: `/Users/wuhaozhe/.claude/projects/-Users-wuhaozhe-PythonProject-pythonProject-Vibe-Trading/memory/project_chinese_master_ppt_20260722.md`

- [ ] **Step 1: Confirm the target is absent**

Run `test ! -e <delivery-path>`. If it exists, stop instead of overwriting.

- [ ] **Step 2: Copy the final PPTX and verify hashes**

Copy the build output to the target. Confirm build and delivery SHA-256 values are identical and both source deck hashes remain unchanged.

- [ ] **Step 3: Write delivery evidence**

Record exact output path, hash, six-slide count, validation results, reused assets, and visual fixes in the delivery manifest and session document.

- [ ] **Step 4: Complete git hygiene**

Run `git status --short --branch`, `git diff --check`, `git stash list`, and list the latest commits. Do not stage build artifacts, push, pull, or make remote comments.

## Plan self-review

- Spec coverage: all eight design-spec sections map to Tasks 1–5.
- Placeholder scan: no TBD, TODO, “similar to,” or undefined implementation step remains.
- Type consistency: one `SlideSpec` contract and one six-slide sequence are used by both build and verification.
- Scope: a single isolated presentation artifact; no application code, API, frontend, or protected agent-core changes.
