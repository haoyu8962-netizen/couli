# 后台 · 商品池 · 线框说明（v2026-11-15，待定稿）

> 状态：待负责人看稿，不是开发规格；定稿后另写 design/specs/。契约基线：rebate-platform origin/main a0d03c585（2026-11-14）。画板在本机运行目录与设计画布，不入库。
> 对抗评审：2026-11-15 由全新的只读评审做了两轮，第 1 轮不通过、修改后第 2 轮通过；只剩读屏属性类问题，记在文末「转开发验收」。画板共 62 张，放在管理后台设计画布的「后台第 2 批三页（待定稿）」一页。

本页在 10 月 31 日草稿 r2（33 张画板、21 条待定项，负责人未回复）的基础上，按现在的契约重新核对、修正并补齐状态，共 62 张画板（第 1 轮对抗评审后补 1 张）。画板由生成脚本统一出（与旧稿同一外壳），界面上不出现 BR 编号和错误码。

## 1. 页面与入口

| 项 | 内容 |
| --- | --- |
| 菜单位置 | 侧栏「运营 / 商品池」；面包屑「运营 / 商品池」，进池内后为「运营 / 商品池 / {池名}」 |
| 路由暂名 | 池列表 `product-pools`；池内商品 `product-pools/:pool_id`；入库是池内页上的右侧抽屉，不单独成页 |
| 权限点 | `content.pool`（规划/04 §11.2「商品池、淘礼金池」，二次验证「–」）。9 个操作都挂这一个权限点，契约里没有一个操作要求 `X-Step-Up-Token`，所以本模块不画二次验证弹窗 |
| 谁能看到 | 持有 `content.pool` 的账号（样例：超管、运营小凑）；没有的账号侧栏不显示「商品池」，从链接直接打开时整页无权限（样例：查询小狸）。只有一个权限点，不存在「能看不能改」的只读态 |
| 需求与规则 | 01 F-ADM-10（商品池）；BR-PROD-08 ③（池内唯一键与重复入库覆盖并复核）、BR-PROD-05 结果分类 ①（联盟答下架时系统下架）、BR-PROD-03 细则「派生失败的处理」（入库被拒的原因）、BR-PROD-10（平台编码与按平台搜索开关）、BR-PRICE-11（取价时间与刷新）、BR-PRICE-16（价格只来自联盟或刷新，不能手改）、BR-PRICE-08（无返利商品不下发）、BR-TEXT-14（错误话术）、BR-TEXT-17（首页卡片的推广标识，本页不展示）；编排裁定 D10-452、D10-480、D10-485、D10-1059（禁售类目） |
| 是否资金页 | 否，不动余额。契约的 `AdminPoolItem`、`AdminPoolCandidate` 都不带返利字段，所以本页不显示返利金额 |

## 2. 页面上有什么

### 2.1 池列表（`AdmPool`）

- 页头：标题「商品池」+ 主按钮【新建商品池】。
- 说明条（信息）：商品池给首页「商品池」模块供货、首页配置里按池 ID 引用；停用的池保留商品和设置，App 读到的是空列表（出处见 §5）。
- 筛选：「状态」下拉（全部状态 / 启用 / 已停用，对应查询参数 `status`，枚举 `AdminProductPoolStatus`）+【查询】【重置】。
- 表格（`role="table"`），按 `created_at` 倒序：
  - 名称：`name`，链接，点了等于【管理商品】；
  - 池 ID：`pool_id`，等宽字 + 复制按钮；
  - 状态：`status`（active → 启用，disabled → 已停用）；
  - 创建时间：`created_at`；最近修改：`updated_at`；
  - 操作：【管理商品】【编辑】。
  - `revision` 不显示，只用作编辑时的版本核对值。
- 分页：`page`、`page_size`（20 / 50 / 100 / 200 四档，契约上限 200）、`total`。

### 2.2 新建 / 编辑池（对话框，`AdmPoolCreate`、`AdmPoolEdit`）

- 名称：`name`，1–64 字，去掉首尾空格后不能为空。
- 状态：单选「启用 / 停用」（`status`，新建默认启用）。
- 池 ID：新建时前端在打开窗口时生成 UUIDv7（小写），只读显示并注明「创建后不能改」；编辑时只读显示 `pool_id`。
- 编辑时副标题「最近修改 {updated_at}」，打开前先用 `adminGetProductPool` 取最新 `name`、`status`、`revision`。
- 编辑时只提交「动过且与读到的值不同」的项 + `expected_revision`；什么都没改时【保存】置灰。

### 2.3 池内商品（`AdmPoolItems`）

- 页头：返回链接 + 池名 + 状态标签 +【编辑】+ 主按钮【入库商品】；池 ID（可复制）、创建时间、最近修改（`adminGetProductPool`）。
- 停用的池另加一条警告：App 读到的是空列表，商品和设置都保留，也可以继续入库（`AdmPoolItemsFilterEmpty` 上可见）。
- 说明条（信息）：价格与券由系统刷新、不能手改；App 只展示「已上架、在展示时段内、价格在有效期内、有返利」的商品，按排序升序（有效期是 BR-PRICE-11 的配置项 `pool.max_age_sec`，后台读不到当前值，说明条里用 `[待定]` 占位）；联盟返回下架时系统自动下架并写原因；重新上架前先复核。
- 筛选：「状态」（全部 / 上架 / 下架，`status`，枚举 `AdminPoolItemStatus`）。
- 表格（`adminListPoolItems`，`sort` 升序再按 `product_key`）：
  - 商品：图（`image`，占位块）、标题（`title`，两行截断）、平台文字标签（`platform`，沿用后台各页的文字标签画法）、商品 ID（`product_key`）；
  - 券后价：`final_price_fen`（后台金额格式 ¥1,234.56）；副行「券前 ¥{price_fen} · 券 ¥{coupon_fen}」，`coupon_fen = 0` 时写「无券」；
  - 取价时间：`quoted_at`；距现在超过有效期（BR-PRICE-11 `pool.max_age_sec`）时加警告标签「价格过期」+ 小字「App 暂不展示，刷新成功后恢复」；画板上过期的那件（纯牛奶）是按默认值画的样例，见 §7 P-06；
  - 状态：`status`；下架时第二行「原因：{invalid_reason}」，`invalid_reason` 为空时写「手动下架」；上架但现在早于 `start_at` 写「未到展示时段，App 暂不展示」，晚于 `end_at` 写「已过展示时段，App 不再展示」；
  - 展示时段：`start_at` / `end_at` 两行，空值写「不限」；
  - 排序：`sort`，右对齐；
  - 操作：【编辑】【下架】或【上架】【移除】（读屏名称带商品标题）。
- 分页同 2.1。`created_by` 只在编辑抽屉显示。
- 时间格式：表格内的取价时间、展示时段写「MM-dd HH:mm」（省略年份，是有意的，为了窄列；跨年时实现按「yyyy-MM-dd HH:mm」显示），页头、抽屉、池列表写「yyyy-MM-dd HH:mm」，沿用后台各页写法。

### 2.4 编辑商品（右侧抽屉，`AdmPoolItemEdit`）

- 商品摘要（取列表行）：图、标题、平台、商品 ID、状态、券后价、取价时间。
- 排序（`sort`，0 起整数）、开始展示 / 结束展示（`start_at` / `end_at`，日期时间框 + 「不限」勾选 = 提交 null）。
- 记录（只读）：入库时间 `created_at`、入库人 `created_by`（契约只有账号 ID）、最近修改 `updated_at`。
- 只提交改了的项；没改时【保存】置灰。上架 / 下架不在抽屉里，在列表行内操作。

