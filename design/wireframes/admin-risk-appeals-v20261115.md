# 后台 · 风控 · 申诉处理 · 线框说明（v2026-11-15，待定稿）

> 状态：待负责人看稿，不是开发规格；定稿后另写 design/specs/。契约基线：rebate-platform origin/main a0d03c585（2026-11-14）。画板在本机运行目录与设计画布，不入库。
> 对抗评审：2026-11-15 由全新的只读评审做了两轮，第 1 轮不通过、修改后第 2 轮通过；只剩读屏属性类问题，记在文末「转开发验收」。画板共 35 张，放在管理后台设计画布的「后台第 2 批三页（待定稿）」一页。

本页是在 2026-10-31 前端线草稿（草稿 r2，负责人未回复，未定稿）基础上，按现在的契约核对、修正、补齐的结果。旧草稿当时的内容来源与 22 条待定项逐条重新对照过，结论写在 §7 与 §8。

## 1. 页面与入口

- 需求：`规划/01` F-ADM-18（申诉处理、客服代为登记、被拦请求查找、撤销另需的权限点与动态码）。规则只引编号：BR-ID-36（可申诉对象、处理时限、同一对象唯一处理中、结案效果；细则「被拦截请求申诉」「维持后再申诉」）、BR-ID-31（解封、移出黑名单）、BR-ID-33（手机号脱敏）、BR-ID-34（后台二次验证档位）、BR-FUND-22（申诉恢复 ①②）、BR-TEXT-23（申诉结果站内信）。形状见 `规划/04` §6.6 `appeals`、§11.2 `risk.appeal`。
- 菜单位置：侧栏「风控与 AI / 风控」→ 页签「申诉」（风控页的其他页签：命中记录、规则清单、黑名单、held 告警，不在本页范围）。
- 路由暂名：列表 `/risk/appeals`（工作台卡片带 `?status=processing`，取自契约 `adminGetDashboard` 示例 `route`）；详情 `/risk/appeals/{appeal_id}`；代登记是列表页上的对话框，不另设路由。
- 入口：
  - 工作台「待处理申诉」卡（`adminGetDashboard` 的 `todo[].key=appeal_pending`，需 `risk.appeal`）：点卡进入本页签，落在「处理中」。工作台本身要 `dashboard.view`；样例账号风控小狸没有 `dashboard.view`，它从侧栏进入。
  - 侧栏「风控」→「申诉」页签。
  - 代登记成功、被拦请求查找结果里的「打开申诉」都进入申诉详情。
- 权限点：`risk.appeal`（读写同一个点；读不需要二次验证）。撤销结案另按详情的 `revoke_permission` 需要 `risk.ban` / `risk.freeze` / `risk.blocklist` 之一并做动态码档二次验证（见 §3）。没有 `risk.appeal` 时列表与详情都回 10403（`data.reason=admin_permission_denied`），整页显示无权限（AdmRiskAppealsNoPerm、AdmRiskAppealDetailNoPerm）。
- 谁能看到：持 `risk.appeal` 的账号（客服、风控），超级管理员持有全部权限点。申诉人「用户详情」链接另需 `user.lookup`。
- 涉及资金：撤销订单申诉会让结算模块生成「申诉恢复」差错单，撤销封禁会解封并改动联盟绑定；按涉资金页面评审。

## 2. 页面上有什么

### 2.1 申诉列表（`adminListAppeals`）

- 标题行「风控」+ 风控页签条（「申诉」为当前页签）。
- 状态页签（四个，计数取 `counts`）：处理中 `counts.processing` → 查询带 `status=processing`；已超时 `counts.overdue` → 带 `overdue=true`；已结案 `counts.closed` → 查询方式待定（§7 P-01）；全部 `counts.all` → 不带状态。计数按本次请求除 `status`、`overdue` 外的全部筛选算。
- 筛选：「申诉对象」下拉（全部 / 账户 / 订单 / 被拦截的请求 → `target_type`）；搜索框「完整申诉编号或 UID」（`q`，精确匹配 `appeal_id` 或申诉人 `user_id`，去首尾空格后 1–64 个字符）+ 小字「精确匹配，不支持部分号码」；【查询】【重置】；右侧【代登记申诉】。
- 已应用条：当前结果对应的筛选 + `total`。
- 表格列（一行一条 `items[]`，按 `created_at` 倒序，样例第 1 行是 10-12 11:30 的 …3e4fa005；每页 20 条，`page` / `page_size`）：
  - 申诉编号：`appeal_id` 末 8 位 + 复制按钮（复制全长）。
  - 申诉人：`user.user_id` 与 `user.phone_masked`（脱敏 3+4，BR-ID-33）；`user=null`（注册类被拦请求，没有账号）显示「没有账号」。
  - 申诉对象：账户；订单 + `target_no`（子订单号）；被拦截的请求 · `request_type` + `target_no` 末 8 位。
  - 申诉前状态：`prev_risk_state`（只账户申诉有，其余「—」）。
  - 提交时间：`created_at`。
  - 处理时限：`deadline_at`（显示为前一日 24:00）；处理中且已过 `deadline_at` 时加「已超时」标签（与契约 `overdue` 口径一致）。
  - 状态：`status`。
  - 处理人：`handler_name`；为空显示「未认领」。
  - 操作：处理中【处理】，已结案【查看】（读屏名带编号末 8 位）。
- 页脚说明句：处理时限只作内部时限（BR-ID-36）、三类申诉对象、订单与被拦请求申诉不改账户风控状态、认领不锁定。

### 2.2 申诉详情（`adminGetAppeal`）

