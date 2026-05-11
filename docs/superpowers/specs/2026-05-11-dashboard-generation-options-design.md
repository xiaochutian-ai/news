# Dashboard 生成选项扩展设计

## 目标

- 将 Dashboard 的“生成选项”扩展为三类：
  - 数据源
  - 过滤策略
  - 去重策略
- 保持现有本地 Dashboard 运行方式不变，只增强表单和后端参数透传。
- 使用固定档位策略，不引入可编辑规则系统，遵守最小化改动原则。

## 背景

- 当前正式 Dashboard 的生成选项只包含数据源复选框，模板位于 `app/templates/_dashboard_generation_options.html.j2`。
- 当前设计预览页也有独立的生成选项模板，位于 `app/templates/_preview_a_generation_options.html.j2`。
- 现有主流程入口是 `app/main.py` 中的 `run_digest()`，目前只接收 `digest_date` 和 `selected_sources`。
- 现有过滤逻辑集中在 `app/pipeline/filter.py`，现有去重逻辑集中在 `app/pipeline/dedupe.py`。

## 需求确认

- 数据源继续沿用当前多选模式。
- 过滤策略采用固定档位，不开放自定义关键词、标签或表达式。
- 去重策略采用固定档位，不开放运行时自定义规则。
- 正式 Dashboard 与设计预览页都要展示相同语义的三个生成选项。

## 方案对比

### 方案 A：固定档位策略分发

- 做法：
  - 表单增加两个 `select` 字段：`filter_strategy` 和 `dedupe_strategy`
  - `run_digest()` 增加对应参数并向 pipeline 透传
  - `filter.py` 与 `dedupe.py` 内部增加轻量策略分发
- 优点：
  - 改动集中，边界清晰
  - 测试简单，易于稳定演进
  - 不引入新实体和新配置文件
- 缺点：
  - 首版灵活性低于规则编辑模式

### 方案 B：规则开关组合

- 做法：
  - 将过滤和去重拆成多个复选开关，由后端组合执行
- 优点：
  - 灵活度高于固定档位
- 缺点：
  - 表单复杂度更高
  - 策略组合数量快速膨胀
  - 首版测试矩阵变大

### 方案 C：可编辑规则

- 做法：
  - 页面允许直接输入关键词、标签、去重规则
- 优点：
  - 灵活性最高
- 缺点：
  - 已接近规则系统
  - 明显超出本次需求边界
  - 需要新增校验、持久化和安全约束

## 推荐方案

- 采用方案 A：固定档位策略分发。
- 原因：
  - 与当前仓库的轻量、本地可运行模式一致
  - 可以把复杂性限制在 pipeline 内部，不污染页面层
  - 后续如果需要更多策略，只需在固定枚举中扩展

## 设计

### 选项模型

- 页面表单保留：
  - `sources`: `list[str]`
- 页面表单新增：
  - `filter_strategy`: `str`
  - `dedupe_strategy`: `str`
- 建议的默认值：
  - `filter_strategy = "standard"`
  - `dedupe_strategy = "standard"`

### 过滤策略档位

- `loose`
  - 命中正向标签或命中正向关键词即保留
  - 不额外执行负向关键词排除
  - 适合希望“多收一点候选”的场景
- `standard`
  - 保持当前行为
  - 先看正向标签，再看正向关键词，最后应用负向关键词排除
- `strict`
  - 需要更强的民生信号
  - 要求正向标签命中，或至少命中两类正向关键词
  - 对噪音更敏感，倾向于少而精

### 去重策略档位

- `conservative`
  - 只按强键去重：标准化标题和标准化 URL
  - 不使用 `source + source_id` 作为额外合并键
  - 适合希望保留更多候选差异的场景
- `standard`
  - 保持当前行为
  - 使用标准化标题、标准化 URL、`source + source_id`
- `aggressive`
  - 在 `standard` 基础上更积极合并
  - 将缺少 URL 但标题高度一致的条目更早视为重复
  - 适合希望压缩重复候选的场景

### 页面行为

- 正式 Dashboard：
  - 在现有数据源复选框下新增两个下拉框
  - 提交表单时一并提交三类生成选项
- 设计预览页：
  - 保持视觉风格不变
  - 语义上与正式 Dashboard 一致，新增同样的两个下拉框
- 结果摘要区：
  - 回显本次选择的 `selected_sources`、`filter_strategy`、`dedupe_strategy`
  - 让用户可以从结果页直观看到本次运行参数

### 后端参数流

1. 页面提交 `sources`、`filter_strategy`、`dedupe_strategy`
2. `app/dashboard_server.py` 从表单中读取这三个值
3. `run_digest()` 新增参数：
   - `selected_sources: list[str] | None = None`
   - `filter_strategy: str = "standard"`
   - `dedupe_strategy: str = "standard"`
4. `run_digest()` 调用过滤与去重时透传策略值
5. 返回结果字典中补充：
   - `filter_strategy`
   - `dedupe_strategy`

### Pipeline 结构

- `app/pipeline/filter.py`
  - 保留现有关键词和标签常量
  - 增加一个策略分发入口，例如 `filter_articles(articles, strategy="standard")`
  - 将当前逻辑收拢为 `standard` 分支
- `app/pipeline/dedupe.py`
  - 增加一个策略分发入口，例如 `deduplicate_articles(articles, strategy="standard")`
  - 将当前逻辑收拢为 `standard` 分支
- `app/main.py`
  - 主流程只负责透传策略，不承载策略细节

## 文件影响

- 修改：
  - `app/main.py`
  - `app/dashboard_server.py`
  - `app/pipeline/filter.py`
  - `app/pipeline/dedupe.py`
  - `app/templates/_dashboard_generation_options.html.j2`
  - `app/templates/_preview_a_generation_options.html.j2`
  - `app/templates/_dashboard_summary.html.j2`
  - `app/templates/_preview_a_summary.html.j2`
  - `app/tests/test_dashboard.py`
- 新增：
  - `app/tests/test_pipeline_strategies.py`

## 测试策略

- Dashboard 模板测试：
  - 验证正式页存在 `sources`、`filter_strategy`、`dedupe_strategy`
  - 验证预览页也存在相同语义的三个选项
  - 验证结果摘要能回显策略值
- Pipeline 策略测试：
  - 验证三种过滤策略在同一批样例数据上的差异
  - 验证三种去重策略在同一批样例数据上的差异
- 主流程透传测试：
  - 验证 `run_digest()` 的返回结果包含策略字段
  - 验证 Dashboard 表单提交后，结果页展示的是本次所选策略

## 风险与处理

- 风险：`run_digest()` 参数继续增长
  - 处理：本次只增加两个字符串参数，不引入更大的配置对象
- 风险：正式页与预览页行为不一致
  - 处理：spec 明确两套生成选项模板都要同步修改，并用测试锁定
- 风险：策略命名与测试用例不一致
  - 处理：统一使用 `loose / standard / strict` 和 `conservative / standard / aggressive`

## 范围边界

- 本次不做自定义关键词编辑。
- 本次不做去重规则文本配置。
- 本次不做策略持久化存储。
- 本次不调整跨天去重的 SQLite 语义。
- 本次不引入新的前端框架或接口层。