### 2.5 入库抽屉（`AdmPoolImportLink`、`AdmPoolImport` 等）

- 标题「入库商品到「{池名}」」；副标题「每次入库一件商品；价格与券以联盟返回为准」。
- 页签：粘贴链接 / 粘贴口令 / 选品搜索（两种粘贴都提交 `link_text`；是否合并成一个页签见 §7 P-03）。
- 入库设置（三个页签共用）：排序、开始展示、结束展示，三项每次必提（`sort`、`start_at`、`end_at`，「不限」= null），默认 0 / 不限 / 不限；一次入库成功后保留，抽屉关闭后复位。
- 覆盖说明条：已在池里的商品会被这次填写的设置覆盖并复核一次。
- 粘贴：多行文本框（最多 4000 字）+ 提示句；字段下显示错误句；30131、30132 下方给【用商品名搜索】。
- 选品搜索（`adminSearchPoolCandidates`）：平台下拉（淘宝 / 京东 / 拼多多，`platform`）、关键词（1–100 字，`q`）、【搜索】；说明句（来自联盟实时搜索、按联盟顺序、不提供总数、价格是此刻报价、无返利商品也可能出现且入库后 App 不展示）。
- 候选行：图、标题、商品 ID、取价时间（`quoted_at`）、券后价 + 券前 · 券（`final_price_fen`、`price_fen`、`coupon_fen`）、【入库】（提交 `item_ref` 原样回传 + 入库设置）。入库成功后该行变「已入库 · 已上架 / 已下架」，不能再点。
- 底部：「已显示 N 条」+【加载更多】/「正在加载…」/「没有更多了」（`next_cursor` 原样回传；为 null 表示没有更多）+ 会话说明句。
- 已在池中确认（`AdmPoolImportOverwrite`）：选品行的 `product_key` 出现在本页已加载的池内商品里时弹出，对比「池里现在 / 这次提交」，【取消】【覆盖并复核】。

## 3. 操作与接口

后台写操作不带 Idempotency-Key（契约 adminCreateProductPool 描述，04 §6.6）；全部操作不要二次验证；所有写操作服务端同事务记操作日志，前端不另做。

| 操作 | operationId 与方法路径 | 权限点 | 二次验证 | 成功后 | 失败码与显示 |
| --- | --- | --- | --- | --- | --- |
| 池列表 | `adminListProductPools` GET `/admin/v1/product-pools` | `content.pool` | 无 | — | 10001、10403、20001（page_size，不应出现）；读取出错 `AdmPoolError` |
| 新建池 | `adminCreateProductPool` POST `/admin/v1/product-pools` | `content.pool` | 无 | 关窗，提示「已创建「{名称}」」，新行置顶高亮（`AdmPoolCreateOk`） | 20001 `[name]` → `AdmPoolCreateInvalid`；20001 `[pool_id]` 不应出现；20902 只在重试时出现 → 读回（§4.8） |
| 读取一个池 | `adminGetProductPool` GET `/admin/v1/product-pools/{pool_id}` | `content.pool` | 无 | — | 30701 → `AdmPoolNotFound` |
| 改名 / 启停 | `adminUpdateProductPool` PATCH `/admin/v1/product-pools/{pool_id}` | `content.pool` | 无 | 关窗，「已保存」，该行刷新高亮（`AdmPoolEditOk`） | 20001 `[name]` → `AdmPoolEditInvalid`；`[body]` 由按钮置灰规避；20902 → `AdmPoolEditConflict`；30701 → 关窗 + 「内容不存在或已下线」 |
| 池内商品 | `adminListPoolItems` GET `/admin/v1/product-pools/{pool_id}/items` | `content.pool` | 无 | — | 30701 → `AdmPoolNotFound`；读取出错 `AdmPoolItemsError` |
| 选品搜索 | `adminSearchPoolCandidates` GET `/admin/v1/product-pools/candidates` | `content.pool` | 无 | — | 20001 `[cursor]` → 「搜索结果已失效，请重新搜索」并回第 1 页；30131 → 结果区「暂不支持这个链接或平台」；50304 → `AdmPoolImportSearchError`；`search_disabled` → 表 B 子键句、不给【重试】 |
| 入库 | `adminAddPoolItem` POST `/admin/v1/product-pools/{pool_id}/items` | `content.pool` | 无 | 新商品：抽屉顶「已入库：{标题}，已上架」（`AdmPoolImportOk`）；已在池里：`AdmPoolImportOverwriteOk` / `AdmPoolImportOverwriteResult` | 20001 `[link_text]` → `AdmPoolImportInvalid`；`[end_at]` 前端先校验；30131 → `AdmPoolImportUnsupported`；30132 → `AdmPoolImportToken`；30141 → `AdmPoolImportOffShelf`；30143 → 选品行内（`AdmPoolImportMore`）；30147 → `AdmPoolImportBlocked`；30701 → 抽屉顶错误条；50401 → `AdmPoolImportRetry` |
| 改池内商品 | `adminUpdatePoolItem` PATCH `/admin/v1/product-pools/{pool_id}/items/{product_key}` | `content.pool` | 无 | 编辑：「已保存」（`AdmPoolItemEditOk`）；上架：`AdmPoolItemOnlineOk` / `AdmPoolItemOnlineFailed`；下架：「已下架」（`AdmPoolItemOfflineOk`） | 20001 `[end_at]` → `AdmPoolItemEditInvalid`；30147 → `AdmPoolItemOnlineBlocked`；30701 → 「内容不存在或已下线」+ 列表重读；50401 → `AdmPoolItemOnlineRetry` |
| 移出池 | `adminRemovePoolItem` DELETE `/admin/v1/product-pools/{pool_id}/items/{product_key}` | `content.pool` | 无 | 关窗，「已移除「{标题}」」，列表重读（`AdmPoolItemRemoveOk`） | 30701 → 第一次提交「内容不存在或已下线」；重试时按已移除处理 |

所有操作另有 10001（回后台登录）、10403（整页无权限或对话框内错误条）、429 / 42901（按 Retry-After 禁用按钮）、5xx（明确失败，可再提交）。逐码落点见画板 `AdmPoolCodes`（返回码一览）。

## 4. 各状态怎么显示

### 4.1 加载中

- 池列表：表格骨架 4 行，筛选与【新建商品池】可用（`AdmPoolLoading`）。
- 池内商品：表格骨架 5 行，页头与筛选可用（`AdmPoolItemsLoading`）。
- 选品第 1 页：结果区骨架，【搜索】变「正在搜索…」并禁用（`AdmPoolImportSearching`）；加载下一页：已显示的行保留，底部「正在加载…」（`AdmPoolImportLoadingMore`）。只采用最后一次搜索的响应，旧响应丢弃（旧稿复审 S3-3）。

### 4.2 空态

- 池列表没有任何池：`AdmPoolEmpty`（「还没有商品池」+【新建商品池】）。筛选后无结果用同一种状态块，文案「没有符合条件的商品池」+【重置】；样例里两种状态的池都有，没有单画，写法照 `AdmPoolItemsFilterEmpty`。
- 池里没有商品：`AdmPoolItemsEmpty`；筛选后没有：`AdmPoolItemsFilterEmpty`（样例是已停用的「国庆囤货」筛「上架」，同时示意停用池的警告条）。
- 选品第 1 页没有结果：`AdmPoolImportNoResult`（不给推荐，不用池里的商品代替——契约「no fall-back items」）；后续页没有更多：`AdmPoolImportNoMore`。