- 顶部：【返回申诉列表】、标题「申诉 …末 8 位」+ 状态标签（`status`）。
- 左栏：
  - 申诉信息卡（两列键值）：申诉编号（`appeal_id` 全长 + 复制）、状态、申诉对象（`target_type` / `target_no` / `request_type`）、申诉人（`user`；有 `user.lookup` 时带【用户详情】）、申诉前状态（`prev_risk_state`，账户申诉）、当前风控状态（`risk_state`，有账号时）、来源（`source`：App 内提交 / 后台代为登记 · 登记人 `registered_by_name`）、提交时间（`created_at`）、处理时限（`deadline_at`）、处理中时「处理人 · 认领于」（`handler_name`、`claimed_at`），已结案时「结案人」「结案时间」（`handler_name`、`closed_at`）。右上【认领】+ 小字「认领只标记处理人，不锁定」。
  - 被拦截的请求卡（只 `target_type=blocked_request`）：拦截请求编号、请求类型、关联手机号（脱敏）、拦截时间、拦截原因（`cause` · `blocklist_dimension`）、申请金额（`amount_fen`，只提现提交，后台金额格式两位小数）。只显示原因类别，不显示命中的值与规则条件。
  - 申诉人陈述卡：`content`（保留换行）。
  - 相关风控记录卡：`risk_hits[]`（新的在前，最多 50 条）——命中时间、规则（`rule_id` + `rule_name`）、处置（`risk_action`）、关联对象（`ref_type` + `ref_id` 原样显示：末 8 位 + 复制，与申诉编号同一画法；订单的 `ref_id` 是对象编号，契约没说返回平台单号，见 §7 P-26）。
- 右栏：
  - 处理中：结案卡——结论单选「维持 / 撤销」（各带按对象类型写的效果说明）；撤销项在 `revoke_permission` 不为空时带「需 {权限点} 与动态码」，本人没有该权限点时置灰并写原因；「结案内部说明」（`note`，1–200 字，计数）；通知方式提示；【提交结案】（撤销且需验证时带盾牌图标与「需动态码二次验证」，选维持时写「维持：只需申诉处理权限，不需动态码」）。
  - 已结案：结案结果卡——结论、结案人、结案时间、效果提示；结案人是本人（或有 `audit.view_all`）时给「查看操作日志」链接，否则一句说明。内部说明只在操作日志，本页不显示。

### 2.3 代登记申诉对话框（`adminRegisterAppeal`；查找用 `adminListBlockedRequests`）

- 说明句；「申诉对象」单选：账户（封禁或冻结的用户）/ 订单（风控作废返利，或黑名单复核后扣回返利的订单）/ 被拦截的请求（44001）。
- 按对象换输入区：账户 → 「用户 UID」（`target_id`）；订单 → 「订单 ID」（`target_id` 为 order_id，见 §7 P-07）；被拦截的请求 → 查找区。
- 查找区（三选一：完整手机号 `phone` / UID `user_id` / 拦截请求编号 `blocked_request_id`）+【查找】；结果表：选择、拦截请求编号（末 8 位 + 复制）、类型、关联手机号（`phone_masked`）、拦截时间（`blocked_at`）、拦截原因（`cause` · `blocklist_dimension`）、申请金额（`amount_fen`）、处理中的申诉（`processing_appeal_id`：有值时该行不可选，给「打开申诉 …」）。按完整手机号查到结果时这次查找写操作日志（契约），输入提示里写明。
- 「本人陈述」（`content`，必填）；「登记原因说明」（`reason`，1–200 字，只进操作日志）；【取消】【登记申诉】。本页不传 `user_id`（由服务端按对象推出）。

## 3. 操作与接口

| 操作 | operationId 与方法路径 | 权限点 | 二次验证 | 成功后 | 失败码与显示 |
| --- | --- | --- | --- | --- | --- |
| 看列表 | `adminListAppeals` · GET /admin/v1/appeals | `risk.appeal` | 无 | 表格 + 四个计数 | 10001 跳登录；10403 整页无权限（AdmRiskAppealsNoPerm）；20001 `fields=[q]` 搜索框下标红，枚举 / `page_size` 不应出现（清参数重查）；429 `error.42901`；5xx `error.50001`（AdmRiskAppealsError） |
| 看详情 | `adminGetAppeal` · GET /admin/v1/appeals/{appeal_id} | `risk.appeal` | 无 | 详情各卡 | 10001；10403 整页无权限（AdmRiskAppealDetailNoPerm）；20001 `fields=[appeal_id]`「找不到这条申诉」；429；5xx（AdmRiskAppealDetailError） |
| 查被拦请求 | `adminListBlockedRequests` · GET /admin/v1/blocked-requests | `risk.appeal` | 无 | 结果表；按手机号查到结果写审计 | 10001；10403；20001 `phone_invalid` / 三选一 / `page_size`；429；5xx（返回码一览 AdmRiskAppealRegisterErrors） |
| 代登记 | `adminRegisterAppeal` · POST /admin/v1/appeals | `risk.appeal` | 无 | 关闭对话框，打开返回的申诉详情（AdmRiskAppealRegistered） | 10001；10403；20001 `target_id`（AdmRiskAppealRegisterInvalid）/ `reason` / `content` / `user_id`；30418（AdmRiskAppealRegisterUsedUp）；429；5xx；结果未知（AdmRiskAppealRegisterUnknown） |
| 认领 | `adminClaimAppeal` · POST /admin/v1/appeals/{appeal_id}/claim（`expected_row_version`） | `risk.appeal` | 无 | 用返回的详情刷新（AdmRiskAppealClaimed） | 10001；10403；20001 `appeal_id`；20902 `resource=appeal` 刷新（AdmRiskAppealClaimConflict）；429；5xx；结果未知（AdmRiskAppealClaimUnknown；重试后确认上次已生效 AdmRiskAppealClaimUnknownDone） |
| 结案 | `adminResolveAppeal` · POST /admin/v1/appeals/{appeal_id}/resolve（`decision`、`note`、`expected_row_version`；需要时带 `X-Step-Up-Token`） | `risk.appeal`；撤销另按 `revoke_permission`（见下） | 撤销且 `revoke_permission` 不为空时 totp 档（10003 `data.tier=totp`） | 右栏换成结案结果（AdmRiskAppealResolved） | 10001；10003 弹动态码（AdmRiskAppealResolveStepUp）；10403（AdmRiskAppealResolveNoPerm）；20001 `note`（AdmRiskAppealResolveInvalid）/ `appeal_id`「找不到这条申诉」（返回码一览）；20902 已结案（AdmRiskAppealResolveConflict）/ 仍处理中（AdmRiskAppealResolveStale）；429；5xx；结果未知（AdmRiskAppealResolveUnknown；重试后确认上次已生效 AdmRiskAppealResolveUnknownDone） |

