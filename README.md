# 民生新闻公众号聚合系统

基于本地 `n8n` + Python 的民生新闻聚合原型。当前版本支持：

- 从人民日报与央视网公开页面抓取候选新闻
- 筛选与百姓生活相关的热点
- 去重、排序并生成一版晨报 HTML/JSON
- 记录草稿和发布状态到本地 SQLite

## 快速开始

```bash
python3 -m pip install -r app/requirements.txt
python3 -m app.main digest
```

## 目录

- `app/`: 业务代码
- `n8n/workflows/`: n8n 工作流样例
- `docs/`: 运维与策略说明
- `output/drafts/`: 生成的稿件
