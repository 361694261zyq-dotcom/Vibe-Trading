# Vibe-Trading HKUDS Full-Feature Bilingual Deck — Design Specification

**Date:** 2026-07-23
**Status:** Approved for direct implementation by the user's instruction to start without further questions
**Deliverables:** one Chinese `.pptx` and one English `.pptx`, with one-to-one slide mapping

## 1. Objective

Create a comprehensive Vibe-Trading presentation that explains the complete product rather than centering only on the trust layer. The deck must reuse the current HKUDS presentation base: white canvas, official HKU bilingual logo, red header rule, restrained editorial illustration language, editable upper-left title, editable one-line caption, and detailed speaker notes.

The narrative is problem-led. Every major capability is presented as a complete problem-solving unit:

1. **Motivation** — why this capability is needed;
2. **Challenges** — what makes the problem hard;
3. **Solution** — how Vibe-Trading addresses the hard parts;
4. **Outcome** — what the user receives or can do next.

This requirement applies to every capability slide. The result must not read as a feature inventory.

## 2. Source of Truth and Content Policy

- Use the current local `README.md` and `README_zh.md` in this checkout as the primary public-product source.
- Use the checked-in project `AGENTS.md` only to resolve architecture and safety details already reflected in the product.
- Do not browse, pull, or substitute remote README content.
- Keep the public headline numbers used by the existing Chinese deck and the user's explicit direction:
  - 88 finance skills across 9 categories;
  - 462 alphas across 5 families;
  - 23 data sources;
  - 30 swarm presets;
  - 18 read-only data tools;
  - 8 backtest engines plus options portfolio;
  - 15 metrics, 5 optimizers, 3 validation tools;
  - 12 broker connectors;
  - 54 MCP tools;
  - 16 IM adapters.
- Do not mention paid data, premium data, marketplace credits, referral links, or QVeris anywhere in slide text, body images, captions, speaker notes, or PDF exports.
- Planned roadmap items must be visually and verbally separated from shipped functionality.
- Do not claim custody, execution-venue status, or unrestricted live trading.

## 3. Existing Files and Non-Destructive Rule

Use the following as read-only references:

- Short Chinese HKUDS deck: `Vibe-Trading_HKUDS_Presentation_CN_2026-07-23.pptx`
- Short English HKUDS deck: `Vibe-Trading_HKUDS_Presentation_EN_2026-07-23.pptx`
- Earlier Chinese full-feature master: `Vibe-Trading中文母版_全功能版_2026-07-22.pptx`
- User-provided template deck: `自制.pptx`

The new files are siblings; no existing presentation or source image is overwritten.

## 4. Output Names

- `Vibe-Trading_HKUDS_Full-Feature_Presentation_CN_2026-07-23.pptx`
- `Vibe-Trading_HKUDS_Full-Feature_Presentation_EN_2026-07-23.pptx`

Both files live in:

`/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/`

## 5. Slide Architecture

The deck contains 34 slides. Slides 1–4 establish the system-level story; slides 5–32 cover individual capability domains; slides 33–34 close with adoption and roadmap. Chinese and English slides use identical ordering and geometry.