结案的四种情况（契约 `adminResolveAppeal`、`adminGetAppeal` 的 `revoke_permission`；BR-ID-36 细则「被拦截请求申诉」权限）：

| 情况 | 需要 | 画板 |
| --- | --- | --- |
| 选维持（任何对象） | 只要 `risk.appeal`，不需动态码 | AdmRiskAppealDetailUphold |
| 撤销且 `revoke_permission=null`（订单申诉；被拦请求 `cause=rule`） | 只要 `risk.appeal`，不需动态码 | AdmRiskAppealDetailOrder |
| 撤销且 `revoke_permission` 为 `risk.ban` / `risk.freeze` / `risk.blocklist`，本人有该点 | 该点 + totp 档动态码 | AdmRiskAppealDetail（已选撤销，按钮带盾牌）→ AdmRiskAppealResolveStepUp |
| 同上，本人没有该点 | 「撤销」置灰并说明；只能维持或请有权限的人结案 | AdmRiskAppealResolveNoPerm（申诉样例账号） |

前端只按详情返回的 `revoke_permission` 决定要不要盾牌与置灰，不自己按对象类型推。结案的检查顺序（契约）：`risk.appeal` → 请求体 → `appeal_id` → 20902 → 撤销另需的权限点 → 动态码，所以 20902 先于 10003 出现。

## 4. 各状态怎么显示

- 加载中：列表保留标题、页签条与筛选，表格区换成骨架，状态页签不带计数（计数随同一次响应返回）——AdmRiskAppealsLoading（样例为从工作台进入时落在「处理中」）。详情各卡换成骨架，不显示【认领】与结案卡——AdmRiskAppealDetailLoading。查找中：【查找】转圈、结果区骨架（返回码一览）。
- 空：筛选或 `q` 没有匹配时 `items=[]`、`total=0`，表格换成空状态，四个计数按申诉对象与 `q` 重新算（AdmRiskAppealsEmpty）；查找无结果给空状态句（返回码一览）。
- 无权限（10403）：查询小狸（只有 `user.lookup`、`order.view`）从链接直接打开列表或详情，整页只显示 10403 文案与【回到用户查询】，不显示任何申诉内容；侧栏按其权限裁剪（AdmRiskAppealsNoPerm、AdmRiskAppealDetailNoPerm）。写操作时刚被收回权限的 10403 用提示句，表单内容保留（返回码一览）。
- 读取出错：5xx 带 `code=50001` 显示 `error.50001`（带 trace 后 6 位）+【重新加载】，已应用的筛选保留（AdmRiskAppealsError、AdmRiskAppealDetailError）；超时 / 无响应借用 `net.unavailable`（§7 P-20）；429 用 `error.42901` 并按 Retry-After 禁用按钮。读接口重试没有副作用。
- 提交中：代登记对话框整体置灰、【取消】与关闭置灰、主按钮转圈（AdmRiskAppealRegisterSubmitting）；结案卡置灰、【提交结案】转圈（AdmRiskAppealResolveSubmitting）；认领中【认领】转圈，结案表单不受影响（返回码一览）。
- 校验未通过（20001）：结案 `note` 落到字段下（AdmRiskAppealResolveInvalid）；代登记 `target_id`（AdmRiskAppealRegisterInvalid），`reason`、`content`、`user_id` 与列表 `q`、查找 `phone_invalid` 写在两张返回码一览里。前端能先拦的（空、超 200 字、11 位手机号）先拦，服务端结果同样落到对应字段。
- 并发冲突（20902 `data.resource=appeal`）：认领冲突刷新后可再认领（AdmRiskAppealClaimConflict）；结案时别人先结案 → 右栏换成别人的结案结果（AdmRiskAppealResolveConflict）；结案时别人刚认领、仍处理中 → 结论与内部说明保留，可重新提交（AdmRiskAppealResolveStale）。代登记没有 20902：同一对象已有处理中的申诉时返回那条申诉（§7 P-06）；次数用完是 30418（AdmRiskAppealRegisterUsedUp）。
- 成功后：认领 → AdmRiskAppealClaimed；结案 → AdmRiskAppealResolved；代登记 → AdmRiskAppealRegistered。回到列表时重新查询（不做乐观更新）。
- 结果未知（请求发出后网络中断、超时或响应读不出）：表单保持打开并锁定，输入项置灰、保留已填内容；一条警告提示条；只给【重试】（原样重发）和【去列表核对】（关闭并回列表重新读取）；不给取消与右上角关闭，不自动重试。三个写操作各一张：
  - 代登记（AdmRiskAppealRegisterUnknown）：对话框标题「代登记申诉 · 结果未知」，查找区、对象、陈述、原因全部锁定。原样重发安全的依据：契约 `adminRegisterAppeal` 不带 Idempotency-Key，但检查顺序里「同一对象已有处理中的申诉 → 返回那条原申诉、不新建」（注册类另按同一关联手机号）。所以上次若已登记，重试返回的就是那条申诉，前端照常打开详情；上次没登记就正常新建。重试也可能遇到 30418（上次没登记、次数已满）或 20001（对象状态已变），按各自画板显示。边界：上次其实已登记、而且在重试之前那条申诉已被别人结案时，「返回原申诉」不再成立，重试会新建第二条或回 30418；可能性很小，照现画法，并入 §7 P-06。
  - 认领（AdmRiskAppealClaimUnknown）：申诉信息卡顶部提示条带两个按钮，【认领】不显示，【用户详情】等会离开本页的按钮置灰，结案卡锁定（「认领结果确认前不能结案」）。锁结案卡不是契约要求，是有意取舍：结果确认前不让接着结案，免得叠加两个未知结果。原样重发安全的依据：契约 `adminClaimAppeal` 用 `expected_row_version` 做 CAS，「the CAS keeps a retry from claiming twice」。重试后两种情况：
    - 回 20902，重新读取后 `handler_id` 是本人：契约写明认领成功时「`handler_id` becomes the caller, `claimed_at` the server's current time and `row_version` goes up by 1」（openapi.yaml 第 22479–22483 行），所以这说明上次已生效 → 提示「上次的认领已生效」，不显示【认领】，结案卡解锁（AdmRiskAppealClaimUnknownDone）。
    - 回 20902，重新读取后处理人是别人或已结案：按 AdmRiskAppealClaimConflict / AdmRiskAppealResolveConflict 显示。上次没生效、重试成功：同 AdmRiskAppealClaimed。
  - 结案（AdmRiskAppealResolveUnknown）：结案卡锁定（结论、内部说明保留），【用户详情】置灰，提示条在卡内顶部，按钮行只有【去列表核对】【重试】。原样重发安全的依据：契约 `adminResolveAppeal` 用 `expected_row_version` 做 CAS，「the CAS keeps a retry from closing twice」。重试后：
    - 回 20902，重新读取后 `status` 已不是处理中且 `handler_id` 是本人：契约写明结案时「`status` becomes the decision, `closed_at` the server's current time, `handler_id` the caller」（openapi.yaml 第 22599–22608 行），所以这说明上次已生效 → 提示「上次的结案已生效」，右栏显示本人的结案结果（AdmRiskAppealResolveUnknownDone）。
    - 回 20902，已结案但结案人不是本人：同 AdmRiskAppealResolveConflict；仍处理中：同 AdmRiskAppealResolveStale。上次没生效、重试成功：同 AdmRiskAppealResolved。带动态码的撤销：重试时带上次的 `X-Step-Up-Token`；契约把令牌的有效期和可用次数留给服务端决定（`adminStepUp`：「the token lifetime and number of uses … the server decides」），所以令牌能否复用列为待定（§7 P-23）；若服务端回 10003 就再弹动态码，验证后用新令牌重发同一请求。注意契约检查顺序 20902 先于 10003，上次已结案时重试先得到 20902，不会白要一次动态码。

