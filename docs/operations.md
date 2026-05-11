# 运维说明

## 本地运行

```bash
python3 -m pip install -r app/requirements.txt
python3 -m app.main digest
```

## 查看产物

- HTML: `output/drafts/<date>-morning-digest.html`
- JSON: `output/drafts/<date>-morning-digest.json`
- SQLite: `data/app/state.db`

## n8n

- 导入 `n8n/workflows/evening_digest.json`
- 确保容器可访问宿主机内的 `/files`
