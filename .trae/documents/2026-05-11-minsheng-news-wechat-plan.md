# 民生新闻公众号聚合系统 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: 使用 `subagent-driven-development`（推荐）或 `executing-plans` 按任务执行本计划。步骤使用 checkbox 语法跟踪。

**Goal:** 基于本地 `n8n` 搭建一个晚间民生热点聚合系统，每天 `22:30` 抓取 `19:30` 之后的央媒官方新闻，筛出与百姓生活密切相关的热点，生成公众号晚报式摘要，并支持人工审核与规则达标后的自动发布。

**Architecture:** 以 `n8n` 负责调度、编排、审核流转和微信发布；以仓库内轻量 Python 脚本负责信源采集、标准化、去重、民生相关性打分、稿件生成和本地状态持久化；整体采用单机 Docker 方案，优先少实体、强边界、易维护。

**Tech Stack:** Docker Desktop, `n8n`, Python 3.12, SQLite, Jinja2, 微信公众号接口

---

## Summary

- 推荐方案：`n8n 主编排 + Python 辅助脚本 + SQLite 本地状态库 + 公众号发布`
- 不推荐首版走纯 `n8n` 大工作流，因为规则、去重和可测试性会迅速失控
- 不推荐首版直接上自研后端服务，因为当前仓库为空，且已存在 `setup.sh` 明确指向本地 Docker + `n8n` 方向
- 首版目标是先做“稳定的晚间晚报”，而不是“全网实时热点平台”

## Current State Analysis

### 仓库现状

- 当前仓库仅有一个文件：`setup.sh`
- `setup.sh` 已经体现出首个重要约束：
  - 部署环境为 macOS 本地
  - 使用 Docker Desktop
  - 启动 `n8n` 容器作为编排引擎
- 当前仓库没有以下内容：
  - 没有信源采集逻辑
  - 没有数据存储
  - 没有去重、排序、摘要或风控逻辑
  - 没有微信接口封装
  - 没有工作流导出文件、环境变量模板或操作文档

### 已确认的产品约束

- 部署形态：本地 `n8n`
- 发布渠道：微信公众号群发
- 运行节奏：每日定时汇总
- 调度时间：每天 `22:30`
- 时间窗口：筛选当天 `19:30` 之后的新闻
- 信源范围：仅央媒官方源
- 稿件形态：晚报式摘要
- 发布模式：同时支持人工审核与自动发布

### 采集可行性判断

- 人民日报可优先接入其图文数据库/版面列表类页面，适合通过固定结构抓取“要闻/民生/社会/经济”等栏目
- 央视新闻可优先接入公开 RSS 与新闻详情页，适合作为首版稳定信源
- 新华社虽然具备更完整的专业供稿能力，但公开自动化接入更偏 B 端供稿体系；首版不作为默认强依赖，只保留扩展位

## Approach Options

### 方案 A：纯 `n8n` 节点实现

- 做法：用 `HTTP Request`、`RSS Read`、`Code`、`IF`、`Merge`、`Wait` 等节点完成全部流程
- 优点：启动最快，视觉化强，不需要额外运行时
- 缺点：
  - 采集解析、去重和规则打分会堆积在 `Code` 节点中
  - 版本管理差，难做单元测试
  - 一旦接入第 3 个以上信源，维护成本明显上升

### 方案 B：`n8n` 主编排 + Python 辅助脚本

- 做法：`n8n` 负责定时调度、串联步骤、审核分支和公众号发布；Python 负责采集、标准化、去重、打分、摘要、HTML 渲染
- 优点：
  - 逻辑边界清楚，符合高内聚低耦合
  - 核心规则可测试，可逐步加信源
  - 保留 `n8n` 的低门槛编排优势
- 缺点：
  - 比纯 `n8n` 多一个脚本层
  - 首版需要处理容器内 Python 运行环境

### 方案 C：自研后端服务 + `n8n` 仅作触发器

- 做法：用 Go/Python 写完整后端服务，`n8n` 只负责调度或完全去掉
- 优点：长期可扩展性最好
- 缺点：
  - 超出当前仓库成熟度
  - 与“本地 `n8n`”方向不一致
  - 首版交付速度最慢

### 推荐决策

- 采用方案 B
- 原因：
  - 与现有 `setup.sh` 的本地 `n8n` 方向一致
  - 兼顾最小化改动与后续可维护性
  - 能把“信源适配”“去重排序”“稿件渲染”“发布审核”拆到清晰边界中

## Proposed Changes

### 目录规划

