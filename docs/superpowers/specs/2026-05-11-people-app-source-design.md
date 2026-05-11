# 人民日报客户端数据源设计

## 目标

- 为现有晨报系统增加一路独立的 `人民日报客户端` 数据源。
- 保留现有 `人民日报` 数据源，不替换、不改写当前 `people_daily` 行为。
- 复用现有 pipeline、存储和 Dashboard 机制，遵守最小化改动原则。

## 现状

- 现有数据源注册集中在 `app/sources/registry.py`。
- 当前已接入的数据源为：
  - `people_daily`
  - `cctv`
  - `xinhua`
- 当前 `people_daily` 使用 `data.people.com.cn` 版面抓取，不是 `peopleapp.com` 客户端内容。
- Dashboard 和 `run_digest()` 已支持按 source key 选择数据源，因此新增一路 source 可以沿用现有入口。

## 方案对比

### 方案 A：新增独立适配器并并存接入

- 做法：
  - 新增 `app/sources/people_app.py`
  - 在 `registry.py` 中新增 `people_app` 注册项
  - 在配置和 Dashboard 中补充对应开关与选项
- 优点：
  - 不影响现有 `people_daily`
  - 适配器职责清晰，高内聚低耦合
  - 回归风险最低，符合“增加一路数据源”的语义
- 缺点：
  - 多一个文件和一个配置开关

### 方案 B：在 `people_daily.py` 中容纳两套抓取逻辑

- 做法：
  - 继续使用 `people_daily.py`
  - 在同一文件内增加 `peopleapp.com` 的解析与抓取实现
  - 在 `registry.py` 中新增第二个 key 指向同文件中的另一个类
- 优点：
  - 文件数量更少
- 缺点：
  - 一个文件承载两个站点协议，职责边界变差
  - 后续维护时更容易出现结构耦合和误改

## 推荐方案

- 采用方案 A：新增独立适配器并并存接入。
- 原因：
  - 与当前 `CCTVAdapter`、`XinhuaAdapter`、`PeopleDailyAdapter` 的结构一致
  - 变更范围稳定，便于单元测试和回归验证
  - 后续 `peopleapp.com` 如有协议变化，只需局部修改新文件

## 设计

### 适配器边界

- 新增 `PeopleAppAdapter`，文件位于 `app/sources/people_app.py`。
- 该适配器只负责：
  - 抓取 `peopleapp.com` 的公开列表页或公开接口
  - 解析目标日期文章链接和标题
  - 获取详情页并补全文本摘要
  - 输出统一的 `RawArticle`
- 该适配器不负责过滤、打分、去重和持久化。

### 注册与配置

- 在 `app/sources/registry.py` 中新增：
  - `SOURCE_BUILDERS["people_app"] = PeopleAppAdapter`
  - `list_available_sources()` 中增加 `人民日报客户端`
- 在 `app/config.py` 中新增：
  - `people_app_enabled: bool = os.getenv("PEOPLE_APP_ENABLED", "true").lower() == "true"`
- `build_source_adapters()` 在未显式传入 `selected_sources` 时，按配置决定是否启用 `people_app`。

### Dashboard 接入

- 在 `app/dashboard_server.py` 中更新 `default_sources`。
- 新数据源出现在 Dashboard 的勾选列表中，并默认参与运行。
- 运行结果页和阶段明细不需要新增字段，沿用已有 `source` 展示。

### 数据流

1. `Dashboard` 或 `run_digest()` 接收到 `selected_sources`
2. `build_source_adapters()` 根据 key 创建 `PeopleAppAdapter`
3. `PeopleAppAdapter.fetch(source_day_compact)` 返回 `RawArticle` 列表
4. 文章进入现有 `normalize -> filter -> score -> dedupe -> select` 流程
5. 结果进入现有 HTML/JSON 输出和 Dashboard 明细展示

### 文章字段约定

- `RawArticle.source` 固定为 `people_app`
- `RawArticle.source_id` 优先使用详情 URL 中稳定片段；若接口提供 ID，则直接使用接口 ID
- `published_at` 优先取源站字段；没有则从目标日期推导固定时间
- `summary` 和 `content` 优先取详情正文前几段；失败时回退为标题

## 失败兜底

- 列表抓取失败：
  - 该源返回空列表
  - 不中断整次 digest 运行
- 列表解析为空：
  - 视为当天无命中
  - 不抛异常
- 详情抓取失败：
  - 保留文章
  - `summary` 和 `content` 回退为标题
- 发布时间缺失：
  - 使用目标日期固定时间兜底，保证排序稳定
- 重复链接：
  - 适配器内部用 `seen` 去重，避免同源重复入列

## 测试

- `app/tests/test_sources.py`
  - 新增列表解析测试
  - 新增适配器 `fetch()` 测试
  - 更新 source 注册与 source 列表测试
- `app/tests/test_dashboard.py`
  - 断言页面包含 `人民日报客户端` 选项
  - 如默认源行为受影响，补一个默认源包含新 key 的轻量测试

## 范围边界

- 本次不修改数据库 schema
- 本次不修改 dedupe 规则
- 本次不新增领域模型
- 本次不引入真实网络端到端测试
- 本次不优化 Dashboard 对 source key 的中文映射
