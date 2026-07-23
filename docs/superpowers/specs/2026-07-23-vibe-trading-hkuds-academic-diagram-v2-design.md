# Vibe-Trading HKUDS Full-Feature Academic-Diagram V2 — Design Specification

**Date:** 2026-07-23
**Status:** Approved by the user's explicit request for six-slide-quality academic illustrations and direct execution without further questions
**Source decks:** the delivered 34-slide CN/EN pair; both remain immutable

## 1. Problem Diagnosis

The delivered 34-slide pair is structurally correct but visually under-informative. Its body images are mostly language-neutral editorial scenes. They suggest a concept, but a viewer cannot reliably infer the module architecture, the hard constraint, the mechanism, and the outcome without reading the editable caption or speaker notes.

The six-slide HKUDS pair demonstrates the required quality floor:

- `build/ppt/hkuds_bilingual_pair/preview/en_delivery/slide-3.png`
- `build/ppt/hkuds_bilingual_pair/preview/en_delivery/slide-4.png`
- `build/ppt/hkuds_bilingual_pair/preview/en_delivery/slide-5.png`

Those slides use academic information-graphic structure: named zones, explicit arrows, short labels, architectural boundaries, comparison logic, and a visible outcome. The new 34-slide pair must use the same communication model.

## 2. Chosen Approach

Three approaches were evaluated:

1. **Continue with language-neutral illustrations.** This preserves reuse across languages but does not solve the user's complaint. Rejected.
2. **Build all diagrams as native PowerPoint vectors.** This gives perfect text accuracy and editability, but loses the hand-drawn academic-illustration character of the six-slide version and would read as a generic consulting deck. Rejected.
3. **Generate language-specific academic diagrams with embedded text.** This best matches the six-slide visual standard. Chinese and English each receive a dedicated image, while the existing editable caption remains supplementary. Selected.

## 3. Deliverables and Non-Destructive Rule

Create two new sibling files in `/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/`:

- `Vibe-Trading_HKUDS_Full-Feature_Academic-Diagram_CN_2026-07-23.pptx`
- `Vibe-Trading_HKUDS_Full-Feature_Academic-Diagram_EN_2026-07-23.pptx`

Do not overwrite the existing six-slide decks, the existing 34-slide pair, or any source images. Preserve the 34-slide order, HKUDS/HKU white baseboard, official logo, red header rule, editable titles, editable three-cell captions, and speaker notes.

## 4. Diagram Readability Contract

Every body image must be understandable when cropped out of the slide and viewed without the title, caption, or speaker notes.

Each image must contain:

- a named problem or input zone;
- at least one explicit hard constraint, boundary, or failure mode;
- a visible mechanism with directional arrows;
- a named output, evidence object, or operating result;
- 6–14 short labels in the deck language;
- no paragraph text, decorative prose, watermark, logo, or fabricated product UI.

The editable bottom caption remains one line with Motivation / Challenge / Solution. It summarizes the diagram but must not supply information that is missing from the diagram.

## 5. Visual Grammar

- Wide 1902×827 body image, warm-white paper, dark-brown hand-drawn linework.
- Muted sage for verified / safe / active states; dusty rose and HKU red for risk, breaks, and blocked paths.
- Rounded technical frames, thin connectors, simple icons, compact uppercase English or concise Chinese labels.
- Academic poster composition rather than narrative character illustration.
- Use only a small number of people when a human role is essential; people cannot be the main explanatory device.
- Use varied diagram archetypes: pipeline, comparison, lifecycle, layered architecture, routing lattice, matrix, state machine, DAG, evidence lineage, topology, and roadmap.
- Keep all critical labels at least 90 px from image edges and large enough to survive placement at 8.2×3.58 inches.

## 6. Slide-by-Slide Diagram Archetypes