### 4.3 无权限

`AdmPoolNoPerm`：查询小狸从链接直接打开，整页「当前账号没有这项操作的权限，请联系超级管理员开通」（`error.10403.admin_permission_denied`），侧栏按其权限裁剪（无「商品池」）。写操作途中被撤权：对话框或抽屉内错误条用同一句，内容保留。

### 4.4 读取出错

`AdmPoolError`、`AdmPoolItemsError`：区域内错误块「出了点问题，请稍后再试（trace 后 6 位）」+【重新加载】。池不存在（30701）：`AdmPoolNotFound` 整页「内容不存在或已下线」+【返回商品池列表】（契约没有删除池的操作，只会是链接里的池 ID 不对）。

### 4.5 提交中

对话框 / 抽屉里的输入项全部置灰（保留已填内容），关闭键置灰（读屏名「关闭（提交完成前不可用）」），按钮变「正在创建… / 正在保存… / 正在入库… / 正在移除…」并禁用，按钮上方一句状态说明。画板：`AdmPoolCreateSubmitting`、`AdmPoolEditSubmitting`、`AdmPoolImportSubmitting`、`AdmPoolItemEditSubmitting`、`AdmPoolItemRemoveSubmitting`。行内上架：该行的【上架】变「正在上架…」，同行【编辑】【移除】置灰，状态栏加「正在向联盟复核…」（`AdmPoolItemOnlineSubmitting`）；其他行照常可点。行内下架：在确认气泡里点【下架】后气泡关闭，该行【下架】变「正在下架…」，同行【编辑】【移除】置灰，状态栏加「正在下架…」（`AdmPoolItemOfflineSubmitting`）。选品行入库：只锁这一行的【入库】，其他行可点（未单画）。

### 4.6 校验未通过（20001）

| 操作 | 字段 | 显示 |
| --- | --- | --- |
| 新建 / 编辑池 | `name` | 顶部「填写内容有误，请检查」+ 名称框下「请填写名称：1–64 字，不能只有空格」（`AdmPoolCreateInvalid`、`AdmPoolEditInvalid`） |
| 编辑池 | `body` | 不应出现：没改时【保存】置灰 |
| 新建池 | `pool_id` | 不应出现（前端生成）；出现按 5xx 显示 |
| 入库 | `link_text` | 粘贴内容里不止一件商品：顶部错误条 + 字段下「一次只能入库一件商品，请只留一个链接或口令」（`AdmPoolImportInvalid`） |
| 入库 / 编辑商品 | `end_at` | 前端先校验「结束时间要晚于开始时间」，不发请求、不出顶部错误条（`AdmPoolItemEditInvalid`）；服务端兜底返回时同样标红，另加顶部「填写内容有误，请检查」 |
| 入库 | `sort`、`body`、`[link_text, item_ref, body]` | 前端保证两种来源二选一、排序为非负整数，正常不出现；出现时对应字段标红 + 顶部错误条 |
| 选品搜索 | `q`、`platform` | 前端先校验，不出现 |
| 选品搜索 | `cursor` | 「搜索结果已失效，请重新搜索」，清空结果回到第 1 页 |
| 两个列表 | `page_size` | 不应出现（只给四档） |

### 4.7 并发冲突

- 编辑池 20902（`data.resource=product_pool`）：`AdmPoolEditConflict`。重新读取后，用户动过的项保留用户的值，没动过的项换成最新值；再保存只发「动过且与最新值不同」的项 + 新的 `revision`；背后列表的该行同时刷新（旧稿 §7 第 19 项，见 §7 P-19）。提示句的拼法：「你改过的{字段}保留你填的；{字段}已换成最新的值」，两项都动过时只说「你改过的内容都保留了，请核对后再保存」，都没动过时只说「已换成最新的值」（草拟，旧稿复审 S3-2）。
- 新建池 20902：只会在重试时出现（同一 `pool_id` 已存在），见 §4.8。
- 池内商品（`adminUpdatePoolItem`、`adminAddPoolItem`、`adminRemovePoolItem`）契约没有版本核对，后提交的覆盖先提交的，不会返回 20902；30701 表示条目已被别人移除（见 §7 P-24）。

### 4.8 结果未知

画法统一：请求发出后网络中断、超时或答复读不出时，对话框 / 抽屉保持打开并锁定（输入项置灰、保留已填内容），顶部一条警告提示条说明结果未知，关闭键置灰（读屏名「关闭（结果确认前不可用）」），底部只有【去列表核对】（关闭并重新读取列表）和【重试】（原样重发）。不自动重试，不提供改完再提交。行内上架 / 下架没有表单：该行状态栏换成「结果未知」标签 +「{上架/下架}请求没有收到答复」，操作栏只剩【重试】【去列表核对】，同行【编辑】【移除】【上架/下架】都不可用，页顶另有一条警告说明。

| 写操作 | 画板 | 原样重发为什么安全（契约依据） | 重试后可能的回应与显示 |
| --- | --- | --- | --- |
| 新建池 | `AdmPoolCreateUnknown` | 池 ID 由前端在打开窗口时生成、每次重试复用；同一 ID 已存在时返回 20902 且什么都不写（adminCreateProductPool 描述：「the id is what makes a retry safe」） | 200：按已创建处理；20902：用 `adminGetProductPool` 读回，一律按「已创建」显示读到的最新值——池 ID 是这次打开窗口时生成的，已存在就说明上次建成了，之后若被别人改过就显示改后的值（这条判断是前端默认，见 §7 P-22） |
| 改名 / 启停 | `AdmPoolEditUnknown` | 带同一个 `expected_revision`：上次若已保存，版本已加 1，重发返回 20902 且不改（adminUpdateProductPool 的版本核对） | 200：已保存；20902：重新读取，最新值等于这次提交的值 → 按「已保存」显示（稿上提示条：「上次如果其实已经保存，会读回并按已保存显示」）；不等 → 用 `AdmPoolEditConflict` 的写法，但提示句改为「不确定上次是否保存过，已重新读取最新值，请核对后再决定是否保存」，不说「这次没有保存」 |
| 入库 | `AdmPoolImportUnknown` | 池内唯一键 (app_id, pool_id, product_key)；重复入库用同一份 `sort` / `start_at` / `end_at` 覆盖并复核一次，契约写明「A repeat is therefore safe to retry」 | 上次没写入：照常返回新增或错误码；上次已写入：返回覆盖结果（`AdmPoolImportOverwriteOk` / `OverwriteResult` 的句子），页面按成功处理。注意两次之间若有别人改了这件商品的排序或时段，重试会覆盖回这次填写的值（见 §7 P-23）。选品路径同理（原样回传同一个 `item_ref`），未单画 |
| 改池内商品（排序 / 时段） | `AdmPoolItemEditUnknown` | 契约没有幂等键也没有版本核对；PATCH 的各项都是「设为目标值」，重复提交得到同样的结果，按天然幂等画（契约没有明说，见 §7 P-24） | 200：已保存；30701：条目已被移除，关抽屉、列表重读 |
| 上架 | `AdmPoolItemOnlineUnknown` | 设为目标状态：对已上架的条目再发 `status=online` 不复核、直接返回（契约：「status=online on an item already online」不走复核） | 200 上架：按 `AdmPoolItemOnlineOk`；200 仍下架带原因：按 `AdmPoolItemOnlineFailed`；30147 / 50401：按对应画板 |
| 下架 | `AdmPoolItemOfflineUnknown` | 设为目标状态：`status=offline` 立即下架，重复下架结果相同（契约没有明说重复下架，见 §7 P-24） | 200：按 `AdmPoolItemOfflineOk` |
| 移出池 | `AdmPoolItemRemoveUnknown` | 契约写明：丢响应后重试返回 30701 且什么都不改 | 200：已移除；30701：按「已移除」处理并重读列表。边界：两次请求之间若有人把同一商品重新入库，重试会删掉那条新记录（并入 §7 P-23） |

