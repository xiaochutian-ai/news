# Digest 可视化界面设计

## 目标

- 为现有 digest 流程增加一个可视化界面，展示每次运行的关键过程和最终结果。
- 支持查看：
  - 已接入的数据源
  - 每个数据源初始抓取数量
  - 过滤后数量
  - 去重后数量
  - 最终入选数量
  - 最终内容分别来自哪个数据源
- 尽量复用当前 Python + Jinja + 静态 HTML 输出方式，遵守最小化改动原则。

## 现状

- 主流程集中在 `app/main.py` 的 `run_digest()`。
- 当前系统已经会生成：
  - digest HTML：面向最终阅读
  - digest JSON：面向结构化结果
- 当前没有“运行追踪”对象，也没有单独的可视化 dashboard 页面。

## 方案对比

### 方案 A：在现有 digest 页面里直接拼接过程统计

- 做法：继续使用 `digest.html.j2`，在最终晨报页面顶部或底部追加统计信息。
- 优点：
  - 改动最小
  - 复用现有渲染链路
- 缺点：
  - “最终内容展示”和“运行分析”耦合在同一页面
  - 页面语义不清晰，后续继续扩展会让模板变重
  - 不利于区分“给读者看”和“给运营看”的信息

### 方案 B：新增独立 dashboard 页面与 trace 快照

- 做法：在不改主业务边界的前提下，为一次 digest 运行生成结构化 trace JSON，再渲染一份独立 dashboard HTML。
- 优点：
  - 高内聚低耦合，digest 内容页和运营看板职责清楚
  - 易测试，后续可以继续加更多阶段指标
  - 与当前 Jinja 静态页面模式一致，不必引入新框架
- 缺点：
  - 比方案 A 多一个模板和一个数据结构

### 方案 C：引入轻量 Web 应用，支持实时运行态展示

- 做法：增加一个 Flask/FastAPI 服务，页面可触发运行并实时查看每个阶段的进度。
- 优点：
  - 交互性最好
  - 可以真正做到运行中可视化
- 缺点：
  - 引入新的服务实体和运行方式
  - 超出当前仓库复杂度，不符合首版最小改动原则

## 推荐方案

- 采用方案 B：独立 dashboard 页面与 trace 快照。
- 原因：
  - 满足“可视化界面 + 过程详情 + 最终结果展示”的核心诉求
  - 保持当前系统的单机、静态输出、易部署特性
  - 后续如果需要实时化，也可以在 trace 数据结构基础上继续演进

## 设计

### 新增运行追踪模型

- 新增一组仅服务于可视化的模型，记录：
  - 运行基本信息：digest_date、source_date、window_label、generated_at
  - 数据源清单
  - 各阶段总量
  - 各数据源在各阶段的数量分布
  - 最终入选条目及来源、分数、理由
  - 输出文件路径
  - 发布结果

### 追踪采集位置

- 在 `run_digest()` 内采集，不侵入各个 pipeline 模块的现有接口。
- 具体做法：
  - 抓取后统计每个 source 的初始数量
  - 过滤后按 source 重新聚合数量
  - 去重后按 source 重新聚合数量
  - 最终选中后统计各 source 入选数量
- 这样能避免为了 dashboard 改写多个模块签名。

### 输出产物

- 在 `output/drafts/` 额外生成：
  - `YYYY-MM-DD-morning-dashboard.html`
  - `YYYY-MM-DD-morning-dashboard.json`
  - `latest-dashboard.html`
  - `latest-dashboard.json`
- `latest-*` 作为稳定入口，方便本地直接预览。

### 页面结构

- 顶部概览：
  - digest 日期
  - source 日期窗口
  - 数据源数量
  - 原始候选数
  - 过滤后数量
  - 去重后数量
  - 最终入选数量
- 阶段漏斗：
  - 原始抓取 -> 过滤通过 -> 去重保留 -> 最终输出
- 数据源明细表：
  - source 名称
  - raw_count
  - filtered_count
  - deduped_count
  - selected_count
- 最终结果表：
  - 标题
  - 来源
  - 分数
  - 入选理由
  - 原文链接
- 输出与发布区：
  - digest HTML / JSON 链接
  - dashboard JSON 链接
  - publish_status / publish_message

### UI 取舍

- 不引入 JavaScript 框架。
- 保持单页静态 HTML，必要时只使用少量原生样式增强可读性。
- 页面重点是“可解释”和“扫一眼能看懂”，不是复杂交互。

## 数据流

1. `run_digest()` 抓取原始文章
2. 各阶段处理继续按原逻辑执行
3. 在主流程里构建 `trace`
4. 生成 digest HTML/JSON
5. 生成 dashboard HTML/JSON
6. 将 dashboard 的 latest 入口更新到稳定文件名

## 测试

- 为追踪统计增加聚焦测试：
  - source 计数聚合是否正确
  - 各阶段总量是否正确
  - 最终结果中的 source 分布是否正确
- 为 dashboard 持久化增加测试：
  - JSON 是否包含关键字段
  - HTML 是否能渲染核心统计数据

## 风险与处理

- 风险：`run_digest()` 继续膨胀
  - 处理：把 trace 构建与 dashboard 渲染拆到独立模块
- 风险：静态 dashboard 不是“实时运行中”页面
  - 处理：首版先满足“运行结果可视化”，后续再考虑实时模式
- 风险：最终入选前的“去重后数量”容易和“跨天已见过滤”混淆
  - 处理：页面中明确标注阶段含义，区分“去重保留”和“跨天去重后可选”

## 范围边界

- 本次不引入数据库新表。
- 本次不做浏览器中手动触发 digest 运行。
- 本次不做 WebSocket 或实时流式刷新。
- 本次只做本地静态 dashboard 展示与稳定预览入口。