| # | Capability | Diagram archetype | Required visible logic |
|---|---|---|---|
| 1 | System promise | End-to-end research pipeline | Question → Data & Tools → Agent Research → Backtest & Validate → Evidence Package |
| 2 | Project overview | Fragmented-vs-integrated comparison | Disconnected tools on the left; one shared workspace and traceable output on the right |
| 3 | Capability map | Four-layer system map | Research Intelligence, Data & Validation, Delivery & Integration, Safety & Execution |
| 4 | Research loop | Closed loop | Plan → Ground → Execute → Validate → Deliver → Revise |
| 5 | Agent Runtime | Runtime architecture | Task state, ReAct loop, tool batch, context compression, checkpoint recovery |
| 6 | Finance Skills | Indexed method library | 88 Skills / 9 Categories → Select Method → Execute Workflow → Reuse |
| 7 | Memory & Search | Retrieval pipeline | Prior Sessions → FTS5 Search → Relevant Evidence → Continue Research |
| 8 | Self-Evolving Skills | Skill lifecycle | Experience → Extract Procedure → Save / Patch / Delete → Reuse → Feedback |
| 9 | Swarms | Shared-context DAG | Planner → specialist roles in parallel → reviewer → unified report; 30 presets |
| 10 | Hypothesis Registry | Pre-registration gate | Claim + Universe + Metric + Invalidation → Frozen Hypothesis → Experiment |
| 11 | Research Autopilot | Deterministic loop | Idea → Signal Scaffold → Linked Backtest → Evidence → Revise |
| 12 | Data Routing | Fallback lattice | One request → Market Router → 23 Data Sources → Sanitized Bars; ordered fallback |
| 13 | Data Bridge | Adapter architecture | CSV / Parquet / DuckDB / Custom Loader → Common Schema → Same Research Tools |
| 14 | Deep Data | Evidence matrix | Price + Fundamentals + Flows + Filings + Macro → 18 Read-Only Tools → Research Context |
| 15 | Documents / Web / Vision | Multimodal ingestion | PDF / DOCX / XLSX / PPTX / URL / Chart → OCR & Parsing → Cited Evidence |
| 16 | Cross-Market Backtest | Engine selection matrix | Common Strategy API → 8 Engines + Options → Market Rules → Comparable Results |
| 17 | Validation & Portfolio | Validation gauntlet | 15 Metrics + Benchmark → 5 Optimizers → Monte Carlo / Bootstrap / Walk-Forward |
| 18 | Alpha Zoo | Taxonomy and benchmark | 462 Alphas / 5 Families → Common Bench → Ranked Comparison |
| 19 | Factor Research | Leakage barriers | PIT Data → Purity Gate → Strict OOS → Random Control → Trustworthy Rank |
| 20 | Correlation Regimes | Regime state graph | Sparse → Building → Fused → Cooling with edge density and hysteresis |
| 21 | Strategy Manager | Lifecycle state machine | Register → Active → Monitoring → Decayed → Disabled with IC / Sharpe checks |
| 22 | Trade Journal | ETL and diagnostics | Broker CSV → Normalize → Behavior Diagnostics → Trader Profile → Testable Hypotheses |
| 23 | Shadow Account | Counterfactual twin paths | Actual Trades vs Rule-Based Shadow under Same Market → Compare → Rule Impact |
| 24 | Evidence Chain | Lineage graph | Config + Data + Strategy + Trades + Metrics + Warnings → Run Card → Reproduce |
| 25 | Research Artifacts | Artifact fan-out | One Verified Run → Report / Code / Pine / TDX / MT5 / Next Session |
| 26 | Scheduled Research | Persistent scheduler loop | Cron / Interval → Due Job → Runtime → Evidence Snapshot → Next Run |
| 27 | Multi-Channel Delivery | Hub-and-spoke topology | Shared Runtime → 16 IM Adapters → Teams receive the same evidence |
| 28 | Product Surfaces | Shared-core architecture | Web / CLI / REST → One Session Runtime → Same Run Record |
| 29 | MCP Server | External-agent boundary | External Agents → MCP Server → 54 Research Tools; order actions outside boundary |
| 30 | MCP Client | Allowlisted tool gateway | Built-In Agent → Operator Allowlist → Stable Tool Names → External Services |
| 31 | Broker Connectors | Capability-tier matrix | 12 channels organized under Read-Only / Paper / Bounded Live with hard refusal |
| 32 | Bounded Autonomy | Mandate boundary | User Mandate → Pre-Trade Gate → Broker Execution; breach → stop; kill switch + audit |
| 33 | Deployment | Deployment topology | pip / Docker → Local Runtime → Web / CLI / REST / MCP → Team Workflow |
| 34 | Roadmap | Status-lane roadmap | Shipped Now / Staged Next / Future Direction with visually different node states |

## 7. Bilingual Text Rules

- Generate an English and a Chinese image for every slide; do not reuse one language image in the other deck.
- Use audience-facing Chinese, not literal translations. Keep established technical terms where clearer: Agent Runtime, ReAct, Swarm, Alpha Zoo, MCP, Shadow Account, Data Bridge, FTS5, PIT, OOS.
- In-image labels are short noun phrases or verbs; no label exceeds 22 Chinese characters or 34 English characters.
- Exact numbers from the frozen local README may appear in images: 88, 9, 462, 5, 23, 30, 18, 8, 15, 5, 3, 12, 54, 16.
- Do not include QVeris, paid, premium, marketplace, referral, or Chinese equivalents anywhere.

## 8. Quality Gates

1. Both decks contain 34 slides with one-to-one ordering and identical geometry.
2. All 68 body images are unique and language-correct.
3. Every cropped body image passes a five-second comprehension check: capability, flow, boundary, and output are inferable without the caption.
4. In-image text is checked visually and against the prompt contract; misspelled or hallucinated labels trigger regeneration.
5. No critical label is cropped, unreadably small, or hidden by the slide title/caption.
6. Existing 34-slide and six-slide deck hashes remain unchanged.
7. Speaker notes and editable captions remain present and language-matched.
8. Office XML, ZIP integrity, forbidden-term scans, full renders, contact-sheet review, and one fix-and-rerender cycle pass before delivery.