通用原则：结果未知后重试得到的冲突类回应（20902、30701），都按「上次可能已经生效」处理，不显示成「你的操作没有生效」。

本模块没有二次验证，不涉及令牌能否复用。

明确失败与结果未知的区别：`AdmPoolItemOnlineRetry`（上架时 50401）与 `AdmPoolImportRetry`（入库时 50401）是服务端明确答复「这次什么都没改、可以再试」，画成普通错误条，按钮恢复可点、输入保留，运营可以改了再提交；结果未知是不知道服务端做没做，表单锁定、只能原样重发或去核对。

### 4.9 其他错误码

入库被拒：30131（认得出商品但派生不了商品 ID，`AdmPoolImportUnsupported`，下方【用商品名搜索】）、30132（什么都认不出，`AdmPoolImportToken`，【用商品名搜索】按口令「」内或首行商品名预填）、30141（新商品联盟答下架，`AdmPoolImportOffShelf`，说明句提示其他池同一商品也已被系统下架）、30143（选品结果过期且找不回同一件商品，行内 +【重新搜索】）、30147（类目已禁售，`AdmPoolImportBlocked`，说明什么都没写入）、30701（池不存在，抽屉顶错误条、【入库】置灰）、50401（`AdmPoolImportRetry`）。上架被拒：30147（`AdmPoolItemOnlineBlocked`，该行没有任何改动）、50401（`AdmPoolItemOnlineRetry`）。全部码见 `AdmPoolCodes`。

### 4.10 成功后

`AdmPoolCreateOk`、`AdmPoolEditOk`、`AdmPoolImportOk`、`AdmPoolImportOverwriteOk`、`AdmPoolImportOverwriteResult`、`AdmPoolItemEditOk`、`AdmPoolItemOnlineOk`、`AdmPoolItemOfflineOk`、`AdmPoolItemRemoveOk`：主区顶部轻提示（`role="status"`，几秒后消失）或抽屉顶成功条；相关行按返回值替换并浅黄高亮，不整表重拉（移除后重读列表）。入库成功后粘贴框清空、入库设置保留，便于连续入库。

## 5. 文案与出处

「草拟」= 普通界面用词或说明句，08 与字典里没有键，出稿时起草，汇总为 §7 P-15。

