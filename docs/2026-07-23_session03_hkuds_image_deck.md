# 2026-07-23 Session 03 — Vibe-Trading HKUDS 克制图解版

## 目标

使用用户 `自制.pptx` 第 3 页的 HKUDS／香港大学底板，结合自制稿和现有六页中文短版，制作一份新的六页中文 PPT。底板只修改左上页题；每页正文只嵌入一张由 `image_gen` 完整生成的图解图片，包括图形与全部文字。

## 用户锁定要求

- 第 3 页是唯一视觉底板。
- 保留白底、港大校徽／校名和红线。
- 正文参考用户提供图片的克制、细线、低饱和系统图风格。
- 正文里的中文、数字和英文全部由图片模型生成；不在本地排字、覆盖或修字。
- 若图中文字或构图需要修复，只重新生成整张图。
- 来源 PPTX 与参考图只读；最终另存新文件。

## 只读来源

- `自制.pptx` SHA-256：`b748caced3f5cca5df2118f24a8ee3345f1bc9ca05e4f5e6f3b63a9b03f47215`
- 现有六页短版 SHA-256：`88b7c7878aa2dc9b2beda6b1b38ec3175233d7fe4bafb88307f7bbdf29295f6c`
- 用户风格参考图 SHA-256：`ea3371f78d6c603b4502d9c9512955251dd1ba67690a4cd012a1a5f7e30fc0e0`

## 计划交付

- `/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS克制图解版_2026-07-23.pptx`

## 进度

- [x] 审阅三份来源与 HKUDS layout。
- [x] 用户确认“保留底板 + 正文单图”方向。
- [x] 用户确认正文全部文字由图片模型生成。
- [x] 写入并提交设计规格与实施计划。
- [x] 建立来源、标题和提示词合同。
- [x] 生成六张正文图。
- [x] 组装六页 HKUDS PPTX。
- [x] 完成结构、Office、ZIP 与来源哈希验证。
- [x] 完成渲染、独立视觉 QA、修复和复验。
- [x] 复制交付件并写入最终证据。

## 最终交付

- 交付文件：`/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS克制图解版_2026-07-23.pptx`
- 工作区构建件：`build/ppt/hkuds_image_deck/Vibe-Trading_HKUDS克制图解版_2026-07-23.pptx`
- 两份文件 SHA-256：`a65e59c2ddbc907baa44e5993b576d23a6c2ecfceedb0267705731a0f312cae6`
- 文件大小：6,972,532 bytes。
- 六页顺序：Vibe-Trading → 项目简介 → Motivation → Challenges → Solution → Outcome。

## 图片生成与内容边界

- 六张正文图均使用内置 `image_gen` 生成，构图、图标、中文、数字和英文标签全部由模型直接输出。
- 没有使用 PowerPoint、Pillow、SVG、HTML 或其他本地方式向正文图添加、覆盖或修正文字。
- Pillow 仅用于制作预览联系表；被嵌入 PPT 的最终六张 PNG 保持模型原始内容。
- 完整提示词与 required labels 位于 `build/ppt/hkuds_image_deck/prompts/prompt_manifest.json`。
- 并发生成曾两次遇到图片服务网络错误；改为单张顺序生成后完成，未切换 CLI、模型或外部服务。

## 模板保护

- 从 `自制.pptx` 第 3 页使用的 `标题和内容` layout 创建六页，保留原始 master、theme、HKU 校徽／中英文校名与红线。
- 每页 slide surface 只有左上标题和一张正文图片；输出包仅含 6 个 slide XML 和 7 个媒体文件（1 个 HKU layout 图片 + 6 张正文图）。
- 自制稿与既有六页短版哈希在交付后仍分别为 `b748caced3f5cca5df2118f24a8ee3345f1bc9ca05e4f5e6f3b63a9b03f47215`、`88b7c7878aa2dc9b2beda6b1b38ec3175233d7fe4bafb88307f7bbdf29295f6c`。

## 验证证据

- 结构与来源隔离：6 页、10 × 5.625 in、精确标题顺序、每页 1 张正文图、正文图不越过红线／页边界、6 张图片哈希唯一、HKUDS layout 图片与线条不变，0 errors / 0 warnings。
- Office Open XML：`All validations PASSED!`。
- ZIP：交付副本无压缩数据错误。
- 最终 PDF：6 页、720 × 405.014 pt、1,298,893 bytes。
- 最终渲染：`build/ppt/hkuds_image_deck/preview/final_render/`。
- 最终联系表：`build/ppt/hkuds_image_deck/preview/contact-final.jpg`。

