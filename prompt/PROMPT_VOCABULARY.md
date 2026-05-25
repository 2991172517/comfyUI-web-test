# 提示词词库：WeiLin 与 CustomProject 对接说明

## WeiLin 词库在哪里？

**不是 JSON 文件**，而是 SQLite 数据库（按语言分库）：

| 文件 | 用途 |
|------|------|
| `custom_nodes/WeiLin-Comfyui-Tools/user_data/userdatas_zh_CN_tags.db` | 中文标签词库（组 / 子组 / 标签） |
| `userdatas_zh_CN_danbooru.db` | Danbooru 相关 |
| `userdatas_zh_CN_history.db` | 历史记录 |

表结构（tags 库）：

- `tag_groups` — 一级分组（如「人物」「服饰」）
- `tag_subgroups` — 二级分组
- `tag_tags` — 词条：`text`（插入内容）、`desc`（说明/显示名）

WeiLin 在 ComfyUI 内通过 HTTP API 访问，前缀：`/weilin/prompt_ui/api/`（见 `app/server/prompt_server.py`）。

## 已导出到 CustomProject

运行：

```powershell
cd E:\ComfyUI-aki-v3\ComfyUI\CustomProject
E:\ComfyUI-aki-v3\python\python.exe scripts\export_weilin_tags_to_manifest.py
```

生成：

`prompt/jsonData/weilin_tags_manifest.json` — **manifest v2** 格式，与现有 `manifest.json` 相同 schema。

## CustomProject 词库如何工作？

| 组件 | 路径 |
|------|------|
| 主清单 | `prompt/jsonData/manifest.json`（`config.py` → `VOCABULARY_MANIFEST_PATH`） |
| 用户覆盖 | `backEnd/data/vocabulary_user.json` |
| 检索索引 | `backEnd/data/vocabulary.db`（SQLite FTS，启动时从 manifest 构建） |

### API（前端补全 / 词库管理）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/vocabulary/suggest?q=` | 输入补全 |
| GET | `/api/vocabulary/categories/tree` | 分类树 |
| GET | `/api/vocabulary/categories/{id}/prompts` | 分类下词条 |
| POST | `/api/vocabulary/rebuild` | 强制重建索引 |
| POST | `/api/vocabulary/prompts` | 新增用户词条 |

manifest 单条词条字段：

```json
{
  "id": "…",
  "name": "显示名",
  "value": "插入到提示词的英文 tag 文本",
  "categoryId": "分类 uuid"
}
```

## 并入词库（推荐）

在 **Tag 显示管理**（`/settings/tags`）页使用 **「并入词库 JSON」**：

1. 上传 `weilin_tags_manifest.json` 或其它 manifest v2 JSON
2. 后端自动去重、写入 `manifest.json`、**重建 `vocabulary.db`**
3. **无需重启后端**；刷新分类树即可看到新数据

API：`POST /api/vocabulary/merge-manifest`（multipart 文件）  
预览：`?dry_run=true`（只统计不写入）

去重规则：

- 分类：相同 `id` 已存在则跳过
- 词条：相同 `categoryId` + `value`（忽略大小写）只保留一条

## 其它接入方式

### 方案 A：手动合并 JSON 文件

1. 备份 `prompt/jsonData/manifest.json`
2. 合并 `weilin_tags_manifest.json` 的 `categories` / `prompts`
3. 调用 `POST /api/vocabulary/rebuild` 或重启后端（启动时会 warm index）

### 方案 B：临时切换 manifest 路径

在 `backEnd/config.py` 把 `VOCABULARY_MANIFEST_PATH` 改为 `weilin_tags_manifest.json`，重启并 `rebuild`。

### 方案 C：双 manifest 加载（需改代码）

在 `vocabulary/index.py` 的 `ensure_index` 中循环加载多个 json，合并后再建 FTS。适合同时保留 Prompt Gallery 与 WeiLin 两套数据。

## 与 WeiLin 实时 API 的差异

| | WeiLin | CustomProject |
|--|--------|----------------|
| 存储 | 插件目录下 `.db` | manifest.json + vocabulary.db |
| 界面 | ComfyUI 节点内嵌 UI | 生成页补全 + 词库管理 API |
| 分类 | 组 → 子组 → 标签 | manifest `categories` 树 |
| 同步 | 在 WeiLin UI 改库 | 改 manifest 或 `vocabulary_user.json` 后 rebuild |

**不建议**长期双写：选 manifest 为唯一源，WeiLin 仅作一次性迁移来源。

## 模型路径（本次一并实现）

`config/model_paths.json` 可配置 Checkpoint / LoRA 扫描目录；模型管理页可编辑。  
默认仍为 `ComfyUI/models/checkpoints` 与 `loras`。生图时请在 ComfyUI 的 `extra_model_paths.yaml` 中配置相同路径。