## 5. 文案与出处

| 位置 | 文案 | 出处 |
| --- | --- | --- |
| 申诉状态标签 | 处理中 / 维持 / 已撤销 | 字典 `admin_dict.appeal_status.*`（contracts/texts.admin.default.json） |
| 申诉前状态、当前风控状态 | 正常 / 冻结 / 申诉中 / 封禁（稿上后跟编码） | `admin_dict.risk_state.*` |
| 风控记录「处置」 | 通过 / 转人工 / 拦截 / 作废佣金 | `admin_dict.risk_action.*` |
| 申诉对象、请求类型、拦截原因与黑名单维度、来源、关联对象类型 | 账户 / 订单 / 被拦截的请求；注册 / 提现提交 / 换手机号 / 收款账号；黑名单 · 手机号 / 收款账号（支付宝）…；App 内提交 / 后台代为登记 | 草拟（字典无键；中文取 contracts/enums/identity.yaml 各值描述与 BR-ID-36 细则类型表，§7 P-12） |
| 冲突 | 状态已变化，请刷新后重试 | `error.20902` |
| 限流 | 操作太频繁，请稍后再试 | `error.42901` |
| 服务出错 | 出了点问题，请稍后再试（{trace6}） | `error.50001` |
| 字段错（不应出现的） | 填写内容有误，请检查 | `error.20001` |
| 手机号不合法 | 请输入 11 位中国大陆手机号 | `error.20001.phone_invalid` |
| 次数用完 | 这项申诉的次数已用完，不能再提交申诉 | `error.30418`；BR-ID-36 细则「维持后再申诉」 |
| 无权限 | 当前账号没有这项操作的权限，请联系超级管理员开通 | 契约 `AdminPermissionDenied` 示例 `msg`（10403 `admin_permission_denied`；后台字典无键） |
| 读接口无响应 | 网络不可用｜请检查网络后重试 | `net.unavailable` / `net.unavailable.desc`（借用 App 键，§7 P-20） |
| 动态码弹窗 | 二次验证 · 动态码；请输入身份验证器中的 6 位动态码；【取消】【验证并继续】 | 照 AdmStepUp；档位 BR-ID-34、契约 `adminResolveAppeal` |
| 无权限页说明 | 申诉页需要权限点 risk.appeal。你是从链接直接打开的… | 契约 `adminListAppeals` / `adminGetAppeal`（权限点）；措辞草拟 |
| 认领小字 | 认领只标记处理人，不锁定 | 契约 `adminClaimAppeal`（D10-158）；措辞草拟 |
| 处理时限说明 | 处理时限只作内部时限，超过即标「已超时」并告警，不对申诉人显示 | BR-ID-36（处理时限只作内部时限）；措辞草拟 |
| 结论效果（账户 · 封禁） | 维持：风控状态恢复为封禁，限制照旧；撤销：风控状态改为正常，按解封处理（淘宝授权失效需本人重新授权） | 契约 `adminResolveAppeal` 效果段、BR-ID-31；措辞草拟 |
| 结论效果（订单） | 维持：订单不再显示申诉中，返利状态不变（作废的仍作废，扣回的仍扣回）；撤销：系统生成「申诉恢复」差错单（作废与扣回的订单都适用），在「对账与差错」由有权限的人处理后恢复 | 契约 `adminResolveAppeal`（D10-1180）、BR-FUND-22 申诉恢复 ①②；措辞草拟 |
| 结论效果（被拦请求 · 名单） | 维持：拦截照旧；撤销：造成拦截的黑名单条目在同一操作里移出，系统不代为重新提交 | 契约 `adminResolveAppeal`、BR-ID-31、BR-ID-36 细则；措辞草拟 |
| 需要的权限 | 撤销封禁另需 risk.ban 权限，并做动态码二次验证；需 {权限点} 与动态码；当前账号没有 {权限点}，不能撤销… | 契约 `revoke_permission`；措辞草拟 |
| 维持提示 | 维持：只需申诉处理权限，不需动态码 | 契约 `adminResolveAppeal`（upholding never needs either）；措辞草拟 |
| 通知方式提示 | 结案后系统给申诉人发「申诉结果」站内信（APPEAL_RESULT）…；被拦请求：不发站内信、不发短信，由客服在企业微信会话里告知本人 | BR-TEXT-23、BR-ID-36、契约 `adminResolveAppeal`；措辞草拟 |
| 内部说明 / 登记原因提示 | 只写入操作日志，不对申诉人（本人）显示；1–200 字 | 契约 `note` / `reason` |
| 查找提示（手机号） | 11 位中国大陆手机号；按关联手机号和该号码现在所属账号查。查到结果时这次查找会记入操作日志 | 契约 `adminListBlockedRequests`；措辞草拟 |
| 风控记录卡副标题 | 最近 50 条，新的在前；只显示时间、规则、处置与关联对象，不显示命中的值与规则条件 | 契约 `adminGetAppeal` `risk_hits` |
| 结果未知提示条（三张） | 「…结果未知」「请求已经发出，但没有收到结果…」「【重试】…原样再发一次…不会重复…」「【去列表核对】…」 | 草拟；重发不重复的说法出自契约（见 §4） |
| 结案结果未知 · 动态码 | 重试时带上次验证得到的凭证 [待定：这张凭证在重试时能否再次使用] | 待定（§7 P-23） |
| 返回原申诉（RegisterErrors） | [待定：前端分不出新建与返回原申诉] | 待定（§7 P-06） |
| 结果未知后确认已生效 | 上次的认领已生效 / 上次的结案已生效（重试时服务端回「状态已变化…」，页面已重新读取…） | 草拟；判断依据契约（§4） |
| 「已结案」页签查询 | [待定：「已结案」页签点开后发哪个查询] | 待定（§7 P-01） |
| 20902 仍处理中补充句 | 处理人已变为 {handler_name}…请确认后重新提交 | 草拟（§7 P-22） |
| 按钮、列名、空态、加载提示、成功提示、说明句等其余文字 | 照画板 | 草拟（§7 P-14） |

