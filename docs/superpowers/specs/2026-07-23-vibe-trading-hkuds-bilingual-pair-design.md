# Vibe-Trading HKUDS 中英文配对演讲版设计

## 目标

以用户最终修改版为唯一内容基线，保留一份中文演讲版，并生成一份纯英文演讲版。两份 PPTX 使用完全一致的文件名基底，只通过 `CN`／`EN` 区分语言。

## 用户批准与边界

- 所有页面内容、图片信息、可编辑说明和演讲者备注均需完整翻译，不删减、不扩写。
- 六张正文图重新生成英文版本；保持原有构图、模块数量、箭头、图标、配色、留白和信息层级。
- HKU 官方双语校徽／校名属于锁定品牌资产，保持原样；除此之外，英文版不得保留中文内容文字。
- 中文版与英文版同时保存，互不覆盖。

## 标准文件名

- 中文：`Vibe-Trading_HKUDS_Presentation_CN_2026-07-23.pptx`
- 英文：`Vibe-Trading_HKUDS_Presentation_EN_2026-07-23.pptx`

## 只读内容基线

- 当前中文最终版：`/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS中文介绍_演讲版_2026-07-23.pptx`
- SHA-256：`8e4eef02bc9599f3ed2237c9306e891dd8550adb67162c5fd222f82e0b740852`
- 6 页；每页 1 张正文图和 1 个 `EDITABLE_CAPTION_*` 原生文本框。
- 演讲者备注段落数为 `[2, 3, 3, 3, 3, 3]`；英文版必须保持同一段落结构。

## 英文版页面标题

1. `Vibe-Trading`
2. `Project Overview`
3. `Motivation: Why It Matters`
4. `Challenges: Why It Is Hard`
5. `Solution: From Question to Reproducible Research`
6. `Research Delivery: From Answers to Complete Evidence`

## 英文版可编辑说明

1. `Starting with a natural-language question, the system organizes data, tools, and collaboration into traceable research.`
2. `From research input to agent execution and evidence delivery, every step runs in one unified workflow.`
3. `What matters is not a plausible-sounding answer, but a research process that can be inspected, reproduced, and reused.`
4. `Data, collaboration, validation, and execution boundaries must stay consistent; one broken link can change the conclusion.`
5. `The system understands the question, calls tools, coordinates research roles, and preserves the full process and results.`
6. `Each study delivers run records, performance metrics, trade details, and risk warnings—not just an answer.`

## 图像本地化方案

采用内置 `image_gen` 的 `text-localization` 编辑流程，每张中文正文图作为独立 edit target：

- 只把图内中文替换为锁定的英文标签；已有英文词保持一致。
- 不增加、删除或移动模块、图标、卡片、箭头、流程节点与统计数字。
- 保持约 1902 × 827、2.30:1 横向比例和暖白／深棕／橄榄绿／灰粉／HKU 红配色。
- 每张图生成后检查英文拼写、遗漏中文、模块数量、箭头方向、裁切与比例；发现问题只针对该张图完整重生。

## 原生文本与备注

- 复制用户最终修改版作为英文容器，保持 slide master、layout、HKU 品牌、图片几何位置、标题位置、说明文本框位置与样式。
- 标题和 `EDITABLE_CAPTION_*` 只替换文本，不改变 shape 几何和格式。
- 演讲者备注忠实翻译为自然、专业英文；保持原段落数量和信息顺序，不新增事实或数字。

## 验证合同

- 中英文各 6 页，文件名基底一致。
- 英文版每页恰好 1 张英文正文图、1 个可编辑说明框和 1 个 notes slide。
- 英文版标题／说明／备注与锁定英文内容一致；备注段落数为 `[2, 3, 3, 3, 3, 3]`。
- 除锁定 HKU 官方品牌图外，英文版原生文本与正文图不得出现中文内容文字。
- 两版均通过 Office Open XML、ZIP 与 LibreOffice 渲染；英文版完成独立视觉 QA。
- 中文用户最终版在生成英文版过程中保持内容哈希不变；只在最终一步做标准化同基名重命名。

## 范围外

- 不刷新项目数据，不修改当前叙事与页数。
- 不将图片内文字改造成原生文本框。
- 不修改 HKU 官方品牌资产。