## 独立视觉 QA 与修复

- 首轮复核确认全部页眉、校徽、红线、标题和正文边界完整；第 1、2、4、6 页 PASS，第 3 页仅有非阻塞的桥接语义建议。
- 唯一阻塞项是第 5 页安全路径文字／箭头在投影时偏小。
- 未做局部放大或文字覆盖，而是通过 `image_gen` 整张重生第 5 页，将安全区提高到约 48% 并放大三条路径。
- 最终独立复核结论：`PASS。三条路径清晰独立，文字、箭头与边框已达到投影可读尺寸；STOP、END、BROKER 均完整，无裁切、遮挡或串线。唯一阻塞项已关闭。`

## Session 收口

### 本 Session 完成

- 将用户自制稿的 HKUDS 第 3 页从“参考样式”提升为真实 slide master/layout 基底。
- 合并自制稿的系统模块内容与既有六页短版的叙事、事实和安全边界。
- 生成六张完整图解正文、组装独立 PPTX，并完成来源保护、结构、Office、ZIP、渲染和独立视觉 QA 闭环。

### 下个 Session 建议

- 若要派生不同受众版，可继续复用此 HKUDS layout 与单图正文方法，只重新生成对应页面图片；当前交付稿保持只读。

### 堵塞项与时机

- 当前无交付堵塞项。
- 正文文字按用户要求完全由图片模型生成，无法像原生文本框那样逐字编辑；若以后需要逐字可编辑版本，应另开文件并明确允许原生文本排版。

### 下个 Session 可直接粘贴的 Prompt

> 请只读使用 `/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS克制图解版_2026-07-23.pptx`，为【填写受众】派生独立新版。保留 HKUDS 底板，只改左上页题；正文继续由 image_gen 生成完整单图，不做本地文字覆盖；生成新文件并完成 Office、ZIP、渲染和独立视觉 QA。

## v2 观众语言修订

### 本次反馈与修改

- 用户要求 Outcome 删除全部四个能力数字，不再用数量支撑价值表达。
- 用户认为 Solution 底部三条安全路径图跑题且看不懂，因此整块删除。
- 用户要求标题更具体、主体图缩小、每个模块增加一行说明，并指出“取证”“连接”等直译词观众无法理解。
- 第 5 页标题改为“解决方案：从提问到可复现研究”；三个模块改为“理解问题，调用工具”“多角色并行研究”“保存过程与结果”。
- 第 5 页底部流程改为“获取数据 → 分析研究 → 构建策略 → 回测验证 → 生成报告”；承托语改为“所有步骤共享数据、工具与研究记录”。
- 第 6 页标题改为“研究交付：从答案到完整证据”；正文只保留“一句问题 → VIBE-TRADING → 运行记录／绩效指标／交易明细／风险警告”。
- 两张新正文图的构图与全部文字仍由内置 `image_gen` 一次性生成；没有本地覆字或局部修字。

### v2 交付与证据

- 新交付文件：`/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS克制图解版_v2_2026-07-23.pptx`
- 构建件：`build/ppt/hkuds_image_deck_v2/Vibe-Trading_HKUDS克制图解版_v2_2026-07-23.pptx`
- 两份 SHA-256：`d4e62ee768d03ea5dbbe2c4c80a621802c555a4ac9d3c86ae4371041d2190c4b`
- 文件大小：9,144,436 bytes；6 页；10 × 5.625 in。
- 第 1–4 页正文图片哈希与 v1 完全一致；v1 交付件哈希仍为 `a65e59c2ddbc907baa44e5993b576d23a6c2ecfceedb0267705731a0f312cae6`。
- 来源 `自制.pptx` 与既有六页短版哈希仍为 `b748caced3f5cca5df2118f24a8ee3345f1bc9ca05e4f5e6f3b63a9b03f47215`、`88b7c7878aa2dc9b2beda6b1b38ec3175233d7fe4bafb88307f7bbdf29295f6c`。
- 结构、来源隔离、Office Open XML、ZIP、LibreOffice PDF 渲染均通过；PDF 6 页、1,190,539 bytes。
- 独立视觉 QA 最终结论 PASS：第 5 页已无安全路径图且观众语言清楚；第 6 页无能力数字；两页标题、正文、HKU Logo 与红线均完整、适合投影。
- 预览：`build/ppt/hkuds_image_deck_v2/preview/contact-v2.jpg`；详细清单：`build/ppt/hkuds_image_deck_v2/delivery_manifest.json`。