## 6. 画板清单

| 文件名 | 标题 | 画的是什么 | 新画 / 改过 / 沿用旧稿 |
| --- | --- | --- | --- |
| AdmRiskAppeals | 后台 · 风控 · 申诉列表 | 列表「全部」页签，8 行样例 | 改过（去「剩 N 个工作日」与时限取值复述） |
| AdmRiskAppealsEmpty | 后台 · 风控 · 申诉列表 · 没有结果 | 筛选无结果，四个计数为 0 | 改过（页脚说明句） |
| AdmRiskAppealsLoading | 后台 · 风控 · 申诉列表 · 加载中 | 表格骨架，从工作台进入落在「处理中」 | 新画 |
| AdmRiskAppealsError | 后台 · 风控 · 申诉列表 · 读取出错 | 50001 错误块 +【重新加载】 | 新画 |
| AdmRiskAppealsNoPerm | 后台 · 风控 · 申诉列表 · 无权限（查询小狸） | 10403 整页 | 新画 |
| AdmRiskAppealDetail | 后台 · 风控 · 申诉详情（账户 · 封禁，处理中） | 未认领；结案卡选撤销、带盾牌 | 改过（去「剩 N」） |
| AdmRiskAppealDetailLoading | 后台 · 风控 · 申诉详情 · 加载中 | 卡片骨架 | 新画 |
| AdmRiskAppealDetailError | 后台 · 风控 · 申诉详情 · 读取出错 | 50001 错误块 | 新画 |
| AdmRiskAppealDetailNoPerm | 后台 · 风控 · 申诉详情 · 无权限（查询小狸） | 10403 整页 | 新画 |
| AdmRiskAppealDetailOrder | 后台 · 风控 · 申诉详情（订单，处理中） | `revoke_permission=null`，撤销不需动态码 | 改过（订单效果含扣回单） |
| AdmRiskAppealDetailBlocked | 后台 · 风控 · 申诉详情（被拦截的请求 · 注册，没有账号，13:00 认领后） | 名单造成，撤销需 risk.blocklist；时点在列表稿之后（列表是认领前） | 改过（去「剩 N」、标题注明时点） |
| AdmRiskAppealDetailUphold | 后台 · 风控 · 申诉结案 · 选维持（不需额外权限与动态码） | 封禁申诉选维持，按钮无盾牌 | 新画 |
| AdmRiskAppealClaimed | 后台 · 风控 · 申诉详情 · 已认领 | 认领成功 | 改过（去「剩 N」） |
| AdmRiskAppealClaimConflict | 后台 · 风控 · 申诉详情 · 认领冲突（20902） | 别人先认领 | 改过（去「剩 N」） |
| AdmRiskAppealClaimUnknown | 后台 · 风控 · 申诉详情 · 认领结果未知 | 认领结果未知，结案卡锁定，【用户详情】置灰 | 新画 |
| AdmRiskAppealClaimUnknownDone | 后台 · 风控 · 申诉详情 · 认领结果未知后确认已生效 | 重试回 20902、重读后处理人是本人 | 新画 |
| AdmRiskAppealResolveStepUp | 后台 · 风控 · 申诉结案 · 动态码 | 撤销封禁的 totp 动态码弹窗 | 改过（去「剩 N」） |
| AdmRiskAppealResolveSubmitting | 后台 · 风控 · 申诉结案 · 提交中 | 结案在途 | 改过（去「剩 N」） |
| AdmRiskAppealResolved | 后台 · 风控 · 申诉详情 · 已结案（撤销） | 结案成功 | 沿用 |
| AdmRiskAppealResolveInvalid | 后台 · 风控 · 申诉结案 · 说明未填（20001） | `note` 校验 | 改过（去「剩 N」） |
| AdmRiskAppealResolveConflict | 后台 · 风控 · 申诉结案 · 冲突（20902） | 别人先结案 | 沿用 |
| AdmRiskAppealResolveStale | 后台 · 风控 · 申诉结案 · 冲突（20902，仍处理中） | 别人刚认领，可重新提交 | 改过（去「剩 N」） |
| AdmRiskAppealResolveNoPerm | 后台 · 风控 · 申诉详情 · 无撤销权限（缺 risk.ban） | 申诉样例账号，撤销置灰 | 改过（去「剩 N」） |
| AdmRiskAppealResolveUnknown | 后台 · 风控 · 申诉结案 · 结果未知 | 撤销封禁（带过动态码）结果未知，结案卡锁定，【用户详情】置灰 | 新画 |
| AdmRiskAppealResolveUnknownDone | 后台 · 风控 · 申诉结案 · 结果未知后确认已生效 | 重试回 20902、重读后本人已结案 | 新画 |
| AdmRiskAppealRegister | 后台 · 风控 · 代登记申诉（账户） | 账户申诉 | 改过（订单选项、底图列表） |
| AdmRiskAppealRegisterNoAccount | 后台 · 风控 · 代登记申诉（被拦截的请求 · 注册，没有账号） | 按完整手机号查找 | 改过（订单选项、查找提示写明记日志） |
| AdmRiskAppealRegisterBlockedOp | 后台 · 风控 · 代登记申诉（被拦截的请求 · 提现提交，账号正常） | 按 UID 查找，一行已有处理中的申诉 | 改过（订单选项、底图列表） |
| AdmRiskAppealRegisterSubmitting | 后台 · 风控 · 代登记申诉 · 提交中 | 登记在途，查找区与结果行全部锁定 | 改过（订单选项、查找区锁定） |
| AdmRiskAppealRegisterInvalid | 后台 · 风控 · 代登记申诉 · 对象不能申诉（20001） | `target_id` 校验 | 改过（订单选项、底图列表） |
| AdmRiskAppealRegisterUsedUp | 后台 · 风控 · 代登记申诉 · 次数已用完（30418） | 30418 | 改过（订单选项、底图列表） |
| AdmRiskAppealRegisterUnknown | 后台 · 风控 · 代登记申诉 · 结果未知 | 对话框锁定，只有【去列表核对】【重试】 | 新画 |
| AdmRiskAppealRegistered | 后台 · 风控 · 代登记申诉 · 已登记 | 登记成功后打开的详情 | 改过（去「剩 N」） |
| AdmRiskAppealResolveErrors | 后台 · 风控 · 申诉列表与处理 · 返回码一览 | 列表、详情与认领、结案的全部返回码 | 改过（结果未知改指新画板、去掉后端待实现说明、加「已结案」页签行） |
| AdmRiskAppealRegisterErrors | 后台 · 风控 · 代登记申诉 · 返回码一览 | 查找与代登记的全部返回码 | 改过（结果未知改指新画板、去掉后端待实现说明） |