| # | Chinese title | English title | Purpose |
|---|---|---|---|
| 1 | Vibe-Trading：把金融问题变成可运行研究 | Vibe-Trading: Turn Finance Questions into Runnable Research | Cover and project promise |
| 2 | 项目简介：为什么需要一体化研究工作站 | Project Overview: Why an Integrated Research Workspace | Project-level motivation, challenges, solution |
| 3 | 能力全景：每项能力都在解决一个具体问题 | Capability Map: Every Feature Solves a Specific Problem | Map the full product and explain the recurring lens |
| 4 | 研究闭环：从问题到可复查证据 | Research Loop: From Question to Inspectable Evidence | Plan → Ground → Execute → Validate → Deliver |
| 5 | Agent Runtime：让长任务连续、可控、可恢复 | Agent Runtime: Keep Long Tasks Coherent and Recoverable | ReAct, batching, compression, recovery |
| 6 | 金融技能库：把专业方法变成可复用流程 | Finance Skills: Turn Methods into Reusable Workflows | 88 skills, 9 categories |
| 7 | 记忆与会话检索：让研究不再每次从零开始 | Memory & Search: Stop Restarting Research from Zero | Persistent memory and SQLite FTS5 search |
| 8 | 自进化技能：把一次经验沉淀为长期能力 | Self-Evolving Skills: Convert Experience into Capability | Full skill CRUD and reusable procedures |
| 9 | Swarm：让多角色并行而不丢失共同上下文 | Swarms: Parallel Roles, Shared Context | 30 presets, DAG, streaming, retry |
| 10 | 假设注册表：先冻结命题，再开始实验 | Hypothesis Registry: Freeze the Claim Before the Experiment | Durable hypotheses and invalidation notes |
| 11 | Research Autopilot：把想法推进到可运行证据 | Research Autopilot: Move Ideas into Runnable Evidence | Hypothesis → deterministic backtest → report |
| 12 | 数据路由：一个请求，穿过 23 个数据入口 | Data Routing: One Request Across 23 Data Sources | Cross-market routing and ordered fallback |
| 13 | Data Bridge：把自有数据接入同一研究流程 | Data Bridge: Bring Private Data into the Same Workflow | Local CSV, Parquet, DuckDB, custom loaders |
| 14 | 深度数据工具：从行情扩展到基本面与资金流 | Deep Data Tools: Go Beyond OHLCV | 18 read-only fundamentals/flow tools |
| 15 | 文档、网页与视觉：把非结构化材料变成证据 | Documents, Web & Vision: Turn Unstructured Inputs into Evidence | Files, OCR, URL, chart-image analysis |
| 16 | 跨市场回测：统一入口，保留各市场真实规则 | Cross-Market Backtesting: One Interface, Real Market Rules | 8 engines, options portfolio, bar intervals |
| 17 | 验证与组合：不只看收益，还要检验稳健性 | Validation & Portfolio: Test Robustness, Not Just Return | Metrics, benchmarks, optimizers, validators |
| 18 | Alpha Zoo：把 462 个因子变成可比较实验 | Alpha Zoo: Make 462 Alphas Comparable | Five families and common bench interface |
| 19 | 因子研究：主动阻断前视偏差与样本内幻觉 | Factor Research: Block Look-Ahead and In-Sample Illusions | PIT, AST purity, strict OOS, compare |
| 20 | 相关性状态：识别市场何时“抱团” | Correlation Regimes: Detect When Markets Fuse | Edge density, hysteresis, descriptive risk context |
| 21 | 策略开发管理：让策略拥有可监控生命周期 | Strategy Development Manager: Monitor the Full Strategy Lifecycle | Register, status, decay scan, state lifecycle |
| 22 | 交易日志分析：把成交记录变成行为诊断 | Trade Journal: Turn Fills into Behavioral Diagnostics | Broker parsers and four behavior diagnostics |
| 23 | Shadow Account：用反事实路径检验交易规则 | Shadow Account: Test Rules with Counterfactual Paths | Extract, run, compare, report |
| 24 | 证据链：让每次运行都可复查、可比较、可追踪 | Evidence Chain: Make Every Run Inspectable and Comparable | Run cards, warnings, attribution, hashes |
| 25 | 研究产物：把结论交付成可继续使用的资产 | Research Artifacts: Deliver Assets That Can Keep Working | Reports, traces, Pine, TDX, MT5, later sessions |
| 26 | 定时研究：把一次对话升级为持续任务 | Scheduled Research: Turn One Conversation into a Continuing Job | Cron/interval, persistence, executor |
| 27 | 多渠道交付：把研究送进团队日常入口 | Multi-Channel Delivery: Put Research Where Teams Work | 16 IM adapters and shared runtime |
| 28 | 多端入口：同一内核服务 Web、CLI 与 REST | Product Surfaces: One Core for Web, CLI, and REST | Human and automation access paths |
| 29 | MCP Server：让外部 Agent 调用 54 个研究工具 | MCP Server: Expose 54 Research Tools to External Agents | Stdio/HTTP/SSE compatibility and safe tool boundary |
| 30 | MCP Client：让内置 Agent 安全调用外部工具 | MCP Client: Let the Built-In Agent Use External Tools Safely | Operator allowlist and stable wrapper names |
| 31 | 交易连接器：12 个通道，能力严格分层 | Broker Connectors: 12 Channels with Hard Capability Tiers | Read, paper, bounded-live tiers |
| 32 | 有边界的自主交易：在 mandate 内执行，在边界外停止 | Bounded Autonomy: Execute Inside a Mandate, Stop at the Boundary | Mandate, structural guard, kill switch, audit |
| 33 | 部署与接入：从本地安装到团队工作流 | Deployment: From Local Install to Team Workflow | Pip, Docker, local services, team entry points |
| 34 | 当前能力与路线图：已经交付什么，下一步是什么 | Shipped Now, Next on the Roadmap | Shipped/planned separation and closing |