### 后续直接使用的 Prompt

> 请只读使用 `/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS克制图解版_v2_2026-07-23.pptx` 派生【填写受众】版本。保留 HKUDS 底板；优先使用观众能直接理解的动作语言，避免 runtime、evidence、link 等直译术语；正文继续由 image_gen 生成完整单图，另存新文件并完成渲染与独立视觉 QA。

## v3 可编辑说明与演讲者文稿

### 用户新增要求

- 六页正文图片全部缩小。
- 图片下方各增加一条原生 PowerPoint 文本框；这行小字不能生成在图片里，必须可直接编辑。
- 六页左上角标题字号同步缩小。
- 六页演讲者备注区加入详细中文口播稿。

### 实施结果

- 当前正式文件（用户修改后标准化重命名）：`/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS中文介绍_演讲版_2026-07-23.pptx`
- 当前正式文件 SHA-256：`8e4eef02bc9599f3ed2237c9306e891dd8550adb67162c5fd222f82e0b740852`；文件大小：6,869,638 bytes。
- 构建件：`build/ppt/hkuds_image_deck_v3/Vibe-Trading_HKUDS克制图解版_v3_可编辑说明_2026-07-23.pptx`
- 原始自动构建件 SHA-256：`501ab7fb1006201c6374b544f9befb970b69921713318c80566037e753575055`；当前正式文件包含用户后续修改，不再与构建件同哈希。
- 当前正式文件仍为 6 页；Office Open XML、ZIP、六页 notes slide 与 `EDITABLE_CAPTION_01..06` 均复核通过。
- 六张正文图统一缩到 8.20 英寸宽，较 v2 缩小约 12.6%；裁切值均为 0，图片内容与哈希未改变。
- 六页左上标题均为原生 24pt；最长标题与 HKU logo 仍保留约 200px 的渲染间距。
- 六个可编辑说明文本框命名为 `EDITABLE_CAPTION_01` 至 `EDITABLE_CAPTION_06`，10.5pt、居中、单行显示。
- 六页均创建原生 notes slide；每页 3 个非空中文段落，共 281–327 个中文字符，按约 60–90 秒完整口播稿编写，可在 PowerPoint 演讲者视图中直接编辑。

### 验证与保护

- 结构／可编辑性、演讲者备注、Office Open XML、ZIP、LibreOffice 六页渲染全部通过。
- 独立视觉 QA 结论 PASS：图片缩小但清晰无变形；六条说明无换行、溢出或碰撞；标题明显缩小；HKU logo 与红线完整。
- v2、v1、`自制.pptx` 与既有六页短版保持只读，哈希分别仍为 `d4e62ee768d03ea5dbbe2c4c80a621802c555a4ac9d3c86ae4371041d2190c4b`、`a65e59c2ddbc907baa44e5993b576d23a6c2ecfceedb0267705731a0f312cae6`、`b748caced3f5cca5df2118f24a8ee3345f1bc9ca05e4f5e6f3b63a9b03f47215`、`88b7c7878aa2dc9b2beda6b1b38ec3175233d7fe4bafb88307f7bbdf29295f6c`。
- 预览：`build/ppt/hkuds_image_deck_v3/preview/contact-v3.jpg`；详细证据：`build/ppt/hkuds_image_deck_v3/delivery_manifest.json`。

### 下个 Session 可直接粘贴的 Prompt

> 请只读使用 `/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS中文介绍_演讲版_2026-07-23.pptx` 派生【填写受众】版本。保留正文图、可编辑页脚说明与演讲者备注的结构；只调整受众叙事和每页口播稿，另存新文件并完成结构、备注、Office、渲染和独立视觉 QA。

## 双语标准化交付（CN / EN）

### 用户锁定要求

- 以用户最后保存的中文演讲稿为唯一内容基线，原封不动地派生纯英文版本。
- 英文版标题、可编辑说明与演讲者备注全部翻译为英文；正文图不能本地覆字，必须逐页重新生成英文图。
- HKU 官方校徽及中英文校名属于品牌底板，保持原样。
- 中文版与英文版使用相同文件名主干，只以 `_CN_` / `_EN_` 区分语言。

### 最终基线与命名