- 修改：`setup.sh`
- 新增：`docker-compose.yml`
- 新增：`.env.example`
- 新增：`README.md`
- 新增：`app/requirements.txt`
- 新增：`app/main.py`
- 新增：`app/config.py`
- 新增：`app/models.py`
- 新增：`app/storage/state.py`
- 新增：`app/storage/schema.sql`
- 新增：`app/sources/base.py`
- 新增：`app/sources/people_daily.py`
- 新增：`app/sources/cctv.py`
- 新增：`app/sources/registry.py`
- 新增：`app/pipeline/fetch.py`
- 新增：`app/pipeline/filter.py`
- 新增：`app/pipeline/dedupe.py`
- 新增：`app/pipeline/score.py`
- 新增：`app/pipeline/draft.py`
- 新增：`app/pipeline/publish.py`
- 新增：`app/render/html_renderer.py`
- 新增：`app/templates/digest.html.j2`
- 新增：`app/tests/test_filter.py`
- 新增：`app/tests/test_dedupe.py`
- 新增：`app/tests/test_score.py`
- 新增：`app/tests/test_draft.py`
- 新增：`n8n/workflows/evening_digest.json`
- 新增：`n8n/workflows/manual_review.json`
- 新增：`docs/source-policy.md`
- 新增：`docs/publishing-policy.md`
- 新增：`docs/operations.md`

### 文件职责与设计

#### `setup.sh`

- 作用：保留一键启动入口，但从“直接 `docker run n8n`”升级为“启动 `docker compose`”
- 为什么：
  - 需要挂载工作目录、环境变量、SQLite 数据和工作流目录
  - 方便后续增加自定义镜像或依赖
- 怎么做：
  - 检查 Docker Desktop
  - 启动 Docker
  - `docker compose up -d`
  - 打开 `n8n` 本地地址

#### `docker-compose.yml`

- 作用：定义 `n8n` 运行环境与持久化卷
- 为什么：
  - 比单个 `docker run` 更易扩展和复现
- 怎么做：
  - 定义 `n8n` 服务
  - 挂载 `./n8n/workflows`、`./data/n8n`、`./data/app`
  - 注入公众号凭据和业务配置
  - 若 `n8n` 容器内缺少 Python，再增加一个轻量 `worker` 服务供 `n8n` 通过 HTTP 调用；首版优先尝试将脚本与依赖放入自定义 `n8n` 镜像，避免多服务

#### `.env.example`

- 作用：统一配置入口
- 配置项：
  - `WECHAT_APP_ID`
  - `WECHAT_APP_SECRET`
  - `WECHAT_MEDIA_ID_COVER`
  - `PUBLISH_MODE=manual|auto`
  - `SCHEDULE_CRON=30 22 * * *`
  - `WINDOW_START=19:30`
  - `WINDOW_END=22:30`
  - `MIN_SCORE_TO_PUBLISH`
  - `MAX_ITEMS_PER_DIGEST`
  - `PEOPLE_DAILY_ENABLED`
  - `CCTV_ENABLED`

#### `app/models.py`

- 作用：定义统一数据模型
- 核心实体：
  - `RawArticle`
  - `NormalizedArticle`
  - `DigestItem`
  - `DigestDraft`
- 关键字段：
  - `source`
  - `source_id`
  - `title`
  - `url`
  - `published_at`
  - `summary`
  - `tags`
  - `score`
  - `dedupe_key`

#### `app/storage/schema.sql` 与 `app/storage/state.py`

- 作用：保存抓取历史、去重指纹、已发布记录和审核结果
- 为什么：
  - 需要跨天去重
  - 需要避免公众号重复发文
  - 需要记录人工审核/自动发布轨迹
- 表设计：
  - `article_seen`
  - `draft_history`
  - `publish_history`
  - `review_history`
- 决策：
  - 首版使用 SQLite，本地单机足够
  - 不引入 Redis/Postgres，避免额外实体

#### `app/sources/base.py`

- 作用：定义信源适配器接口
- 接口约束：
  - `fetch(window_start, window_end) -> list[RawArticle]`
  - 每个适配器只负责一个官方来源
- 原则：
  - 面向接口编程
  - 新增信源只扩展适配器，不改动管道主逻辑

#### `app/sources/people_daily.py`

- 作用：抓取人民日报当日版面或文章列表，并抽取候选新闻
- 选择策略：
  - 优先读取固定结构的当日列表页
  - 只保留与民生相关的版面或标题
- 首版过滤版面建议：
  - `要闻`
  - `社会`
  - `民生`
  - `经济`
  - `生态`
- 风险：
  - 页面结构调整可能影响解析，因此需要适配器级回归测试

#### `app/sources/cctv.py`

- 作用：抓取央视公开 RSS 与文章页
- 选择策略：
  - 优先使用 `国内新闻`、`社会新闻`、`财经新闻` 等 RSS
  - 补抓详情页以提取正文摘要与发布时间
- 风险：
  - 同一主题可能在不同 RSS 重复出现，因此必须做 URL 和标题双重去重

#### `app/sources/registry.py`

