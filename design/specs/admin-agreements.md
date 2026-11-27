# 协议版本 agreements（管理后台）· 设计规格

- 状态：规格先行（fe 起草，编排 D10-3511 / D10-3513 核过；2026-11-27）。画板未出，§1 只列状态与数据来源；画板出图后补文件名与 sha256，入账开发前以本规格与画板为准。
- 核对版本：规划仓库 SPEC_REF f1d6a935d8d8（规划/01 F-ADM-14 行、04 §6.2 / §6.6 / §10.1 / §11.2 `content.agreement`、08 BR-ID-12、BR-WDR-31、BR-ID-34）；契约 rebate-platform origin/main c2cd08ff9 `contracts/openapi.yaml` 的 adminListAgreements（:19056）、adminPublishAgreementVersion（:19135）、adminGetAgreementVersion（:19249）与 schema AgreementType、AdminAgreementVersion、AdminAgreementVersionDetail、AdminAgreementPublishRequest；服务端同一提交 `apps/api/src/modules/content/application/agreement-admin.ts`（F1-02p）、`domain/agreements/index.ts` validateAgreementPublish、`domain/article-body/index.ts`（正文白名单）、`specs/permissions.yaml`。主干 apps/admin 没有页面调 `/admin/v1/agreements`（只在 `resources/index.ts:67` 有「内容」菜单组，权限 any(content.article, content.agreement)）。
- 路由：后台资源 `agreements`（菜单「内容 / 协议版本」）；`agreements/{type}`（该类型的历史版本与正文，抽屉或子页由画板定）；发布表单为该类型页上的抽屉，不另设路由。从哪来：侧栏；去哪：无。
- 需求：01 F-ADM-14（协议部分：Tiptap 富文本、版本化、劳务协议「需重签」、发布需权限点、每次发布记法务确认、不做二次验证）；规则只引编号：BR-ID-12、BR-WDR-31、BR-ID-34。
- 是否资金或归属页面：否。但发布会改变用户须重新同意 / 重签的范围（BR-ID-12、BR-WDR-31），按「对外不可撤回」处理：发布前二次确认，发布后不可修改、不可删除（04 §6.2）。

## 1. 页面与状态（画板待出）

### 1.1 列表：各类型当前版本

| 状态 | 什么时候出现 | 数据来源 |
| --- | --- | --- |
| 列表 | 进入页面 | 五个类型各一行（privacy、agreement、labor_agreement、sdk_list、collect_list，契约 AgreementType 顺序）；每行调一次 adminListAgreements `type=<类型>&page=1&page_size=1` 取最新版（服务端按 published_at、再按 version 倒序）。列：类型名、当前版本 `version`、最低有效版本 `min_version`、需重签 `requires_resign`（只有劳务协议可能为「是」）、法务确认人 `legal_confirmed_by`、法务确认说明 `legal_confirm_note`（过长省略、悬停看全文）、发布时间 `published_at`、发布人（`published_by` 账号 id，D10-3513 ②）、操作【历史版本】【发布新版本】 |
| 某类型未发布 | 该类型 total=0 | 版本列显示「未发布」，其余列为「—」；操作只有【发布第 1 版】（expected_version=0） |
| 加载中 / 加载失败 | 首次进入、刷新 | 表格区骨架；失败时该区换错误结果 +【重试】（10403 换无权限句，10001 走全局重新登录） |
| 无权限 | 账号没有 `content.agreement` | 「协议版本」菜单项不出（主干「内容」菜单组按 any(content.article, content.agreement) 判，组内现在还没有页面，`resources/index.ts:67`）；直接打开地址显示无权限页 |

列表响应**不含** `legal_confirmed_on`（确认日期只进审计，04 §6.6），列表与详情都不显示确认日期。「发布人」先显示 `published_by` 账号 id，名字等契约补字段（FU-ADMIN-AGREEMENT-PUBLISHER-NAME，D10-3513 ②）。

### 1.2 详情：历史版本与正文（只读）

| 状态 | 什么时候出现 | 数据来源 |
| --- | --- | --- |
| 历史版本列表 | 【历史版本】 | adminListAgreements `type=<类型>`，分页（page_size 20），倒序；列同 §1.1，加「正文地址」`url`（新窗口打开）与【查看】 |
| 版本正文 | 历史行【查看】 | adminGetAgreementVersion：`title`、`body`（Tiptap JSON 只读渲染）、`text_sha256`、`article_id` / `article_version`、`min_version`、`requires_resign`、法务确认人与说明、发布时间、发布人 id；操作【以此为底稿发布新版本】（D10-3513 ④） |
| 以此为底稿 | 版本正文里点【以此为底稿发布新版本】 | 打开 §1.3 发布抽屉，**只把这一版的正文**带进编辑器（替换默认预填的当前版正文）；标题、最低有效版本、法务三字段照 §1.3 默认，不带这一版的值；expected_version 仍取该类型当前最新版 |
| 版本不存在 30701 | 列表过时或地址里的版本号不存在 | 显示「该版本不存在」并刷新历史列表 |

