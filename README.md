# 民生新闻公众号聚合系统

基于本地 `n8n` + Python 的民生新闻聚合原型。当前版本支持：

- 从人民日报与央视网公开页面抓取候选新闻
- 筛选与百姓生活相关的热点
- 去重、排序并生成一版晨报 HTML/JSON
- 记录草稿和发布状态到本地 SQLite

## 快速开始

```bash
./start_dashboard.sh
```

首次启动会自动检查并安装 Dashboard 依赖：

- `Homebrew`
- `python3`
- 项目内 `.venv`
- `app/requirements.txt` 中声明的 Python 包

如果只想手动生成一版稿件，也可以在环境准备完成后执行：

```bash
.venv/bin/python -m app.main digest
```

## 运行本地服务

当前项目的本地服务入口是 Dashboard 服务，用于在浏览器中选择数据源、触发晨报生成并查看产物明细。

### 启动服务

```bash
./start_dashboard.sh
```

脚本会先完成环境检查，再在端口被占用时自动先杀后起。

如果需要手动启动 Dashboard 作为兜底方式，可以执行：

```bash
.venv/bin/python -m app.dashboard_server
```

启动后终端会输出：

```text
dashboard=http://127.0.0.1:8000/
```

默认访问地址：

- Dashboard 首页：`http://127.0.0.1:8000/`
- 设计预览页：`http://127.0.0.1:8000/preview/design-a`

### 自定义端口

如果 `8000` 端口已被占用，可以改用其他端口启动：

```bash
.venv/bin/python -c "from app.dashboard_server import serve_dashboard; serve_dashboard(port=8001)"
```

或者：

```bash
PORT=8001 ./start_dashboard.sh
```

### 服务能力

- 勾选数据源并执行晨报生成
- 选择过滤策略：`宽松 / 标准 / 严格`
- 默认启用关键词黑名单过滤，命中如 `习近平 / 李强 / 习主席 / 总书记` 的文章会被剔除
- 选择去重策略：`保守 / 标准 / 激进`
- 查看 `Raw / Filtered / Deduped / Chosen` 四阶段明细
- 直接访问生成的 HTML/JSON 产物

## 目录

- `app/`: 业务代码
- `n8n/workflows/`: n8n 工作流样例
- `docs/`: 运维与策略说明
- `output/drafts/`: 生成的稿件