## 6. Per-Slide Narrative Contract

Every capability slide uses four content zones inside the body image:

- **Motivation / 为什么需要** — one audience-facing problem statement;
- **Challenges / 难在哪里** — two or three concrete constraints;
- **Solution / 怎么解决** — two to four concrete mechanisms already present in the repository;
- **Outcome / 交付什么** — a short outcome strip describing the inspectable deliverable.

The slide title names the problem solved, not merely the module. A small source footer reads `Local README · v0.1.12 · 2026-07-23` or its Chinese equivalent. The footer is part of the body image and never contains a remote or paid-data reference.

## 7. Visual System

### 7.1 Baseboard

- Canvas: 16:9, 10 × 5.625 inches, inherited from the current HKUDS short deck.
- Background: white / warm white.
- Official HKU bilingual logo: inherited from the existing slide layout without alteration.
- Header rule: inherited red rule with existing accent segment.
- Title: upper-left, editable, dark HKU red, smaller than the earliest drafts, single line wherever possible.
- Caption: editable one-line text block under the image.

### 7.2 Body Image

- 1902 × 827 PNG, placed with the same geometry as the current short deck.
- Restrained editorial-infographic style:
  - dark brown line work;
  - muted sage;
  - dusty rose;
  - HKU red accents;
  - warm neutral cards and generous whitespace.
- Body labels are deterministically rendered from the bilingual content contract. This avoids hallucinated words, mistranslations, and unreadable generated text.
- Reuse the visual grammar of the existing short deck—rounded cards, thin connectors, simple node diagrams, restrained status capsules—but create new body images.
- Vary the internal diagram by capability: pipeline, lifecycle, matrix, tiers, constellation, stack, or comparison. The Motivation/Challenges/Solution/Outcome logic stays visible on every capability slide.

## 8. Bilingual Mapping

- Chinese and English decks have the same 34 slides, same body-image dimensions, same placements, and same notes-paragraph counts.
- English is written for an international technical/product audience, not word-for-word Chinese syntax.
- Chinese terminology favors audience-facing language over literal translations. Examples:
  - grounding → “证据接入” or “材料进入研究上下文,” not “取证” when that would sound legalistic;
  - links → “关联记录 / 运行关联,” not generic “链接” when the relation is semantic;
  - run card → “运行卡片 / 研究运行记录,” with the English term kept only where useful.
- Product and protocol names remain in English where that improves precision: Agent Runtime, Swarm, Alpha Zoo, MCP, Shadow Account, Data Bridge.

## 9. Speaker Notes

- Cover: two paragraphs.
- Slides 2–34: three paragraphs each.
- Paragraph 1 explains motivation, paragraph 2 explains the hard constraints, and paragraph 3 explains the Vibe-Trading mechanisms and resulting deliverable.
- Notes are detailed enough for roughly 45–75 seconds of speaking per slide.
- Notes use the same language as the deck and contain no paid-data references.

## 10. Verification Gates

1. 34 slides in both files; same ordering and language-neutral geometry.
2. Exact paired filenames; existing short decks remain byte-identical.
3. One body image, one native title, and one native editable caption per slide.
4. Speaker notes: 2 paragraphs on cover, 3 paragraphs elsewhere.
5. English native text and notes contain no CJK characters; the official HKU logo is the only bilingual graphic.
6. Forbidden-term scan across slide XML, notes XML, and image-source contract.
7. Required headline-number scan: 88, 462, 23, 30, 18, 8, 15, 5, 3, 12, 54, 16.
8. Office Open XML validation and ZIP integrity.
9. LibreOffice PDF render and full-resolution slide PNGs.
10. Programmatic image-bound checks and independent visual QA with blocker/major/minor classification.
11. Final revalidation of the previous English short deck alongside the new full-feature pair.