已发布版本永不修改、不可删除：详情里没有编辑、删除、撤回入口（「以此为底稿」是发布新版本，不改旧版）。

### 1.3 发布新版本（抽屉表单）

| 字段 | 规则（契约 AdminAgreementPublishRequest、validateAgreementPublish） | 前端做法 |
| --- | --- | --- |
| 新版本号 | 服务端定为当前最新版 + 1（首版为 1），不由表单提交 | 只读显示「将发布第 N 版」 |
| 标题 `title` | 1–100 字 | 必填；预填当前版标题（可改），首版留空 |
| 正文 `body` | Tiptap JSON 字符串，≤ 200000 字符、嵌套 ≤ 20 层，节点与标记只在白名单内：doc、paragraph、heading（1–3 级）、bulletList、orderedList、listItem、blockquote、horizontalRule、image（只许媒体 CDN 地址）、text、hardBreak；bold、italic、link（href） | Tiptap 编辑器只开白名单内的扩展，插图照服务端 article-body 白名单（只许媒体 CDN 地址，D10-3513 ③）；预填当前版正文（可改；从历史版本进入时为那一版正文，§1.2）、首版为空；超长前端先拦 |
| 最低有效版本 `min_version` | 整数，≥ 1、≥ 当前版的 min_version（不下调）、≤ 新版本号；sdk_list、collect_list 必须等于新版本号 | 数字输入，范围提示「当前 M 至 N」；sdk_list / collect_list 固定为 N、只读；说明句按类型：privacy「低于此版本的已登录用户需重新同意」、agreement「只记录最低版本，不触发重新同意」、labor_agreement「低于此版本的签署需重签」（规则只引 BR-ID-12、BR-WDR-31，不在页面另写规则） |
| 需重签 `requires_resign` | 不可自选：劳务协议当且仅当 min_version = 新版本号时为 true，其余类型一律 false；服务端只核不填 | 不给开关；按上式算出、只读显示「需重签：是 / 否」并随 min_version 变化，提交时照算出的值发送 |
| 法务确认人 `legal_confirmed_by` | 1–64 字，去空白后非空 | 必填 |
| 法务确认说明 `legal_confirm_note` | 1–500 字，去空白后非空 | 必填，多行 |
| 法务确认日期 `legal_confirmed_on` | 合法日历日（YYYY-MM-DD） | 必填，日期选择器，**不预填**（D10-3513 ⑤） |
| `expected_version` | 控制台看到的该类型最新版本（无则 0），不符 → 20902 | 打开抽屉时记下，表单不显示 |

| 状态 | 什么时候出现 | 处理 |
| --- | --- | --- |
| 填写 | 【发布新版本】/【发布第 1 版】 | 上表 |
| 发布确认 | 点【发布】 | 确认框列出：类型、新版本号、最低有效版本（与当前版对比）、需重签、法务确认人与日期；提示「发布后不能修改或删除」；按钮【返回修改】【确认发布】 |
| 发布中 | 请求在途 | 表单只读、按钮转圈，连点只发一次 |
| 成功 | 200 | 关抽屉、提示「已发布第 N 版」，以响应刷新该类型行（响应即新版本，含 `url`） |
| 字段被拒 20001 | `data.fields` 列出所有不过的字段（title / body / min_version / requires_resign / legal_confirmed_by / legal_confirm_note / legal_confirmed_on） | 各字段旁提示，不关抽屉、可改后再交；`requires_resign` 被拒说明前端算式与服务端不一致，给通用句并记日志（不让人手改） |
| 版本已变 20902 | `data.resource=agreement`（别人刚发布了新版） | 提示「该协议已有新版本」，重读该类型当前版；表单内容保留，expected_version 更新为新值、新版本号随之 +1，min_version 下限按新当前版重核，用户确认后再交 |
| 无权限 10403 | 权限被撤 | 提示，不能再交 |
| 未登录 10001 | 会话过期 | 全局重新登录，表单内容不保留 |
| 服务端配置缺 50001 | 服务端 h5_base_url 未配或不是 https（agreement-admin.ts 注释） | 通用失败提示 + trace 末 6 位，可重试 |
| 限流 42901 / 429 | — | 稍后再试 |
| 无响应（断网、超时、5xx） | — | 结果未知：不自动重发；重读该类型当前版——最新版本号已是 expected_version + 1 且标题一致 → 按已发布处理；仍是原版本 → 解锁可再交（同一 expected_version，CAS 保证不会发两次） |

## 2. 组件（03 §9.1 antd）

| 区域 | 组件 |
| --- | --- |
| 列表 | Table（5 行固定，不分页；两类公示清单与三类协议同表、不分组，D10-3513 ⑧）、Tag（需重签「是」）、Typography.Text ellipsis（法务说明）、Typography.Text code（发布人 id）、Button（行操作） |
| 历史版本 | Drawer 或子页（画板定）+ Table 分页 + Button【查看】、【以此为底稿发布新版本】 |
| 正文只读 | Tiptap 只读渲染（与 H5 同一套白名单扩展；H5 用 @tiptap/static-renderer 3.31.4） |
| 发布表单 | Drawer + Form：Input（标题）、Tiptap 编辑器（正文）、InputNumber（最低有效版本）、只读 Descriptions（新版本号、需重签）、Input / Input.TextArea（法务确认人、说明）、DatePicker（确认日期）；Modal.confirm（发布确认） |

