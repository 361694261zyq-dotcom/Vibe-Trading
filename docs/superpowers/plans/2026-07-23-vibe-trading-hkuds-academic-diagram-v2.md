# Vibe-Trading HKUDS Full-Feature Academic-Diagram V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: implement this plan inline in the current task because the user requested direct execution and the project instructions prohibit worktree/subagent overhead for this artifact revision. Track each checkbox and verify after every generation batch.

**Goal:** Rebuild the 34-slide Chinese/English full-feature deck pair with six-slide-quality academic diagrams whose embedded labels and relationships make each slide understandable without its caption.

**Architecture:** A bilingual diagram contract supplies exact labels, layout archetypes, and prompts for 68 generated raster diagrams. A non-destructive deck builder clones the delivered 34-slide pair, replaces only the body-image relationship on every slide, and preserves the HKUDS baseboard, editable titles/captions, and notes. Programmatic checks and full slide renders validate structure, text policy, and visual readability.

**Tech Stack:** built-in `image_gen`; Node.js contract validation; Python 3 with `python-pptx`, Pillow, and lxml; Keynote/LibreOffice rendering; Poppler; Office Open XML validators.

---

### Task 1: Freeze the bilingual diagram contract

**Files:**

- Create: `build/ppt/full_feature_academic_v2_20260723/work/diagram_contract.js`
- Create: `build/ppt/full_feature_academic_v2_20260723/work/prompt_manifest.json`

- [ ] Encode all 34 diagram archetypes, exact CN/EN labels, required arrows, boundaries, facts, and negative constraints.
- [ ] Validate 34 unique keys, 6–14 labels per language, label-length limits, required headline numbers, and forbidden terms.
- [ ] Run `node build/ppt/full_feature_academic_v2_20260723/work/diagram_contract.js --check` and require a zero exit code with `slides: 34` and `images: 68`.

### Task 2: Establish the visual baseline with three representative slides

**Files:**

- Create: `build/ppt/full_feature_academic_v2_20260723/assets/en/slide_04.png`
- Create: `build/ppt/full_feature_academic_v2_20260723/assets/en/slide_12.png`
- Create: `build/ppt/full_feature_academic_v2_20260723/assets/en/slide_31.png`

- [ ] Generate slide 4 as a process loop, slide 12 as a routing lattice, and slide 31 as a capability-tier matrix using the exact shared style prompt.
- [ ] Normalize each output to 1902×827 without clipping labels.
- [ ] Inspect the three files at original resolution and reject any misspelling, pseudo-text, decorative character dominance, ambiguous arrow, or unreadable label.
- [ ] Run one targeted regeneration cycle on every rejected baseline image.

### Task 3: Generate and verify all English academic diagrams

**Files:**

- Create: `build/ppt/full_feature_academic_v2_20260723/assets/en/slide_01.png` through `slide_34.png`
- Create: `build/ppt/full_feature_academic_v2_20260723/work/generation_manifest_en.json`

- [ ] Generate one English image per slide with the slide-specific exact label list.
- [ ] Save every accepted built-in output inside the workspace; never leave a consumed asset only in the generated-images cache.
- [ ] Verify PNG dimensions, unique hashes, required label presence by visual review, and forbidden-term absence.
- [ ] Create four contact sheets and inspect all 34 images for five-second standalone comprehension.
- [ ] Regenerate every image with a blocker or major issue, then recreate the affected contact sheet.

### Task 4: Generate and verify all Chinese academic diagrams

**Files:**

- Create: `build/ppt/full_feature_academic_v2_20260723/assets/cn/slide_01.png` through `slide_34.png`
- Create: `build/ppt/full_feature_academic_v2_20260723/work/generation_manifest_cn.json`

- [ ] Generate one Chinese image per slide using concise audience-facing terminology and the same diagram geometry contract as English.
- [ ] Save every accepted image in the workspace and normalize to 1902×827.
- [ ] Visually inspect every Chinese label; regenerate mistranslations, malformed characters, pseudo-text, and ambiguous terminology.
- [ ] Create four Chinese contact sheets and run the same standalone-comprehension review as English.

### Task 5: Build the non-destructive CN/EN V2 deck pair

**Files:**

- Create: `build/ppt/full_feature_academic_v2_20260723/work/build_decks.py`
- Create: `build/ppt/full_feature_academic_v2_20260723/Vibe-Trading_HKUDS_Full-Feature_Academic-Diagram_CN_2026-07-23.pptx`
- Create: `build/ppt/full_feature_academic_v2_20260723/Vibe-Trading_HKUDS_Full-Feature_Academic-Diagram_EN_2026-07-23.pptx`

- [ ] Read the delivered 34-slide pair as immutable bases.
- [ ] Replace only each `BODY_ILLUSTRATION` image while preserving title, editable three-cell caption, logo, red rule, notes, masters, layouts, and geometry.
- [ ] Set package metadata to identify the academic-diagram V2 pair.
- [ ] Run `unzip -t` on both files and compare base/V2 slide counts, notes counts, shape names, and object geometry.

### Task 6: Render, bug-hunt, and repair

**Files:**

- Create: `build/ppt/full_feature_academic_v2_20260723/render/cn/slide-01.png` through `slide-34.png`
- Create: `build/ppt/full_feature_academic_v2_20260723/render/en/slide-01.png` through `slide-34.png`
- Create: `build/ppt/full_feature_academic_v2_20260723/verification_report.json`

- [ ] Render both files to full-resolution slide PNGs with Keynote or LibreOffice and Poppler.
- [ ] Inspect all slide renders for label scale, cropping, title collisions, logo/rule fidelity, and caption support role.
- [ ] Run the Office validator and content/forbidden-term checker.
- [ ] Complete at least one fix-and-rerender cycle and recheck affected slides.
- [ ] Verify that both existing 34-slide files and both six-slide files remain byte-identical to their recorded SHA-256 hashes.

### Task 7: Deliver and record the new pair

**Files:**

- Copy to: `/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS_Full-Feature_Academic-Diagram_CN_2026-07-23.pptx`
- Copy to: `/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS_Full-Feature_Academic-Diagram_EN_2026-07-23.pptx`
- Create: `docs/2026-07-23_session05_hkuds_academic_diagram_v2.md`

- [ ] Copy only final verified V2 files to the user folder.
- [ ] Record output hashes, slide counts, image counts, notes counts, QA findings, unchanged-source hashes, and evidence paths.
- [ ] Run git hygiene, commit only the spec/plan/session documentation locally, and do not push.