| 位置 | 文案 | 出处 |
| --- | --- | --- |
| 池列表说明条 | 商品池给首页的「商品池」模块供货：首页配置里按池 ID 引用。停用的池保留商品和设置，App 读到的是空列表。 | 契约 adminUpdateProductPool（停用池保留商品、读为空）、listPageSectionItems；措辞草拟 |
| 池内说明条 | 价格与券由系统定时向联盟刷新，不能手工改。App 只展示：已上架、在展示时段内、价格在有效期内（[待定：时限取 pool.max_age_sec，后台暂读不到]）、有返利的商品，按排序数字从小到大。联盟返回下架时系统会自动下架……重新上架前会先向联盟复核一次。 | BR-PRICE-11（`pool.max_age_sec`）、BR-PRICE-16、BR-PRICE-08；契约 listPageSectionItems（过期不下发、no_rebate 不下发、排序）、adminListPoolItems（`invalid_reason`）、adminUpdatePoolItem（上架先复核）；措辞草拟 |
| 停用池警告 | 这个池已停用，App 读到的是空列表；池里的商品和设置都保留，也可以继续入库。 | 契约 adminUpdateProductPool、adminAddPoolItem（「Items may be added to a disabled pool」）；措辞草拟 |
| 新建 / 编辑：名称提示与错误 | 1–64 字，只在后台显示；请填写名称：1–64 字，不能只有空格 | 契约 `AdminProductPoolName`（1–64，编排者默认）、20001 `[name]`；措辞草拟 |
| 新建 / 编辑：状态说明 | 首页引用后立即按池里的商品供货；App 读到的是空列表…… | 契约 listPageSectionItems；措辞草拟 |
| 新建：池 ID 说明 | 打开本窗口时生成；创建后不能改 | 契约 adminCreateProductPool（前端生成 UUIDv7、重试复用）；措辞草拟 |
| 派生提示 | 价格过期（标签）/ App 暂不展示，刷新成功后恢复（小字）/ 未到展示时段，App 暂不展示 / 已过展示时段，App 不再展示 | BR-PRICE-11（`pool.max_age_sec`）、契约 listPageSectionItems（`start_at`..`end_at`）；措辞草拟；时限读不到见 §7 P-06 |
| 下架原因 | 原因：{invalid_reason} / 手动下架 | `invalid_reason` 为服务端原文，前端只拼前缀；「手动下架」是推断，见 §7 P-09 |
| 下架确认气泡 | 下架后 App 立即不展示。重新上架要先经联盟复核，可能不通过。 | 契约 adminUpdatePoolItem（offline 立即生效、online 先复核）；措辞草拟；要不要确认见 §7 P-11 |
| 移除确认正文 | 移除后这件商品不再属于这个池……以后要用可以重新入库，会作为新记录。 | 契约 adminRemovePoolItem（删除条目、product_refs 保留）；措辞草拟 |
| 覆盖说明条与确认框 | 如果这件商品已经在这个池里，会用这次填写的排序和展示时段覆盖原来的设置（入库时间和入库人不变），并立即向联盟复核一次…… | 契约 adminAddPoolItem、BR-PROD-08 ③；措辞草拟 |
| 入库结果句 | 已入库：{标题}，已上架。/「{标题}」已在这个池里：排序和展示时段已按这次填写覆盖……/ 已覆盖，但没有上架 | 契约 adminAddPoolItem 200；措辞草拟；新增与覆盖怎么区分见 §7 P-02 |
| 30131 | 暂不支持这个链接或平台 +【用商品名搜索】 | `error.30131`；按钮按 BR-TEXT-14 表 A 30131 行（D10-656） |
| 30132 | 这个链接或口令暂时识别不了 +【用商品名搜索】 | `error.30132`（BR-TEXT-14 表 A，D10-666 ②） |
| 30141 | 商品已下架；说明句「联盟返回这件商品已下架，没有入库。其他池里如果有这件商品，也已被系统下架。」 | `error.30141`；说明句依据契约 adminAddPoolItem（其他条目照样下架），措辞草拟，见 §7 P-20 |
| 30143 | 商品信息已失效，请重新搜索 +【重新搜索】 | `error.30143` |
| 30147 | 商品所在类目已被禁售，不能加入商品池 / 没有上架：商品所在类目已被禁售 | 契约 error-codes.yaml 30147 的含义与动作；字典没有 `error.30147`，见 §7 P-25 |
| 30147 说明句 | 没有入库；如果这件商品已在这个池里，它的排序、展示时段和上下架状态也都没有改动。/ 「{标题}」没有任何改动：仍是下架，原因也没有改写。 | 契约 adminAddPoolItem、adminUpdatePoolItem 的禁售类目段；措辞草拟 |
| 30147 后续 | 可以换一件商品；类目确属误禁时，[待定：禁售类目名单在哪里调整——契约没有维护它的后台接口]（`AdmPoolImportBlocked`、`AdmPoolItemOnlineBlocked` 两处） | error-codes.yaml 30147 动作提到「在禁售类目名单里调整」，但契约没有对应操作，见 §7 P-26 |
| 30701 | 内容不存在或已下线 | `error.30701` |
| 50304 | {platform_name}搜索暂不可用，请稍后再试 / {platform_name}暂不提供搜索，可以粘贴商品链接查返利 | `error.50304`、`error.50304.search_disabled`；后台沿用 App 句子见 §7 P-16 |
| 50401 / 5xx | 出了点问题，请稍后再试（{trace6}） | `error.50401`、BR-TEXT-14 表 A「其他 5xxxx」 |
| 50401 说明句 | 联盟这次没有回应……没有任何改动，仍是下架。可以再点「上架」重试。/ 这次入库没有任何改动，填写的内容都还在。可以稍后再点「入库」重试。 | 契约 adminUpdatePoolItem、adminAddPoolItem（50401 nothing changed, retry）；措辞草拟 |
| 20001 | 填写内容有误，请检查 | `error.20001` |
| 20001 `[link_text]` | 一次只能入库一件商品，请只留一个链接或口令 | 契约 adminAddPoolItem（编排者默认）；措辞草拟 |
| 20001 `[end_at]` | 结束时间要晚于开始时间 | 契约 adminAddPoolItem / adminUpdatePoolItem；措辞草拟 |
| 20001 `[cursor]` | 搜索结果已失效，请重新搜索 | 契约 adminSearchPoolCandidates；措辞草拟 |
| 20902 | 状态已变化，请刷新后重试 | `error.20902` |
| 10403 | 当前账号没有这项操作的权限，请联系超级管理员开通 | `error.10403.admin_permission_denied`（BR-TEXT-14 表 B） |
| 无权限页辅助句 | 你是从链接直接打开的。当前账号没有商品池的权限，所以左侧菜单里不显示「商品池」；需要时请联系超级管理员在「后台账号与权限」里勾选。 | BR-ID-34、规划/04 §11.2（按权限点裁剪菜单）；不露权限点编码，与 `AdmHomeNoPerm` 同一写法；措辞草拟 |
| 粘贴页签提示 | 粘贴一个淘宝、京东或拼多多的商品链接；一次只能一件商品 / 粘贴从淘宝、京东或拼多多复制的整段分享文字；一次只能一件商品 | 三个平台：BR-PROD-03（MVP 只有 taobao、jd、pdd 生成 product_key）；一次一件：契约 adminAddPoolItem 20001 `[link_text]`；措辞草拟，平台范围与 §7 P-10 一起定 |
| 42901 | 操作太频繁，请稍后再试 | `error.42901` |
| 提交中说明 | 请求已发出。完成前不能关闭、取消或重复提交；等待超时仍没有答复时，这里会改为「结果未知」。 | 草拟（沿用后台账号页 `AdmAdminCreateSubmitting` 的句式） |
| 结果未知提示条 | 结果未知：没有收到服务器的答复 / ……点【重试】会按原样再发一次……点【去列表核对】…… | 共用任务书 §2 画法；各句里「不会建出第二个池」「不会重复修改」「不会多出一条」「重试会答内容不存在」分别出自 §4.8 表中的契约依据；措辞草拟 |
| 选品说明句 | 结果来自联盟实时搜索，按联盟的顺序排列，不提供总数。价格是此刻的联盟报价；没有返利的商品也可能出现在这里，入库后 App 不展示它们。 | 契约 adminSearchPoolCandidates；措辞草拟 |
| 会话说明句 | 翻页间隔超过 30 分钟时，联盟搜索会从你要的这一页重新开始去重……页面按商品 ID 合并，同一件商品只显示一次。 | BR-PROD-08 细则「会话异常」、契约 adminSearchPoolCandidates；显示时机见 §7 P-05 |
| 选品无结果 | 没有找到相关商品，换个关键词试试 / 这个关键词没有搜到可以入库的商品…… | 草拟（旧稿复审 S3-4 改句） |
| 空态 / 筛选无结果 | 还没有商品池 / 这个池还没有商品 / 没有符合条件的商品（商品池） | 草拟 |
| 按钮、列名、页签、成功轻提示 | 新建商品池、管理商品、入库商品、覆盖并复核、去列表核对、重试、已创建、已保存、已下架、已移除 等 | 草拟 |
| 改池 · 结果未知后重试遇 20902 且值不相等（没有单独画板，见 `AdmPoolCodes`） | 不确定上次是否保存过，已重新读取最新值，请核对后再决定是否保存 | 草拟 |

## 6. 画板清单

均为 1440 宽；「改过」= 相对 10 月旧稿有改动，「沿用」= 与旧稿逐字节相同。