## 3. 文案键

| 键（拟） | 中文 | 说明 |
| --- | --- | --- |
| `admin_dict.agreement_type.<type>` ×5 | 隐私政策 / 用户协议 / 劳务协议 / SDK 清单 / 个人信息收集清单 | 登记进后台字典 `contracts/texts.admin.default.json`（D10-3513 ①；主干现无此组，由契约线加，§7 第 2 项）；页面按字典取名，补齐前显示编码，不在页面 texts 里另写类型名 |
| 页面与表单句 | 「将发布第 N 版」「发布后不能修改或删除」「需重签：是 / 否」、min_version 三类说明句、20902 / 30701 / 50001 提示 | 后台文案，不进用户侧字典 |

## 4. 接口

| operationId | 什么时候调 | 本页会遇到的返回码 |
| --- | --- | --- |
| adminListAgreements | 进入（每类型 page_size=1）、【历史版本】（按类型分页）、20902 后重读、无响应后核对 | 10001、10403、20001（page_size 超限）、42901 |
| adminGetAgreementVersion | 历史行【查看】 | 10001、10403、20001、30701 |
| adminPublishAgreementVersion | 【确认发布】 | 10001、10403、20001（data.fields）、20902（data.resource=agreement）、42901、50001；**二次验证：契约无 `x-step-up`、08 BR-ID-34 为 none，前端不弹验证**（主干服务端现状见 §7 第 1 项「待上游」） |

发布没有 Idempotency-Key（契约 description：CAS 保证重试不会发布两次，04 §6.6）。

## 5. 权限点（04 §11.2）

`content.agreement`：读（列表、详情）与发布同一个点，读不需二次验证；范围含 SDK 清单与个人信息收集清单（04 §11.2，2026-10-22）。超管全有（ADD-04）。没有该点：菜单不出、地址直开显示无权限页。

## 6. 稿上没画、实现要做的

- 发布表单打开期间别人发布了新版：靠 20902 兜底，不轮询。
- 正文编辑器的扩展集合必须与服务端白名单逐项一致（多开的节点会被 20001 [body] 拒）；实现单测钉住扩展清单。
- 列表 5 个类型并发 5 次读取，任一失败只影响该行（行内【重试】）。
- 首版（total=0）的 min_version 下限为 1、上限为 1，即只能填 1。
- 「以此为底稿」带入的正文若含当前白名单外的节点（旧版按旧白名单发布），编辑器按白名单丢弃并在表单上方提示「部分格式已去掉」，不直接提交原文。

## 7. 待上游与已定默认

**待上游**
1. **二次验证**：契约三个操作都没有 `x-step-up`，08 BR-ID-34 明列「页面与协议发布」为 none（「发布新版用户协议 → 不做二次验证」，2026-11-23）；但主干 `specs/permissions.yaml:51` 的 `content.agreement` 仍是 `step_up_tier: totp`，服务端守卫据此会对发布回 10003。前端照契约与 08 不弹验证、不在前端绕；服务端改为 none 由后端三档改造（B1-18lb 一线）完成，本页落地依赖它。未改前若收到 10003，按确定拒绝提示「服务端暂要求身份验证，本次未发布」（与 F1-08ef 同口径，D10-3467）。
2. **类型名字典**：`admin_dict.agreement_type.*` 五键由契约线登记进 `contracts/texts.admin.default.json`（D10-3513 ①），补齐前页面显示编码。
3. **Tiptap 依赖**：apps/admin 现在没有 Tiptap（只有 apps/h5 依赖 @tiptap/* 3.31.4）；先入账一张 deps 任务给 apps/admin 引入同版本的 @tiptap/core、@tiptap/pm、@tiptap/starter-kit、@tiptap/extension-image（及只读渲染所需的包），本页的开发任务 deps 它（D10-3513 ⑥；锁文件只有 deps 任务能改）。

**已定默认（编排 D10-3513，2026-11-27）**
- ① 类型中文名登记进后台字典（见上第 2 项，§3）。
- ② 「发布人」先显示 `published_by` 账号 id，名字登 FU-ADMIN-AGREEMENT-PUBLISHER-NAME 待契约补（§1.1）。
- ③ 正文插图与服务端 article-body 白名单一致：只许媒体 CDN 地址的 image（§1.3）。
- ④ 历史版本可作底稿发布新版本，只带正文（§1.2）。
- ⑤ 法务确认日期不预填、必填（§1.3）。
- ⑥ 先入账 deps 任务给 apps/admin 引入 Tiptap，本页 deps 它（见上第 3 项）。
- ⑦ 契约不带 type 的全量列表本页不用，按类型取（§4）。
- ⑧ 两类公示清单（sdk_list、collect_list）与三类协议同表、不分组；它们不参与同意（D10-465），min_version 恒等于 version、需重签恒「否」（§1.1、§2）。