画板由 `couli-runs/F1-spec-drafts/admin-risk-appeals/gen-risk-appeals.py` 的副本生成（外壳与旧稿同一份），改动处注明 v20261115。没有删掉的旧画板。

## 7. 待定清单

> 2026-11-15 分拣：本节各条先对契约与规划核实现状，再交 TypeSafe Jev 判断（规划/11 §7.1），分三类——「已按默认处理」的由代理按默认做法定，负责人看稿时可以推翻；「转契约线 / 规划补」的不问负责人，画板先照默认画法；「待负责人定」的本页没有。Jev 后的数字是「代理可先按默认做」一问的分数（0–1）。

| 编号 | 是什么 | 画板上的占位或默认画法 | 需要谁定（分拣前的写法，以分拣列为准） | 分拣（2026-11-15） |
| --- | --- | --- | --- | --- |
| P-01 | 「已结案」页签查不出：契约 `counts.closed` 是维持与已撤销的合计，但 `status` 筛选只接受一个值（processing / upheld / revoked），没有一次查询对应「已结案」（旧稿 §7-1，仍未解决） | 页签照画、计数照 `counts.closed`；返回码一览写 `[待定：「已结案」页签点开后发哪个查询]` | 契约线（加 `closed` 筛选值或允许多值）；负责人可选改为拆成两个页签 | 转契约线补（不问负责人）：`adminListAppeals` 的 `status` 筛选加 `closed`（= upheld + revoked）或允许多值，使「已结案」页签能一次分页查出；补上前该页签不开发。 |
| P-02 | 申诉编号统一用 `appeal_id`：契约已定（列表说明：显示编号就是 appeal_id，不另设号）。剩下的是对账页、操作日志页旧稿里的 AP… 写法（旧稿 §7-2） | 本页已全用 UUID | 那几页定稿时处理，不在本页 | 不属于本页的决定，定稿时一并处理（Jev 0.95） |
| P-03 | 列表里长编号只显示末 8 位 + 复制（旧稿 §7-3） | 末 8 位 + 复制，详情显示全长 | 负责人 | 已按默认处理（Jev 0.95，待负责人看稿时可推翻） |
| P-04 | 44001 弹窗没有拦截请求编号：BR-ID-36 细则要求弹窗显示这个编号（第三方首次登录被拦、没有账号也没有手机号的人只能靠它让客服查到），契约 `adminListBlockedRequests` 也写「44001 弹窗里显示的 ref_id」，但 error-codes.yaml 里 44001 的 `data` 只有 `risk_msg_code`——契约内部不同步（旧稿 §7-4，仍未解决） | 查找区三种方式照画 | 契约线 + App 线 | 转契约线补（不问负责人）：按 BR-ID-36 给 44001 的 `data` 补拦截请求编号（契约 `adminListBlockedRequests` 已写「44001 弹窗里显示的 ref_id」，error-codes.yaml 的 44001 却没有这个字段，属同步缺陷），App 线在弹窗里显示、可复制。不补的话，第三方首次登录被拦、没有账号也没有手机号的人查不到。 |
| P-06 | 代登记遇到同一对象已有处理中的申诉时，契约返回那条原申诉（HTTP 200、同形状），前端分不出新建还是旧的（旧稿 §7-6，仍未解决）。另：结果未知后重试，若上次已登记且那条已被结案，重试会新建第二条或回 30418（可能性很小） | 一律打开返回的申诉详情（AdmRiskAppealRegistered），返回码一览该行标待定、不出区分提示 | 契约线（如加 `reused` 标记）/ 负责人 | 转契约线补（不问负责人）：`adminRegisterAppeal` 的 200 响应加「是否返回了原有申诉」标记（如 `reused`）；补上后页面才出区分提示。 |
| P-07 | 代登记订单申诉要内部 `order_id`，客服手里是平台订单号，本对话框没有按订单号查的接口（旧稿 §7-7，仍未解决）；订单选项的可申诉范围已按契约补「黑名单复核后扣回」 | 「订单」单选项保留，输入框「订单 ID」未单独画 | 负责人（保留 / 去掉订单项）；要按订单号查需契约线 | 已按默认处理（Jev 0.88，待负责人看稿时可推翻） |
| P-08 | 代登记账户时是否预览用户风控状态：`risk.appeal` 下没有预览接口（旧稿 §7-8） | 只给 UID 输入框，以服务端结果为准 | 负责人 | 已按默认处理（Jev 0.89，待负责人看稿时可推翻） |
| P-10 | 本人陈述没有长度上限：契约 `content` 只有 minLength 1（旧稿 §7-10，仍未解决） | 不显示计数 | 契约线 + App 线 | 转契约线补（不问负责人）：给申诉陈述 `content` 定 maxLength（App 提交与后台代登记同一上限），App 线同步。 |
| P-11 | 申诉人 UID 的显示与搜索：契约 `user_id` 是 UUID，`q` 按 `user_id` 精确匹配（旧稿 §7-11） | 画板沿用 U 号样例写法 | 负责人（与用户管理页一致即可） | 已按默认处理（Jev 0.96，待负责人看稿时可推翻） |
| P-12 | 后台字典缺行：只有 `appeal_status`、`risk_state`、`risk_action`，没有申诉对象类型、请求类型、拦截原因、黑名单维度、来源、关联对象类型的中文名（旧稿 §7-12）。另：枚举描述把 account 写作「账号」，画板照 BR-ID-36 写「账户」。按 BR-TEXT-25，后台枚举中文名先在其细则表登记，补齐前原样显示编码 | 用稿上草拟用词 | 契约线补字典；用词负责人 | 转规划补（不问负责人）：先在 BR-TEXT-25 细则表加行：申诉对象类型、被拦请求类型、拦截原因、黑名单维度、申诉来源、关联对象类型（用词以画板为提议，account 写「账户」）；再由契约线补字典键。登记前实现上原样显示编码。 |
| P-13 | 风控页各页签的名字与可见权限（只持 `risk.appeal` 的账号能否看命中记录、黑名单）（旧稿 §7-13） | 页签名照规则清单稿；本页无权限稿用没有任何 risk.* 的查询小狸，避开这个问题 | 风控页统一定 | 不属于本页的决定，定稿时一并处理（Jev 0.94） |
| P-14 | 草拟文案待确认：§5 标「草拟」的全部文字（说明句、效果说明、通知提示、字段提示、空态、成功提示、结果未知提示条、无权限说明等）（含旧稿 §7-14） | 照画板 | 负责人 | 已按默认处理（Jev 0.95，待负责人看稿时可推翻） |
| P-15 | 结案结论是否预选（旧稿 §7-15） | 画板为演示预选；建议实现时不预选 | 负责人 | 已按默认处理（Jev 0.93，待负责人看稿时可推翻） |
| P-16 | 结案时是否预览站内信正文（旧稿 §7-16） | 不预览，只写模板编码 APPEAL_RESULT | 负责人 | 已按默认处理（Jev 0.93，待负责人看稿时可推翻） |
| P-17 | 【认领】何时显示、叫什么：契约允许本人再认领（只让 `row_version` 加 1）（旧稿 §7-17） | 处理中且处理人不是本人时显示「认领」 | 负责人 | 已按默认处理（Jev 0.93，待负责人看稿时可推翻） |
| P-18 | 只持 `risk.appeal` 的样例账号「申诉样例账号」（旧稿 §7-18） | 保留，用于 AdmRiskAppealResolveNoPerm | 派工方 / 负责人 | 不属于本页的决定，定稿时一并处理（Jev 0.94） |
| P-19 | 旧风控稿规则编号不合契约 `AdminRiskRuleId` 格式（旧稿 §7-19） | 本页用 ORDER_BLACKLIST 等；其他页签不在本页 | 风控页定稿时统一 | 不属于本页的决定，定稿时一并处理（Jev 0.95） |
| P-20 | 后台读接口无响应借用 App 的 `net.unavailable`（旧稿 §7-20） | 照用 | 负责人 | 已按默认处理（Jev 0.96，待负责人看稿时可推翻） |
| P-21 | 结案结果卡「查看操作日志」的筛选：契约 `adminListAuditLogs` 的 `target_type` 是自由文本，没写申诉记录的取值（旧稿 §7-21，仍未解决） | 链接只带 `target_id={appeal_id}`；没有查看全部日志权限的账号只看得到自己的记录，实现时在链接提示里注明（画板不另画） | 契约线 | 转契约线补（不问负责人）：`adminListAuditLogs` 写明申诉记录的 `target_type` 取值，页面据此给「查看操作日志」加类型筛选（没有查看全部日志权限的账号只看得到自己的记录，实现时在链接提示里注明）。 |
| P-22 | 20902 仍处理中时多一句「处理人已变为…请确认后重新提交」（旧稿 §7-22） | 照画（AdmRiskAppealResolveStale） | 负责人 | 已按默认处理（Jev 0.91，待负责人看稿时可推翻） |
| P-23 | 带动态码的撤销结案在结果未知后重试，上次的 `X-Step-Up-Token` 能否再用：契约 `adminStepUp` 把令牌有效期与可用次数留给服务端；后端主干的现行实现是业务成功才作废令牌、被拒或出错时释放（admin 权限守卫，测试 AC-B1-34h） | 重试原样带上次令牌；服务端回 10003 时再弹动态码 | 契约线 / 后端 | 转契约线补（不问负责人）：把后端现行行为写进契约 `adminStepUp`：二次验证令牌业务成功才作废，被拒或出错时释放、有效期内可再用（admin 权限守卫的实现；测试 AC-B1-34h 验证了成功后不可再用）。写明后画板把占位换成确定说法。与「内容 P-12」是同一件事。 |
| P-24 | 订单申诉详情是否显示订单当前返利状态（作废 / 扣回）：`adminGetAppeal` 不返回订单的返利状态，撤销后走 R12 还是 R13 由结算模块按订单现状定 | 效果说明写成两种都适用的通用说法，不显示状态 | 负责人（要显示需契约线加字段） | 已按默认处理（Jev 0.91，待负责人看稿时可推翻） |
| P-26 | 风控记录「关联对象」要不要显示成平台订单号：契约 `ref_id` 是对象编号（示例为 UUID），没说返回平台单号 | 按 `ref_type` + `ref_id` 原样显示，末 8 位 + 复制 | 契约线（要显示平台单号需补字段） | 转契约线补（不问负责人）：如要在风控记录里显示平台订单号，`risk_hits` 行需加平台单号字段；不加则维持显示对象编号。 |
| P-25 | 「处理时限」把 `deadline_at`（次日 00:00）显示为前一日 24:00 | 照旧稿显示前一日 24:00 | 负责人 | 已按默认处理（Jev 0.94，待负责人看稿时可推翻） |