- 作用：信源注册表
- 为什么：
  - 让主流程仅依赖接口数组，而不感知具体实现

#### `app/pipeline/fetch.py`

- 作用：驱动所有适配器抓取窗口内数据并统一标准化
- 输出：`list[NormalizedArticle]`

#### `app/pipeline/filter.py`

- 作用：筛掉与百姓生活弱相关的内容
- 首版规则：
  - 保留命中教育、医疗、养老、就业、住房、交通、消费、食品安全、社会保障、文旅、生态、灾害预警、公共服务等主题的新闻
  - 降权纯外事、纯会议报道、纯国际冲突、纯党建宣传类稿件
  - 保留涉及“政策落地影响民生”的要闻
- 决策：
  - 首版先走“规则优先”，不强依赖大模型
  - 摘要生成可以接入模型，但“是否入选”先由可解释规则决定

#### `app/pipeline/dedupe.py`

- 作用：做当天内和跨天去重
- 去重键：
  - 标题归一化
  - URL 归一化
  - `source + source_id`
- 规则：
  - 同题不同源保留分数更高、信息更完整的一条主记录
  - 在草稿中保留“相关来源”字段，必要时附上补充来源

#### `app/pipeline/score.py`

- 作用：计算民生热点分数并排序
- 评分维度：
  - 民生主题权重
  - 来源权威权重
  - 发布时间新鲜度
  - 可执行/可感知影响程度
  - 覆盖面
- 输出：
  - `score`
  - `reason_codes`
- 决策：
  - 每条新闻必须能解释“为什么被选中”

#### `app/pipeline/draft.py`

- 作用：生成公众号晚报草稿
- 草稿结构：
  - 顶部导语
  - 7-10 条摘要条目
  - 每条包含：标题、2-3 句摘要、影响点、来源、原文链接
  - 尾部说明：仅聚合官方公开报道，按民生相关性筛选
- 决策：
  - 首版默认输出 `7` 条，超过则截断，不足则允许 `5-6` 条发布

#### `app/render/html_renderer.py` 与 `app/templates/digest.html.j2`

- 作用：将草稿渲染成适合公众号图文的 HTML
- 为什么：
  - 公众号群发接口接受结构化图文内容，首版使用 HTML 模板更可控
- 样式要求：
  - 简洁、适合手机阅读
  - 每条新闻之间有明确分隔
  - 原文链接放在每条末尾

#### `app/pipeline/publish.py`

- 作用：对接公众号发布接口
- 模式：
  - `manual`：只生成草稿与待审核记录，由人确认后点击发布
  - `auto`：规则达标后自动群发
- 自动发布门槛：
  - 条目数达到阈值
  - 平均分达到阈值
  - 无黑名单主题
  - 无空摘要或空来源

#### `n8n/workflows/evening_digest.json`

- 作用：主工作流
- 节点步骤：
  - `Cron`：22:30 触发
  - `Execute Command` 或 `HTTP Request`：运行抓取与生成脚本
  - `IF`：判断发布模式
  - `IF`：判断自动发布条件
  - `HTTP Request`：调用公众号接口创建素材/发布
  - `Slack/Email/Webhook` 可选：发送结果通知
- 主工作流只负责编排，不承载复杂业务规则

#### `n8n/workflows/manual_review.json`

- 作用：审核分支工作流
- 流程：
  - 写入待审核草稿
  - 通知人工进入 `n8n` 或指定审核页面确认
  - 发布后回写 `publish_history`

#### `docs/source-policy.md`

- 作用：记录允许接入的官方信源、栏目与过滤边界

#### `docs/publishing-policy.md`

- 作用：记录人工审核和自动发布切换规则、禁发主题与兜底策略

#### `docs/operations.md`

- 作用：记录本地运行、工作流导入、凭据配置、故障排查与恢复步骤

## Data Flow

1. `Cron` 在 `22:30` 触发主流程
2. 读取时间窗口：当天 `19:30-22:30`
3. 各信源适配器并行拉取候选稿
4. 标准化为统一文章模型
5. 规则过滤民生相关内容
6. 对重复稿件聚合与去重
7. 计算民生热点分数并排序
8. 生成晚报草稿和 HTML
9. 进入人工审核或自动发布分支
10. 发布结果写入状态库，保留审计痕迹

## Failure Modes And Handling

- 信源不可达：
  - 单个信源失败不阻断全局
  - 记录失败原因并降级输出
- 候选稿不足：
  - 少于 `5` 条时默认不自动发布，仅进入人工审核
- 页面结构变化：
  - 适配器返回结构化错误，通知人工处理
- 去重误伤：
  - 保存候选池快照，方便人工回看
- 微信接口失败：
  - 标记为“待重试”，不重复生成新稿
- 自动发布风险：
  - 必须有黑名单主题和最低质量阈值

