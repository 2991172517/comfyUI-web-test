# civitai_model_parser

Civitai（仅官方 API）与 Shakker 模型链接解析。已集成到 `CustomProject/backEnd`，也可独立运行。

## 独立启动

```bash
cd CustomProject/civitai_model_parser
pip install -r requirements.txt
# 需能 import 上级 backEnd（main.py 已配置 sys.path）
uvicorn main:app --reload --port 8010
```

## API（与主后端一致）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/model-sources/parse?url=` | 解析链接，返回统一 `model` / `versions` |
| GET | `/api/model-sources/version/{site}/{versionId}?modelId=` | 版本详情（Shakker 需 modelId） |
| POST | `/api/model-sources/import` | 下载/导入到 `ComfyUI/models/` |

## 后端模块结构

```
backEnd/
  model_parser/          # 解析核心
    civitai/
    shakker/
    site_router.py
  services/
    model_import_service.py
  routers/
    model_sources.py
  main.py                # include_router(model_sources)
```

## 导入目录约定

- 权重：`ComfyUI/models/checkpoints/` 或 `models/loras/`
- 说明与参考图：`models/{folder}/<模型主文件名>/模型说明.txt`、`preview_01.png` …