| 文件名 | 标题 | 画的是什么 | 新画 / 改过 / 沿用 |
| --- | --- | --- | --- |
| AdmPool | 后台 · 商品池 · 列表 | 池列表 | 沿用 |
| AdmPoolEmpty | 后台 · 商品池 · 列表空态 | 还没有池 | 沿用 |
| AdmPoolLoading | 后台 · 商品池 · 列表 · 加载中 | 表格骨架 | 新画 |
| AdmPoolError | 后台 · 商品池 · 列表 · 读取出错 | 区域出错 + 重新加载 | 新画 |
| AdmPoolNoPerm | 后台 · 商品池 · 无权限（查询小狸） | 整页无权限（辅助句不露权限点编码） | 改过 |
| AdmPoolCreate | 后台 · 商品池 · 新建 | 新建对话框 | 沿用 |
| AdmPoolCreateInvalid | 后台 · 商品池 · 新建 · 校验不通过 | 20001 `[name]` | 沿用 |
| AdmPoolCreateSubmitting | 后台 · 商品池 · 新建 · 提交中 | 表单锁定、正在创建 | 新画 |
| AdmPoolCreateUnknown | 后台 · 商品池 · 新建 · 结果未知 | 锁定 + 重试 / 去列表核对 | 新画 |
| AdmPoolCreateOk | 后台 · 商品池 · 新建 · 已创建 | 新行置顶高亮 + 轻提示 | 新画 |
| AdmPoolEdit | 后台 · 商品池 · 编辑 | 编辑对话框 | 沿用 |
| AdmPoolEditInvalid | 后台 · 商品池 · 编辑 · 校验未通过 | 20001 `[name]` | 新画 |
| AdmPoolEditConflict | 后台 · 商品池 · 编辑 · 状态已变化 | 20902 重新读取 | 沿用 |
| AdmPoolEditSubmitting | 后台 · 商品池 · 编辑 · 提交中 | 表单锁定、正在保存 | 新画 |
| AdmPoolEditUnknown | 后台 · 商品池 · 编辑 · 结果未知 | 锁定 + 重试 / 去列表核对 | 新画 |
| AdmPoolEditOk | 后台 · 商品池 · 编辑 · 已保存 | 行刷新高亮 + 轻提示 | 新画 |
| AdmPoolNotFound | 后台 · 商品池 · 池不存在 | 30701 整页 | 沿用 |
| AdmPoolItems | 后台 · 商品池 · 池内商品 | 池内列表（7 件，含各派生提示） | 改过（说明条与过期标签不写时限数值，池内列表类画板同） |
| AdmPoolItemsEmpty | 后台 · 商品池 · 池内空态 | 池里没有商品 | 沿用 |
| AdmPoolItemsFilterEmpty | 后台 · 商品池 · 池内商品 · 筛选无结果 | 已停用的池筛「上架」无结果 + 停用警告 | 新画 |
| AdmPoolItemsLoading | 后台 · 商品池 · 池内商品 · 加载中 | 表格骨架 | 沿用 |
| AdmPoolItemsError | 后台 · 商品池 · 池内商品 · 加载失败 | 区域出错 | 沿用 |
| AdmPoolItemEdit | 后台 · 商品池 · 编辑商品 | 编辑抽屉 | 沿用 |
| AdmPoolItemEditInvalid | 后台 · 商品池 · 编辑商品 · 校验不通过 | 结束早于开始 | 沿用 |
| AdmPoolItemEditSubmitting | 后台 · 商品池 · 编辑商品 · 提交中 | 抽屉锁定 | 新画 |
| AdmPoolItemEditUnknown | 后台 · 商品池 · 编辑商品 · 结果未知 | 抽屉锁定 + 重试 / 去列表核对 | 新画 |
| AdmPoolItemEditOk | 后台 · 商品池 · 编辑商品 · 已保存 | 行刷新高亮 | 新画 |
| AdmPoolItemOnlineSubmitting | 后台 · 商品池 · 上架 · 提交中 | 行内正在上架、同行锁定 | 新画 |
| AdmPoolItemOnlineOk | 后台 · 商品池 · 上架 · 复核通过 | 行按返回值替换 | 沿用 |
| AdmPoolItemOnlineFailed | 后台 · 商品池 · 上架 · 复核没通过 | 200 仍下架带原因 | 沿用 |
| AdmPoolItemOnlineRetry | 后台 · 商品池 · 上架 · 联盟暂时没有回应 | 50401 明确失败可重试 | 沿用 |
| AdmPoolItemOnlineBlocked | 后台 · 商品池 · 上架 · 类目已禁售 | 30147 | 新画 |
| AdmPoolItemOnlineUnknown | 后台 · 商品池 · 上架 · 结果未知 | 行锁定 + 行内重试 / 去列表核对 | 新画 |
| AdmPoolItemOfflineConfirm | 后台 · 商品池 · 下架确认 | 确认气泡 | 沿用 |
| AdmPoolItemOfflineSubmitting | 后台 · 商品池 · 下架 · 提交中 | 行内正在下架、同行锁定 | 新画（评审第 1 轮补） |
| AdmPoolItemOfflineOk | 后台 · 商品池 · 下架 · 已下架 | 行按返回值替换 | 新画 |
| AdmPoolItemOfflineUnknown | 后台 · 商品池 · 下架 · 结果未知 | 行锁定 + 行内重试 / 去列表核对 | 新画 |
| AdmPoolItemRemove | 后台 · 商品池 · 移除商品 | 移除确认 | 沿用 |
| AdmPoolItemRemoveSubmitting | 后台 · 商品池 · 移除商品 · 提交中 | 确认框锁定 | 新画 |
| AdmPoolItemRemoveUnknown | 后台 · 商品池 · 移除商品 · 结果未知 | 确认框锁定 + 重试 / 去列表核对 | 新画 |
| AdmPoolItemRemoveOk | 后台 · 商品池 · 移除商品 · 已移除 | 列表少一件 + 轻提示 | 新画 |
| AdmPoolImportLink | 后台 · 商品池 · 入库 · 粘贴链接 | 入库抽屉就绪 | 沿用 |
| AdmPoolImportSubmitting | 后台 · 商品池 · 入库 · 提交中 | 抽屉锁定 | 新画 |
| AdmPoolImportUnknown | 后台 · 商品池 · 入库 · 结果未知 | 抽屉锁定 + 重试 / 去列表核对 | 新画 |
| AdmPoolImportOk | 后台 · 商品池 · 入库 · 粘贴链接 · 已入库 | 新商品入库成功；背后列表首行新增并高亮，共 8 条 | 新画 |
| AdmPoolImportInvalid | 后台 · 商品池 · 入库 · 校验未通过 | 20001 `[link_text]` | 新画 |
| AdmPoolImportToken | 后台 · 商品池 · 入库 · 口令识别不了 | 30132 | 改过 |
| AdmPoolImportUnsupported | 后台 · 商品池 · 入库 · 不支持的链接 | 30131 | 改过 |
| AdmPoolImportOffShelf | 后台 · 商品池 · 入库 · 商品已下架 | 30141 | 沿用 |
| AdmPoolImportBlocked | 后台 · 商品池 · 入库 · 类目已禁售 | 30147 | 新画 |
| AdmPoolImportRetry | 后台 · 商品池 · 入库 · 暂时失败可重试 | 50401 明确失败可重试 | 新画 |
| AdmPoolImport | 后台 · 商品池 · 入库 · 选品搜索 | 选品第 1 页 | 沿用 |
| AdmPoolImportSearching | 后台 · 商品池 · 入库 · 选品搜索 · 搜索中 | 第 1 页骨架 | 沿用 |
| AdmPoolImportLoadingMore | 后台 · 商品池 · 入库 · 选品搜索 · 正在加载 | 下一页加载中 | 沿用 |
| AdmPoolImportMore | 后台 · 商品池 · 入库 · 选品搜索 · 加载更多 | 第 2 页 + 一行已入库 + 一行 30143 | 改过 |
| AdmPoolImportNoMore | 后台 · 商品池 · 入库 · 选品搜索 · 没有更多了 | `next_cursor` 为 null | 沿用 |
| AdmPoolImportNoResult | 后台 · 商品池 · 入库 · 选品搜索 · 没有结果 | 第 1 页空 | 改过 |
| AdmPoolImportSearchError | 后台 · 商品池 · 入库 · 搜索暂不可用 | 50304 | 沿用 |
| AdmPoolImportOverwrite | 后台 · 商品池 · 入库 · 已在池中 · 确认覆盖 | 覆盖确认 | 沿用 |
| AdmPoolImportOverwriteOk | 后台 · 商品池 · 入库 · 已在池中 · 覆盖并复核通过 | 覆盖并上架；背后列表该行按返回值替换（排序 0、时段不限、取价刷新）挪到第一行 | 改过 |
| AdmPoolImportOverwriteResult | 后台 · 商品池 · 入库 · 已在池中 · 覆盖结果 | 覆盖但复核没通过；背后列表该行按返回值替换并挪到第一行 | 改过 |
| AdmPoolCodes | 后台 · 商品池 · 返回码一览 | 9 个操作的全部返回码与落点（稿上对照表） | 新画 |

没有删除旧画板：33 张旧稿的读写动作都能对上契约里的操作。

## 7. 待定清单

> 2026-11-15 分拣：本节各条先对契约与规划核实现状，再交 TypeSafe Jev 判断（规划/11 §7.1），分三类——「已按默认处理」的由代理按默认做法定，负责人看稿时可以推翻；「转契约线 / 规划补」的不问负责人，画板先照默认画法；「待负责人定」的有 1 条（P-14），负责人已于 2026-11-15 定为「本期要做」。Jev 后的数字是「代理可先按默认做」一问的分数（0–1）。