## Assumptions & Decisions

- 不做全网爬虫，首版只接央媒官方源
- 不做实时快讯，首版只做晚间定时报
- 不引入复杂数据库，首版只用 SQLite
- 不引入搜索引擎或向量库，首版规则足够
- 不做前端管理台，首版审核入口依赖 `n8n` 工作流与本地操作文档
- 不直接复刻原文，公众号内容以摘要和原文链接为主，降低版权与重复发布风险
- 默认先开启人工审核；自动发布作为显式配置开关，不默认开启

## Acceptance Criteria

- 每天 `22:30` 自动运行一次
- 能稳定抓到 `19:30` 之后的人民日报和央视新闻候选稿
- 能从候选稿中筛出 `5-10` 条民生相关热点
- 草稿包含标题、摘要、来源和原文链接
- 同题内容不会重复出现在同一篇晚报中
- 人工审核模式可正常生成候选稿且不自动群发
- 自动发布模式仅在满足阈值时群发，否则转人工审核
- 发布与失败记录都能在本地状态库追踪

## Verification Steps

- 配置校验：
  - 使用 `.env.example` 补齐公众号凭据与调度配置
- 适配器校验：
  - 单独运行人民日报与央视适配器，确认窗口过滤正确
- 规则校验：
  - 运行 `filter`、`dedupe`、`score` 单元测试
- 集成校验：
  - 模拟一次 `19:30-22:30` 窗口运行，确认能生成 1 篇完整晚报 HTML
- 发布校验：
  - 在 `manual` 模式下验证只产出草稿
  - 在 `auto` 模式下用测试号验证条件达标才发布
- 回归校验：
  - 连续两天运行，确认跨天去重与历史记录正常

## Implementation Tasks

### Task 1: 运行时与配置基线

**Files:**
- Modify: `setup.sh`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `README.md`

- [ ] 将 `setup.sh` 从单次容器启动改为 `docker compose` 启动
- [ ] 定义 `n8n` 运行、持久化卷和环境变量注入
- [ ] 写清本地启动、停止、重置数据和导入工作流步骤

### Task 2: 统一模型与状态存储

**Files:**
- Create: `app/models.py`
- Create: `app/storage/schema.sql`
- Create: `app/storage/state.py`

- [ ] 定义文章、草稿、发布记录的统一模型
- [ ] 建立 SQLite 表结构和初始化逻辑
- [ ] 提供已见文章、草稿历史、发布历史的读写接口

### Task 3: 信源适配器

**Files:**
- Create: `app/sources/base.py`
- Create: `app/sources/people_daily.py`
- Create: `app/sources/cctv.py`
- Create: `app/sources/registry.py`

- [ ] 抽象统一适配器接口
- [ ] 实现人民日报采集与标准化
- [ ] 实现央视 RSS/详情页采集与标准化
- [ ] 用注册表方式接入主流程

### Task 4: 民生筛选与排序

**Files:**
- Create: `app/pipeline/fetch.py`
- Create: `app/pipeline/filter.py`
- Create: `app/pipeline/dedupe.py`
- Create: `app/pipeline/score.py`

- [ ] 汇总窗口内候选稿
- [ ] 实现民生主题规则过滤
- [ ] 实现当天内和跨天去重
- [ ] 输出可解释评分与排序结果

### Task 5: 草稿生成与渲染

**Files:**
- Create: `app/pipeline/draft.py`
- Create: `app/render/html_renderer.py`
- Create: `app/templates/digest.html.j2`

- [ ] 生成晚报式摘要结构
- [ ] 渲染为公众号可用 HTML
- [ ] 对条目数不足、摘要缺失等情况做降级

### Task 6: 发布与审核流

**Files:**
- Create: `app/pipeline/publish.py`
- Create: `n8n/workflows/evening_digest.json`
- Create: `n8n/workflows/manual_review.json`

- [ ] 封装公众号发布调用
- [ ] 编排人工审核与自动发布分支
- [ ] 失败时保留待重试状态，不重复生成新稿

### Task 7: 测试与运维文档

**Files:**
- Create: `app/tests/test_filter.py`
- Create: `app/tests/test_dedupe.py`
- Create: `app/tests/test_score.py`
- Create: `app/tests/test_draft.py`
- Create: `docs/source-policy.md`
- Create: `docs/publishing-policy.md`
- Create: `docs/operations.md`

- [ ] 为筛选、去重、打分、草稿生成编写聚焦测试
- [ ] 写清信源边界、禁发规则和人工接管流程
- [ ] 写清常见故障排查步骤

## Rollout Strategy

- 第 1 阶段：仅启用人工审核，观察 3-5 天
- 第 2 阶段：在满足稿件数量、平均分、失败率阈值后开启自动发布
- 第 3 阶段：增加新华社或更多官方民生栏目作为扩展信源