- 用户最后保存的中文源稿 SHA-256：`a62a4fa5ee4f00d9a9d0cafdd04d3920e0412a8b06256493c2dc0507bdf5dbb7`。这次保存晚于 v3 章节记录的 `8e4eef...`，因此双语版以 `a62a4...` 为最终基线。
- 中文标准名：`/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS_Presentation_CN_2026-07-23.pptx`。
- 英文标准名：`/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS_Presentation_EN_2026-07-23.pptx`。
- 英文构建件：`build/ppt/hkuds_bilingual_pair/Vibe-Trading_HKUDS_Presentation_EN_2026-07-23.pptx`。
- 中文交付 SHA-256：`a62a4fa5ee4f00d9a9d0cafdd04d3920e0412a8b06256493c2dc0507bdf5dbb7`，6,869,553 bytes。
- 英文交付 SHA-256：`954b96aa9430207c2641e14034f5c58d31fa0fc2d08ba2cfe404acda14bdc589`，7,298,745 bytes。

### 英文版实施

- 六张正文图均以中文成品中对应 PNG 为编辑基底，通过内置 `image_gen` 逐页完整重生；没有使用 PowerPoint、Python、Pillow、SVG 或本地覆盖层修改图中文字。
- 页面主题、可编辑说明与 speaker notes 按锁定内容合同逐项翻译；段落数保持 `[2, 3, 3, 3, 3, 3]`。
- 每页仍只有 1 张正文图与 1 个 `EDITABLE_CAPTION_01..06` 可编辑说明块；母版、layout、HKU 品牌图片、红线及对象几何位置保持不变。
- 第 5、6 页英文标题因字符串更长，首次渲染出现两行并接近红线；仅将这两页标题从 24pt 缩至 16pt，使其恢复单行，未移动任何对象。
- 独立 QA 指出第 4 页图中 `Research, paper, and live trading` 的 `paper` 语义含糊；按整图重生规则将其修正为 `Research, paper trading, and live trading must stay isolated`，没有局部覆字。
- 图片提示词、源图与英文图哈希记录：`build/ppt/hkuds_bilingual_pair/prompts/imagegen_manifest.json`；英译合同：`build/ppt/hkuds_bilingual_pair/work/content_en.py`。

### 验证证据

- Office Open XML：`All validations PASSED!`，相对中文源稿无新增 XSD 错误。
- ZIP：无压缩数据错误。
- 双语结构合同：命名主干一致；6 页；英文 native text、说明、备注与合同逐项一致；notes 段落数一致；正文图哈希与生成产物一致；master、layout、theme、HKU 品牌图片及页面几何一致。
- 最终英文渲染：`build/ppt/hkuds_bilingual_pair/preview/en_delivery/`；联系表：`build/ppt/hkuds_bilingual_pair/preview/en_delivery/contact_sheet.jpg`。
- 独立视觉 QA 最终结论：`PASS`，0 blocker / 0 major。第 4 页措辞问题已关闭；六页无裁切、重叠或 caption 越界，HKU logo 与红线一致。
- 两项接受的非阻塞 minor：第 2 页约 0.46% 的肉眼不可见比例差异；第 5、6 页为容纳英文长标题而使用 16pt，仍清晰且不碰 logo。
- 完整交付清单：`build/ppt/hkuds_bilingual_pair/delivery_manifest.json`。

### Session 收口

- 本 Session 完成：将用户最后保存的中文演讲稿标准化为 CN 文件，并交付一份内容、图像、caption 和 speaker notes 全英文的 EN 配对文件；六张正文图全部重新生成。
- 下个 Session 建议：若按不同受众派生新版，从 CN 或 EN 中选对应语言作为只读基线，保持相同主干命名并另存，不回改本次双语对。
- 堵塞项与时机：当前无交付堵塞。正式外发前若 README 数量或项目功能再次变化，需要重新核对事实内容再派生，不应静默回改这次演讲稿。
- 下个 Session 可直接粘贴的 Prompt：

> 请只读使用 `/Users/wuhaozhe/Desktop/hkuds/vibe trading ppt/中文母版/Vibe-Trading_HKUDS_Presentation_CN_2026-07-23.pptx` 或对应 `_EN_` 版本，为【填写受众】派生独立新版。保留 HKU 底板、可编辑 caption 与 speaker notes；正文图继续整张生成，不做局部覆字；另存新文件并完成结构、Office、渲染和独立视觉 QA。
