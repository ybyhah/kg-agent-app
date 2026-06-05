# 开发说明

## 当前目录职责

- `app.py`
  应用入口，适合本地运行和 Replit 部署

- `src/`
  后端逻辑

- `templates/`
  Flask 模板页面

- `static/`
  样式和后续前端静态资源

- `data/intermediate/`
  放成员 B 的中间 JSON 结果

- `data/kg/`
  放成员 C 的 RDF Turtle 文件

## 建议开发顺序

1. 先保证页面能打开
2. 再保证 `/api/query` 和 `/api/sparql` 可用
3. 再接固定查询工具
4. 最后接大模型、LangGraph 或可视化

## 本地运行

```powershell
cd "D:\cxdownload\kg agent\kg_agent_app"
python app.py
```

浏览器打开：

```text
http://127.0.0.1:5000
```

## 数据接入约定

成员 B 交付：

- `data/intermediate/entities.json`
- `data/intermediate/relations.json`
- `data/intermediate/attributes.json`

成员 C 交付：

- `data/kg/schema.ttl`
- `data/kg/core.ttl`
- `data/kg/aligned.ttl`

## 当前注意事项

- 现在的查询工具还是骨架，后续要改成正式 SPARQL 模板
- 当前页面适合展示，但真实内容还要等 TTL 接入
- 如果 schema 变动，成员 D 要优先改工具层，不要只改前端