「旧 §7-n」指 10 月草稿评审页的第 n 项；「契约已定」的条目只记录结论，不再待定。

| 编号 | 是什么 | 画板上的占位或默认画法 | 需要谁定（分拣前的写法，以分拣列为准） | 分拣（2026-11-15） |
| --- | --- | --- | --- | --- |
| P-01（旧 §7-1） | 重复入库提交前要不要先确认。契约仍没有按商品 ID 查池内条目的参数（`adminListPoolItems` 只有 `status` 与分页），也没有只校验不写入的预检 | 只在选品路径、且该商品在本页已加载的池内列表里时弹 `AdmPoolImportOverwrite`；其余靠常驻覆盖说明 | 负责人（要补契约需另开契约任务） | 已按默认处理（Jev 0.90，待负责人看稿时可推翻） |
| P-02（旧 §7-2） | 入库 200 怎么区分新增与覆盖：返回体仍只有条目本身，没有「是否覆盖」字段 | 前端按返回的 `created_at` 早于本次提交判为覆盖 | 负责人 / 契约线 | 已按默认处理（Jev 0.93，待负责人看稿时可推翻） |
| P-03（旧 §7-3） | 「粘贴链接」「粘贴口令」要不要合成一个页签。两者提交同一字段，30132 文案已改成「这个链接或口令…」 | 仍画两个页签 | 负责人 | 已按默认处理（Jev 0.94，待负责人看稿时可推翻） |
| P-05（旧 §7-5 与复审 S2-1） | 选品翻页按商品 ID 合并后，说明句常驻还是只在间隔超 30 分钟时显示；后续页合并后 0 条新增时怎么提示、要不要自动再拉一页 | 说明句常驻；0 条新增时保留已显示的行与【加载更多】，提示句用草拟的「这一页没有新的商品，可以继续加载更多」，不自动再拉 | 负责人 | 已按默认处理（Jev 0.94，待负责人看稿时可推翻） |
| P-06（旧 §7-6） | 「价格过期」「App 暂不展示，刷新成功后恢复」等派生提示（时限是 BR-PRICE-11 的 `pool.max_age_sec`）：契约没有「App 是否展示 / 原因」字段 | `pool.max_age_sec` 是 BR-PRICE-11 的可配置项，后台读不到当前值；画板上纯牛奶的「价格过期」是按默认值画的样例，说明条里时限用 `[待定]` 占位。已转契约线下发该值或给「App 是否展示 / 原因」字段；补上之前的默认画法是「照 BR-PRICE-11 的默认值判断并显示标签」（后台与 App 可能不一致）。另：04 写明 `commission_rate_bp` 为空的条目在下次刷新前也不下发，后台同样看不出 | 负责人 / 契约线 | 转契约线补（不问负责人）：把 `pool.max_age_sec` 的当前值下发给后台，或直接给每件商品「App 是否展示 / 不展示原因」字段；补上前后台按 08 默认值判断「价格过期」。 |
| P-07（旧 §7-7） | 无返利商品被 App 过滤，后台看不出是哪件：契约不给返利字段 | 只在说明条笼统提示 | 负责人 / 契约线 | 转契约线补（不问负责人）：并入上一条：「不展示原因」里给出「无返利」。 |
| P-08（旧 §7-8） | 入库人只有账号 ID（`created_by`），契约没有账号名 | 编辑抽屉原样显示 ID | 负责人 / 契约线 | 转契约线补（不问负责人）：池内商品返回入库人名称（现在只有 `created_by` 账号 ID）。 |
| P-09（旧 §7-9） | 下架且 `invalid_reason` 为空时显示「手动下架」是推断 | 显示「手动下架」 | 负责人 | 已按默认处理（Jev 0.92，待负责人看稿时可推翻） |
| P-10（旧 §7-10） | 选品平台下拉列哪些平台（契约 `platform` 是全量平台编码） | 只列淘宝、京东、拼多多 | 负责人 | 已按默认处理（Jev 0.86，待负责人看稿时可推翻） |
| P-11（旧 §7-11） | 下架要不要先确认 | 画了确认气泡 `AdmPoolItemOfflineConfirm` | 负责人 | 已按默认处理（Jev 0.94，待负责人看稿时可推翻） |
| P-12（旧 §7-12） | 新建窗口里显示池 ID | 显示并注明创建后不能改 | 负责人 | 已按默认处理（Jev 0.91，待负责人看稿时可推翻） |
| P-13（旧 §7-13） | 停用的池正好是信息流备用池（`feed.fallback_pool_id`）时要不要特别提醒；本页读不到这个配置 | 只写通用后果 | 负责人 | 已按默认处理（Jev 0.89，待负责人看稿时可推翻） |
| P-14（旧 §7-14） | 需求有、契约没有的功能本期做不做：F-ADM-10 主句把「标签、刷新价格与券、自动失效下架」列在本期，后半句又写标签列与官方物料频道「上线后一月内只记目标」，前后不一致；刷新与自动失效按 BR-PRICE-11 由系统自动完成。见 §8.3 | 都不画 | 负责人 | **负责人 2026-11-15 定：标签本期要做**（撤回 2026-10-18 把标签列挪到上线后的写法）。待规划补 04 `pool_items` 的标签列、契约线给商品池接口加标签字段、首页配置与首页读池支持按标签筛选之后，再补标签的画板；商品池页其余部分照现稿，不用等。官方物料频道入库仍是上线后目标 |
| P-15（旧 §7-15） | 草拟文案待确认：§5 里标「草拟」的说明条、提示句、结果句、按钮与列名；另含池列表说明条要不要写首页卡片的「推广」角标（契约 listPageSectionItems 写明首页卡片都带「推广」，事实已定，后台写不写是界面选择） | 按稿上措辞；不写角标句 | 负责人 | 已按默认处理（Jev 0.95，待负责人看稿时可推翻） |
| P-16（旧 §7-16） | `search_disabled` 沿用 App 用户那句「可以粘贴商品链接查返利」 | 沿用全站同一句 | 负责人 | 已按默认处理（Jev 0.96，待负责人看稿时可推翻） |
| P-18（旧 §7-18） | 无权限稿的样例账号 | 用查询小狸 | 负责人 | 不属于本页的决定，定稿时一并处理（Jev 0.95） |
| P-19（旧 §7-19） | 编辑池冲突后各项取谁的值，以及提示句拼法 | 动过的保留、没动过的换最新；句式见 §4.7 | 负责人 | 已按默认处理（Jev 0.90，待负责人看稿时可推翻） |
| P-20（旧 §7-20 的展示部分） | 30141 时要不要告诉运营「其他池里同一商品也已被系统下架」 | 说明句照提，画板已是条件句「其他池里如果有这件商品，也已被系统下架」（不点名池） | 负责人 | 已按默认处理（Jev 0.87，待负责人看稿时可推翻） |
| P-21（旧 §7-21） | 选品结果里已在池中的商品要不要先标「已在池中」 | 不标，点了才弹确认 | 负责人 | 已按默认处理（Jev 0.92，待负责人看稿时可推翻） |
| P-22 | 新建池重试遇 20902 后怎么判（契约只说「读回」） | 一律按已创建显示读到的最新值（池 ID 由本窗口生成，已存在即上次已建成） | 负责人 / 契约线 | 已按默认处理（Jev 0.90，待负责人看稿时可推翻） |
| P-23 | 结果未知后原样重试会盖掉两次之间别人的改动：入库重试会把别人改过的排序或时段覆盖回这次填写的值；移除重试时，若有人已把同一商品重新入库，会删掉那条新记录 | 照画，不另提示 | 负责人 | 已按默认处理（Jev 0.86，待负责人看稿时可推翻） |
| P-24 | `adminUpdatePoolItem` 没有幂等键也没有版本核对：原样重发按「设为目标值」的天然幂等画，契约没有明说；同理两个人同时改同一件商品时后提交的覆盖先提交的，页面不会报冲突 | 照画（`AdmPoolItemEditUnknown`、`AdmPoolItemOfflineUnknown`） | 契约线确认 | 转契约线补（不问负责人）：`adminUpdatePoolItem` 写明「原样重发安全」（设为目标值的幂等语义），并评估是否加版本核对（现在两人同时改后提交的覆盖先提交的、不报冲突）。 |
| P-25 | 30147 的文案：规划 08 的码表与 BR-TEXT-14 表 A 都还没有登记 30147，字典 `texts.default.json` 也没有 `error.30147`；画板用契约 error-codes.yaml 里的含义句 | 「商品所在类目已被禁售，不能加入商品池」 | 负责人（文案）/ 契约线（补键） | 转规划补（不问负责人）：先在 08 的码表与 BR-TEXT-14 表 A 登记 30147，再由契约线补 `error.30147` 文案键（画板用句：「商品所在类目已被禁售，不能加入商品池」）。 |
| P-26 | 30147 后运营去哪里调整禁售类目名单：error-codes.yaml 的动作提到「在禁售类目名单里调整」，但契约没有维护名单的后台操作 | `AdmPoolItemOnlineBlocked` 上为 [待定] 占位，不画入口 | 负责人 | 转契约线补（不问负责人）：禁售类目名单（表 `category_blocklist`）由谁、在哪里维护：契约没有后台维护操作，error-codes.yaml 的处理动作却让运营「在禁售类目名单里调整」。补维护入口或改掉这句处理动作（要不要做维护页由规划定）。 |
| P-27 | 画板「今天」：沿用 sample-data 的 2026-10-12，新增样例的时间都落在当天 10:05–10:10。例外：`AdmPoolImportMore` 第 2 页取价 10:40 是旧稿有意画的（与第 1 页隔 38 分钟，示意选品会话过期），保留 | — | 派工方登记样例 | 不属于本页的决定，定稿时一并处理（Jev 0.95） |

