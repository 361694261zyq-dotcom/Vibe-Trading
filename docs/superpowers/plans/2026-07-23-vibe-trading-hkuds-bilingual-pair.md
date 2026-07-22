# Vibe-Trading HKUDS Bilingual Pair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the user-final Chinese deck and create a matching English deck with regenerated English body images, translated editable captions, and translated speaker notes.

**Architecture:** Treat the user-final Chinese PPTX as immutable content input. Extract and localize each body image independently with built-in `image_gen`, then unpack a copy of the Chinese PPTX, replace only the six body-image media files and all non-brand text, and repack it as the English deck. Rename the Chinese deck only at the final delivery step so both outputs share the same filename base.

**Tech Stack:** Office Open XML, PPTX skill unpack/clean/pack scripts, built-in `image_gen`, `apply_patch`, `python-pptx` read-only verification, LibreOffice, Poppler.

---

### Task 1: Freeze the user-final Chinese source and translation contract

**Files:**
- Read: `/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS中文介绍_演讲版_2026-07-23.pptx`
- Create: `build/ppt/hkuds_bilingual_pair/work/content_en.py`
- Create: `build/ppt/hkuds_bilingual_pair/assets/source_cn/slide_01.png` through `slide_06.png`

- [ ] **Step 1: Verify the source hash and structure**

Run SHA-256 and `python-pptx` checks. Expected hash: `8e4eef02bc9599f3ed2237c9306e891dd8550adb67162c5fd222f82e0b740852`; expected slides: 6; expected captions: `EDITABLE_CAPTION_01..06`; expected notes paragraphs: `[2,3,3,3,3,3]`.

- [ ] **Step 2: Write the English content contract**

Create `content_en.py` with immutable tuples for six titles, six captions, the translated speaker-note paragraphs, and exact per-image English labels. The titles and captions must exactly match `docs/superpowers/specs/2026-07-23-vibe-trading-hkuds-bilingual-pair-design.md`.

- [ ] **Step 3: Extract the six embedded body images**

Use `python-pptx` read-only access to write each picture blob to `assets/source_cn/slide_0N.png`. Verify each extracted hash equals the picture hash in the source presentation.

### Task 2: Regenerate six English body images

**Files:**
- Read: `build/ppt/hkuds_bilingual_pair/assets/source_cn/slide_01.png` through `slide_06.png`
- Create: `build/ppt/hkuds_bilingual_pair/assets/english/slide_01.png` through `slide_06.png`
- Create: `build/ppt/hkuds_bilingual_pair/prompts/prompt_manifest.json`

- [ ] **Step 1: Inspect every edit target**

Load each source image with `view_image` at original detail before calling `image_gen`.

- [ ] **Step 2: Localize one slide image at a time**

For each image, call built-in `image_gen` with use case `text-localization`. State: change only text; preserve canvas ratio, composition, panels, icons, arrows, statistics, colors, line weight, whitespace, and object positions. Supply every required English label verbatim and prohibit extra text or Chinese content.

- [ ] **Step 3: Persist and verify each English image**

Copy the selected output from `$CODEX_HOME/generated_images/...` into `assets/english/slide_0N.png`. Verify dimensions are approximately 1902 × 827 and inspect the English spelling, module count, arrows, crop, and remaining Chinese. Regenerate the whole affected image when a blocking issue is found; never overlay local text.

### Task 3: Build the English PPTX without changing layout

**Files:**
- Create: `build/ppt/hkuds_bilingual_pair/unpacked_en/`
- Modify: `build/ppt/hkuds_bilingual_pair/unpacked_en/ppt/slides/slide1.xml` through `slide6.xml`
- Modify: `build/ppt/hkuds_bilingual_pair/unpacked_en/ppt/notesSlides/notesSlide*.xml`
- Replace: the six body-image media files resolved through slide relationships
- Create: `build/ppt/hkuds_bilingual_pair/Vibe-Trading_HKUDS_Presentation_EN_2026-07-23.pptx`

- [ ] **Step 1: Unpack a copy of the user-final Chinese deck**

Run the PPTX skill `office/unpack.py` into `unpacked_en/`. Map each slide picture relationship to its media filename and each slide to its notes-slide relationship.

- [ ] **Step 2: Replace only localizable content**

Use `apply_patch` to replace the six slide titles, six caption texts, and all notes paragraphs with their English contract values. Copy the six regenerated English images over the mapped body-image media files. Do not touch the HKU layout image, master, theme, geometry, shape IDs, relationships, or speaker-note paragraph counts.

- [ ] **Step 3: Clean and pack**

Run `clean.py`, then `office/pack.py --original <Chinese source>` to create the build English PPTX. Expected: `All validations PASSED!`.

### Task 4: Verify, deliver, and standardize both filenames

**Files:**
- Create: `build/ppt/hkuds_bilingual_pair/work/verify_pair.py`
- Create: `build/ppt/hkuds_bilingual_pair/preview/en/`
- Create: `/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS_Presentation_EN_2026-07-23.pptx`
- Rename: `/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS中文介绍_演讲版_2026-07-23.pptx` to `/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS_Presentation_CN_2026-07-23.pptx`

- [ ] **Step 1: Run structural and translation checks**

Verify both decks contain 6 slides; English titles/captions/notes equal the content contract; English notes paragraph counts are `[2,3,3,3,3,3]`; each English slide has one body picture and one caption; shape geometry, layout, HKU brand hashes, and slide relationships match the Chinese source.

- [ ] **Step 2: Render and inspect the English deck**

Convert to PDF with LibreOffice and render all six slides at 180 DPI. Inspect all pages for Chinese content outside the locked HKU brand, spelling errors, missing labels, changed module counts, crop, overlap, and title/caption overflow. Complete at least one fix-and-reverify cycle, then request independent visual QA.

- [ ] **Step 3: Deliver both matching files**

Copy the verified English build to the EN destination only if absent. Rename the Chinese source to the CN destination only if absent. Confirm the Chinese hash remains `8e4eef02bc9599f3ed2237c9306e891dd8550adb67162c5fd222f82e0b740852` after renaming and verify both Office packages and ZIP integrity.

- [ ] **Step 4: Record final evidence**

Create a delivery manifest, update `docs/2026-07-23_session03_hkuds_image_deck.md`, and update Claude/Codex PPT memory with both final paths, hashes, image-generation provenance, and QA results.
