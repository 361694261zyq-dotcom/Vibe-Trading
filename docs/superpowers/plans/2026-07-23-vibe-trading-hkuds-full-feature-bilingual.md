# Vibe-Trading HKUDS Full-Feature Bilingual Deck — Implementation Plan

**Goal:** Deliver a 34-slide Chinese/English HKUDS presentation pair in which every capability is explained through Motivation → Challenges → Solution → Outcome, using the current local README and the existing HKU baseboard.

**Architecture:** A single bilingual content contract drives bespoke 1902×827 image-generation illustrations, editable Motivation/Challenges/Solution caption strips, a template-based PowerPoint builder, speaker notes, and pair verification. The builder starts from the current HKUDS short deck so the official logo and header rule remain inherited layout objects. Existing user files are read-only.

**Runtime:** Built-in image generation for bespoke text-free illustrations; Python 3.12 + python-pptx/lxml for template-based deck assembly and verification; LibreOffice + Poppler for rendering; existing `pptx` skill validators for Office Open XML checks.

## Task 1: Freeze the bilingual content contract

**Files**

- Create: `build/ppt/full_feature_hkuds_20260723/work/content_contract.js`
- Create: `build/ppt/full_feature_hkuds_20260723/work/facts_snapshot.json`

**Actions**

1. Encode all 34 slide titles, captions, Motivation, Challenges, Solution, Outcome, facts, visual layout kind, and source tag in one contract.
2. Encode Chinese and English speaker notes as two paragraphs on slide 1 and three paragraphs on slides 2–34.
3. Include all required current numbers and exclude every paid-data reference.
4. Add a contract self-check for slide count, bilingual field completeness, note counts, forbidden terms, and matching keys.

**Verification**

```bash
NODE_PATH="$BUNDLED_NODE_MODULES" node build/ppt/full_feature_hkuds_20260723/work/content_contract.js --check
```

## Task 2: Generate bespoke short-deck-quality body illustrations

**Files**

- Create: `build/ppt/full_feature_hkuds_20260723/work/image_prompt_manifest.json`
- Create: `build/ppt/full_feature_hkuds_20260723/assets/illustrations/slide_01.png` through `slide_34.png`
- Create: `build/ppt/full_feature_hkuds_20260723/assets/image_generation_manifest.json`

**Actions**

1. Use the polished six-slide deck images as style references.
2. Generate one bespoke 1902×827 illustration per slide using a restrained warm-white/dark-brown/sage/dusty-rose/HKU-red palette.
3. Communicate Motivation → Challenges → Solution through one integrated scene, not a repeated panel template.
4. Generate no text, numbers, logo, watermark, or fabricated interface copy inside the image.
5. Inspect every result for subject accuracy, composition, accidental text, and consistency before deck assembly.

**Verification**

```bash
file build/ppt/full_feature_hkuds_20260723/assets/illustrations/slide_*.png
sips -g pixelWidth -g pixelHeight build/ppt/full_feature_hkuds_20260723/assets/illustrations/slide_*.png
```

## Task 3: Build both PowerPoint files from the HKUDS template

**Files**

- Create: `build/ppt/full_feature_hkuds_20260723/work/build_decks.py`
- Create: `build/ppt/full_feature_hkuds_20260723/Vibe-Trading_HKUDS_Full-Feature_Presentation_CN_2026-07-23.pptx`
- Create: `build/ppt/full_feature_hkuds_20260723/Vibe-Trading_HKUDS_Full-Feature_Presentation_EN_2026-07-23.pptx`

**Actions**

1. Open the current Chinese short deck as the immutable template.
2. Remove its six content slides while retaining slide masters, layouts, theme, and HKU logo asset.
3. Add 34 slides from the HKUDS content layout.
4. Add one body illustration, one editable upper-left title, and one editable Motivation/Challenges/Solution caption to each slide.
5. Add bilingual speaker notes with the required paragraph counts.
6. Set metadata and stable shape names for later verification.

**Verification**

```bash
python3 build/ppt/full_feature_hkuds_20260723/work/build_decks.py
unzip -t build/ppt/full_feature_hkuds_20260723/*.pptx
```

## Task 4: Verify language, geometry, content, and template preservation

**Files**

- Create: `build/ppt/full_feature_hkuds_20260723/work/verify_decks.py`
- Create: `build/ppt/full_feature_hkuds_20260723/verification.json`

**Actions**

1. Verify 34 slides and one-to-one Chinese/English ordering.
2. Verify paired filenames differ only by `_CN_` / `_EN_`.
3. Verify identical slide-level object geometry across languages.
4. Verify title, caption, body image, and notes on every slide.
5. Scan native slide text, notes, contract, and image metadata for forbidden terms.
6. Verify required facts and shipped/planned status language.
7. Verify the existing short English deck remains unchanged and still passes its pair checker.

**Verification**

```bash
python3 build/ppt/full_feature_hkuds_20260723/work/verify_decks.py
python3 /Users/wuhaozhe/.codex/skills/pptx/scripts/office/validate.py build/ppt/full_feature_hkuds_20260723/*.pptx
```

## Task 5: Render and visually inspect all slides

**Files**

- Create: `build/ppt/full_feature_hkuds_20260723/preview/cn/*.png`
- Create: `build/ppt/full_feature_hkuds_20260723/preview/en/*.png`
- Create: `build/ppt/full_feature_hkuds_20260723/preview/*/contact-sheet-*.png`

**Actions**

1. Render both decks to PDF with LibreOffice and to full-resolution PNGs with Poppler.
2. Generate paginated contact sheets.
3. Inspect titles, logo, red rule, image bounds, caption line, text density, and bilingual pairing.
4. Run independent visual QA through the existing presentation QA agent.
5. Fix blockers and majors, then repeat render and verification until clear.

## Task 6: Deliver non-destructively and close the session

**Files**

- Copy to: `/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS_Full-Feature_Presentation_CN_2026-07-23.pptx`
- Copy to: `/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS_Full-Feature_Presentation_EN_2026-07-23.pptx`
- Create: `docs/2026-07-23_session04_hkuds_full_feature_bilingual_deck.md`
- Update: project memory with output paths and verification status

**Actions**

1. Copy only the final verified files into the user folder.
2. Confirm the short CN/EN pair is still present and unchanged.
3. Record SHA-256 hashes, slide counts, QA results, and evidence paths.
4. Check branch, worktree, untracked files, and staged scope.
5. Commit only the session documentation and memory update. Do not push.
