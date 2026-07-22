# Session 04 — HKUDS 全功能双语演示文稿

日期：2026-07-23
状态：本地交付与最终独立视觉复核均完成（PASS）
分支：`main`（本 session 未 pull / push）

## 本 session 完成内容

- 保持用户最终六页中英文短版只读，另行生成 34 页全功能中文、英文演示文稿。
- 内容事实基线来自当前 checkout 的本地 `README.md`（v0.1.12），重点覆盖 88 个金融技能、462 个因子、23 个数据入口、30 个 Swarm presets、8 个回测引擎、18 类深度只读数据、54 个 MCP 工具、12 个交易连接器等当前能力。
- 每个能力域都按 Motivation / Challenges / Solution 展开，Outcome 与关键事实进入原生 speaker notes。
- 34 页复用真实 HKUDS / HKU 白底底板、官方 Logo 与红线；每页正文使用一张独立、无可读文字的生成式信息图。
- 每页底部使用一个原生可编辑的三栏信息带，分别承载 Motivation、Challenge、Solution。102 个子句均为人工收束的完整短句，不使用省略号，也不依赖自动截断。
- 根据第一次独立视觉 QA 重做五页：
  - 第 17 页：加强投影环境下的线条对比；
  - 第 20 页：把右侧图表与人物收回安全边距；
  - 第 23 页：改为实际交易路径与规则化影子路径的反事实对照；
  - 第 31 页：把 12 个交易通道明确组织为只读、模拟、受限实盘三层硬门；
  - 第 34 页：用实体里程碑、阶段边界与淡化未来节点明确区分已交付、分阶段与下一步。
- 封面标题提升一级，其余左上标题继续保持克制小字号。
- 中文和英文各自包含 34 张正文图、34 个可编辑标题、34 个可编辑三栏信息带和完整原生演讲者备注。
- 所有原生英文正文无 CJK；HKU 官方 Logo 中的中英文校名按模板保留。
- 不出现 QVeris、付费、premium、marketplace、referral 等表述；数据入口只写为 23 Data Sources / 23 个数据入口。

## 最终交付文件

- 中文：`/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS_Full-Feature_Presentation_CN_2026-07-23.pptx`
  - SHA-256：`d69a4b0f2dfc8f003de0fed83d71a091bbdf6a7c03cf39266fb988983ba0f27d`
- 英文：`/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS_Full-Feature_Presentation_EN_2026-07-23.pptx`
  - SHA-256：`b25883686c227eeca2898dea126e87df32962ca2614a4f2f9e8f09316eff4c56`

## 保持不变的六页短版

- 中文：`Vibe-Trading_HKUDS_Presentation_CN_2026-07-23.pptx`
  - SHA-256：`a62a4fa5ee4f00d9a9d0cafdd04d3920e0412a8b06256493c2dc0507bdf5dbb7`
- 英文：`Vibe-Trading_HKUDS_Presentation_EN_2026-07-23.pptx`
  - SHA-256：`954b96aa9430207c2641e14034f5c58d31fa0fc2d08ba2cfe404acda14bdc589`

## 验证证据

- `content_contract.js --check`：34 页、双语字段、三栏短句长度、禁用词和事实约束通过。
- `verify_decks.py`：
  - 两版均为 34 页、34 张独立插画；
  - 标题、正文图、底栏几何一致；
  - 每页 notes 与合同完全一致；
  - 中文 notes 2–3 段，英文 notes 2–3 段；
  - Desktop 副本与构建件哈希一致；
  - 原六页短版哈希未变化；
  - ZIP / Open XML 全部可解析。
- Office Open XML validator：中英文两版均 `All validations PASSED!`。
- 英文使用 LibreOffice 实渲 34 页；中文使用 Keynote 14.4 实渲 34 页。逐页 contact sheet 检查未见标题碰撞、正文裁切、中文缺字、底栏换行或乱码。
- 最终渲染证据：`build/ppt/full_feature_hkuds_20260723/render_v4_review/`（ignored build artifact）。
- 第一次独立 QA 的 major 问题（底栏省略号、第 23 页语义偏移、第 31 页分层不清、第 34 页路线图不清）已逐项修复；最终独立视觉 QA 为 PASS（0 blocker / 0 major）。复核后又将中文第 32 页改为“有边界的自主交易”语义并用 Keynote 重渲，版面与底栏均无溢出。
- 最终包级扫描：两版均为 34 页；禁用词命中 0；中英文省略号命中 0；六页短版哈希保持不变。

## 下个 session

- 根据具体受众（投资人、研究者、开发者、课程汇报）从 34 页全功能版只读派生受众版，调整页序和详略，不回改本次交付。
- 对外发布前，如果本地 README 或版本号已更新，重新冻结事实快照并重建数据页与路线图页。

## 堵塞项与时机

- 当前无交付堵塞。
- 远端分支落后 `origin/main` 2 个 commit；本任务按用户指定使用本地未 push README，不应在本 session pull 或 push。

## 下个 session 可直接粘贴的 prompt

> 从 `/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS_Full-Feature_Presentation_CN_2026-07-23.pptx` 和对应 EN 版只读派生一套面向【填写受众】的演示稿。保持 HKUDS 底板、Logo、红线、正文插画与可编辑三栏底注风格；按该受众重排内容、压缩或展开页面，并保留原生 speaker notes。不要覆盖 34 页全功能版，也不要出现 QVeris 或付费相关表述。开始前先核对本地 README 是否有新事实。