旧稿 §7-5、§7-9 已由契约解决，不再列入：
- §7-5「写操作后端还没做」——契约已定：代登记、认领、结案三个操作都已上线（契约里没有 `x-implementation: planned`），都不带 Idempotency-Key，防重复靠 `expected_row_version` CAS 与「同一对象返回原申诉」。画板放开【代登记申诉】【认领】与结案卡，去掉「后端待实现」字样。
- §7-9「剩 N 个工作日」——契约已定：只返回 `deadline_at`，超时口径是契约的 `overdue`（处理中且过了 `deadline_at`）。画板只显示截止时刻与「已超时」标签，不显示剩余工作日（要显示需契约另加字段）。

## 8. 与 10 月旧草稿的差别

契约变化导致的改动：
- 写操作已上线：去掉返回码一览里「后端待实现（B1-03ze）」的说明，列表的【代登记申诉】、详情的【认领】与结案卡都按正常可用画。
- 订单申诉的可申诉范围补「黑名单复核后扣回返利的订单」（D10-1180）：代登记对话框的「订单」选项改为「风控作废返利，或黑名单复核后扣回返利的订单」；订单申诉详情的结论效果改为两种订单都适用（维持：返利状态不变；撤销：申诉恢复差错单作废与扣回都适用）。
- 被拦请求查找按完整手机号查到结果会写操作日志：查找提示里写明。
- 10403 文案改注出处为契约示例 `msg`（后台字典里没有 `error.10403.admin_permission_denied` 键）。

