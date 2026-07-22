# Vibe-Trading HKUDS Editable Caption v3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a new six-slide HKUDS deck with smaller body images, editable one-line captions, and smaller top-left titles.

**Architecture:** Treat the delivered v2 PPTX as read-only. Unpack its Office Open XML, apply deterministic geometry and text-box edits to each slide XML, clean and repack to a new v3 filename, then render and verify the result. No generated image or source deck is modified.

**Tech Stack:** Office Open XML, PPTX skill unpack/clean/pack scripts, `apply_patch`, LibreOffice, Poppler, `python-pptx` for read-only verification.

---

### Task 1: Prepare an isolated v3 package

**Files:**
- Read: `/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS克制图解版_v2_2026-07-23.pptx`
- Create: `build/ppt/hkuds_image_deck_v3/unpacked/`

- [ ] **Step 1: Confirm the v2 hash**

Run:

```bash
shasum -a 256 '/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS克制图解版_v2_2026-07-23.pptx'
```

Expected: `d4e62ee768d03ea5dbbe2c4c80a621802c555a4ac9d3c86ae4371041d2190c4b`.

- [ ] **Step 2: Unpack v2**

Run:

```bash
.venv/bin/python /Users/wuhaozhe/.codex/skills/pptx/scripts/office/unpack.py \
  '/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS克制图解版_v2_2026-07-23.pptx' \
  build/ppt/hkuds_image_deck_v3/unpacked
```

Expected: six files under `ppt/slides/slide1.xml` through `slide6.xml`.

### Task 2: Apply the uniform slide layout

**Files:**
- Modify: `build/ppt/hkuds_image_deck_v3/unpacked/ppt/slides/slide1.xml`
- Modify: `build/ppt/hkuds_image_deck_v3/unpacked/ppt/slides/slide2.xml`
- Modify: `build/ppt/hkuds_image_deck_v3/unpacked/ppt/slides/slide3.xml`
- Modify: `build/ppt/hkuds_image_deck_v3/unpacked/ppt/slides/slide4.xml`
- Modify: `build/ppt/hkuds_image_deck_v3/unpacked/ppt/slides/slide5.xml`
- Modify: `build/ppt/hkuds_image_deck_v3/unpacked/ppt/slides/slide6.xml`

- [ ] **Step 1: Shrink and center each body picture**

For the body picture `a:xfrm`, apply this exact geometry:

```xml
<a:off x="822960" y="987552"/>
<a:ext cx="7498080" cy="3260206"/>
```

Expected: 8.2-inch-wide image centered at x=0.9 inches, with original aspect ratio preserved.

- [ ] **Step 2: Reduce every title to 24pt**

Insert this run property before each title `<a:t>`:

```xml
<a:rPr lang="zh-CN" sz="2400" b="1"/>
```

Expected: all six slide titles remain in the existing title placeholder and inherit HKU red.

- [ ] **Step 3: Add one editable caption shape per slide**

Use shape IDs `5`, names `EDITABLE_CAPTION_01` through `EDITABLE_CAPTION_06`, and this contract:

```xml
<a:xfrm>
  <a:off x="594360" y="4462272"/>
  <a:ext cx="7955280" cy="274320"/>
</a:xfrm>
```

The text body must use `wrap="none"`, zero text insets, centered alignment, `PingFang SC`, 10.5pt, and `6B5743`. Insert the exact six captions from the approved design spec.

- [ ] **Step 4: Inspect all six XML files**

Run:

```bash
rg -n 'EDITABLE_CAPTION_|sz="2400"|x="822960" y="987552"|cx="7498080" cy="3260206"' \
  build/ppt/hkuds_image_deck_v3/unpacked/ppt/slides/slide*.xml
```

Expected: each marker appears once per slide; six captions are present.

### Task 3: Pack, verify, render, and deliver

**Files:**
- Create: `build/ppt/hkuds_image_deck_v3/Vibe-Trading_HKUDS克制图解版_v3_可编辑说明_2026-07-23.pptx`
- Create: `/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS克制图解版_v3_可编辑说明_2026-07-23.pptx`
- Create: `build/ppt/hkuds_image_deck_v3/preview/`

- [ ] **Step 1: Clean and pack**

Run:

```bash
.venv/bin/python /Users/wuhaozhe/.codex/skills/pptx/scripts/clean.py build/ppt/hkuds_image_deck_v3/unpacked
.venv/bin/python /Users/wuhaozhe/.codex/skills/pptx/scripts/office/pack.py \
  build/ppt/hkuds_image_deck_v3/unpacked \
  build/ppt/hkuds_image_deck_v3/Vibe-Trading_HKUDS克制图解版_v3_可编辑说明_2026-07-23.pptx \
  --original '/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS克制图解版_v2_2026-07-23.pptx'
```

Expected: pack succeeds and the output opens with six slides.

- [ ] **Step 2: Run structural and Office checks**

Verify with `python-pptx` that every slide has one picture, one `EDITABLE_CAPTION_*` shape, a 24pt title, and the approved caption text. Run Office validation and `unzip -tq`.

Expected: zero errors; embedded body-image hashes equal v2.

- [ ] **Step 3: Render and complete visual QA**

Convert v3 to PDF with LibreOffice, render all six pages at 180 DPI with `pdftoppm`, inspect every page, fix any title/caption collision or unreadable image, and re-render affected pages. Request independent visual QA after the local fix-and-verify cycle.

Expected: all titles, images, captions, logo, and red line are complete and projection-readable.

- [ ] **Step 4: Copy the verified deck to the delivery folder**

Copy only if the destination filename is absent, then compare build and delivery SHA-256 hashes.

Expected: both hashes match; v1, v2, `自制.pptx`, and the six-slide source deck hashes remain unchanged.

- [ ] **Step 5: Record session evidence**

Update `docs/2026-07-23_session03_hkuds_image_deck.md`, the project PPT memory, and a v3 delivery manifest with the final hashes and QA result.