契约已定、不再待定的旧项：

- 旧 §7-4（无返利商品能不能入库）：契约已定——可以入库，`adminSearchPoolCandidates` 写明无返利商品会出现在选品结果里，App 读池时由 listPageSectionItems 过滤（BR-PRICE-08）。按此画，不加错误。
- 旧 §7-17（草稿按契约而不是旧任务书画）：契约已定——重复入库是覆盖并复核、新建池由前端生成池 ID、标签不在契约里，现契约仍是这样。
- 旧 §7-20 的事实部分：契约已定——新商品被联盟答下架时，其他池里持有这个商品 ID 的条目照样置为下架（adminAddPoolItem 描述）。只剩「要不要告诉运营」，见 P-20。

## 8. 与 10 月旧草稿的差别

### 8.1 契约变化导致的改动

旧稿依据的是 CT-07d 合并前的契约快照；与现契约同一段对比，schema 没有变化，变化都在操作描述与错误码：

1. **新增 30147（禁售类目，编排裁定 D10-1059）**：`adminAddPoolItem` 对新商品和已在池里的商品都会先查禁售类目，命中即什么都不写；`adminUpdatePoolItem` 只在下架 → 上架的复核时查。新画 `AdmPoolImportBlocked`、`AdmPoolItemOnlineBlocked`。
2. **入库的价格异常口径**：新商品联盟答复 `price_status=anomaly` → 50401（拒绝，什么都不写）；已在池里的商品遇到失效引用或价格异常不拒绝，走「覆盖成立、下架、200 带原因」，且只动这一行。旧稿的 50401 说明句「联盟这次没有回应」对新商品不再准确，新画的 `AdmPoolImportRetry` 改用「这次入库没有任何改动」；`AdmPoolImportOverwriteResult` 的画法不变。
3. **30132 文案**：BR-TEXT-14 与字典改为「这个链接或口令暂时识别不了」（D10-666 ②），`AdmPoolImportToken` 已改。
4. **30131 也给【用商品名搜索】**（BR-TEXT-14 表 A 30131 行，D10-656），`AdmPoolImportUnsupported` 已加按钮（选品搜索里的 30131 是平台没有搜索能力，仍只给【改用粘贴链接】）。
5. 契约去掉了各操作的 `x-implementation: planned`（接口已上线），不影响画法。

### 8.2 新增的状态

池列表加载中、读取出错；池内筛选无结果（含停用池警告）；五个写操作各自的提交中、结果未知与成功后（上架 / 下架另有行内的提交中与结果未知）；编辑池校验未通过；入库成功（新商品）、`[link_text]` 校验未通过、30147、50401；上架 30147；返回码一览。共新画 29 张（含第 1 轮对抗评审补的下架提交中）。另按 10 月复审遗留意见改了两处：选品无结果的说明句（S3-4）、`AdmPoolImportMore` 的稿注计数（S3-1）。

### 8.3 与需求的差距（F-ADM-10 有、这 9 个操作没有，均不画成可操作功能）

- **标签**：负责人 2026-11-15 定为本期要做（§7 P-14）。现契约 `AdminPoolItem` 没有标签字段，也没有按标签筛选，本稿暂时没有标签的画板，等规划与契约补上后再画。
- **刷新价格与券（手动）**：契约没有手动刷新单条或全池的操作；价格只由系统刷新（BR-PRICE-11），页面只显示 `quoted_at` 与超时提示。
- **自动失效下架**：由系统在刷新时完成，结果以「下架 · 原因：{invalid_reason}」体现在列表里，后台没有可操作的开关或记录页。
- **官方物料频道入库**：F-ADM-10 写明属上线后一月内，契约没有。
- **淘礼金素材**（F-ADM-10 括注 BR-TEXT-15）：不在这 9 个操作里，本页不画。
- 旧稿已删、仍不画的：批量上下架 / 打标签、平台与价格筛选、按标题或商品 ID 搜索、池的件数统计与「被引用」、全池刷新状态、多行批量粘贴、导出。

以上是否本期补做见 §7 P-14。

### 8.4 删掉的功能

无。

### 8.5 第 1 轮对抗评审后的修改（2026-11-15）

补下架提交中；统一改池结果未知后重试遇 20902 的说法（并定下通用原则，见 §4.8）；入库成功与两张覆盖结果的背后列表按返回值刷新；时限不再写数值，改引 BR-PRICE-11 `pool.max_age_sec`；无权限页不露权限点编码；返回码一览拆开改池 20902、补改池内商品 50401 的边界；补粘贴页签提示的出处、移除重试的边界、时间格式与样例时间例外的说明。

## 9. 转开发验收（读屏属性，第 1 轮对抗评审记下，稿上不改）

1. 入库抽屉的页签（粘贴链接 / 粘贴口令 / 选品搜索）不是 `tablist` / `tab`，键盘聚焦不到。
2. 对话框、抽屉打开时，背后页面的按钮没有 `inert`。
3. 下架确认气泡的焦点归属与 `aria-describedby`。