删掉的内容：
- 「剩 N 个工作日」（契约没有剩余工作日字段，前端也不该自算法定日历）。
- 页脚说明句里「提交后第 3 个工作日 24:00（+08:00）」的取值复述（只保留「内部时限、超时告警、不对申诉人显示」）。
- 旧的「结果未确认，请刷新页面查看」「登记结果未确认，请先核对是否已登记，再决定是否重新提交」两种写法，改为新的「结果未知」画法。
- 返回码一览里「返回原申诉」一行按 created_at / 登记人推断的默认做法（推断不可靠，改为一律打开返回的申诉，待 P-06 定）。

新增的状态（12 张）：列表加载中 / 读取出错 / 无权限，详情加载中 / 读取出错 / 无权限，结案选维持（不需额外权限与动态码），认领、结案、代登记各一张结果未知，认领、结案各一张「结果未知后确认已生效」。返回码一览加「已结案」页签一行，结果未知、加载、出错、无权限各行改指新画板。

其他：`fix-adm-tables.py` 按规范把代登记对话框里查找结果表的读屏名改为对话框标题（原为「查找结果 · 被拦截的请求」），并调整了表格行内按钮的属性顺序；不影响画面。

第 1 轮对抗评审后（2026-11-15）的改动：
- 列表样例按 `created_at` 倒序重排（…3e4fa005 在 …3e4fa001 前），用这张列表作底图的画板一并改。
- 查询小狸的侧栏改为「用户与订单：用户查询、订单查询 / 数据：报表 / 系统：操作日志」，与 AdmPoolNoPerm、AdmUserDetailNoPerm 一致（报表登录即可看，sample-data §10.1，所以保留）。
- 代登记「提交中」的查找区（方式、输入框、【查找】、结果行单选）全部锁定。
- 风控记录「关联对象」改按 `ref_id` 原样显示；账户申诉样例的内部说明改为「这笔订单」（两条命中关联同一笔订单）。
- 「被拦的提现…金额没有冻结」改为「没有建单，撤销后也不自动恢复」（BR-ID-36 细则）；返回码一览去掉无出处的「缺省 5 秒」；结案段补 20001 `fields=[appeal_id]`。
- 样例时限核对：…3e4fa007 / …3e4fa008 / …3e4fa004 的时限都是 09-30 24:00，按样例日历（09-25～27 中秋、10-01～07 国庆放假，10-10 调休上班，与 check-samples.py 同一份）从提交日次日数 3 个工作日得出，彼此自洽，未改。

## 转开发验收

以下是读屏属性方面的意见，设计稿不改，由开发验收时处理：
- 锁定的查找结果表里，复制按钮仍可聚焦。
- 结果未知提示条是 `role="alert"`，出现时焦点应落到【重试】。
- 风控记录里复制按钮的读屏名不统一：账户申诉各张带了时间、规则与类型，订单申诉与被拦请求申诉只有「复制关联对象编号 {编号}」，实现时统一成一种（第 2 轮评审）。

