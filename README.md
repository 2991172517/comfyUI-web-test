# CustomProject

ComfyUI 旁的轻量控制台：读取 API 工作流、展示关键节点、修改参数并提交到 ComfyUI。

## 目录

```
CustomProject/
  backEnd/            # FastAPI 编排服务 :8000
  frontEnd/           # Vue 3 + Vite + Tailwind + shadcn-vue :5173

workflows/                 # API 工作流（母版 + 子工作流）
  First_api.json           # 母版（只读，勿直接改）
  First_api.meta.json      # 拓扑元数据（LoRA 角色 / Style 绕过规则）
  variants/*.json          # 子工作流（可保存参数）
config/
  prompt_defaults.json     # 全局默认正/负提示追加
```

> **启动命令详见 [START.md](./START.md)**  
> **分发给他人（闭源 exe）**：见 **[docs/打包指南.md](./docs/打包指南.md)**；客户使用见 [docs/使用说明.md](./docs/使用说明.md)

## 拉取后如何启动（速览）

1. **目录**：`CustomProject` 放在 ComfyUI 根目录下（见 [START.md](./START.md)）。
2. **首次**：`backEnd` 执行 `pip install -r requirements.txt`；`frontEnd` 执行 `npm install`。
3. **每次使用**（三个终端，顺序不要反）：
   - ComfyUI 根目录：`python main.py` → http://127.0.0.1:8188
   - `CustomProject/backEnd`：`python main.py` → http://127.0.0.1:8000
   - `CustomProject/frontEnd`：`npm run dev` → http://127.0.0.1:5173（浏览器打开此地址）
4. 前端通过 Vite 把 `/api` 代理到后端；后端再连接 ComfyUI。  
   详细命令、排错、生产构建见 **[START.md](./START.md)**。

## 工作流来源

从 **`CustomProject/workflows/`** 读取（**File → Export (API)** 导出的 json）。

- **母版** `First_api.json`：模板只读；控制台「保存参数」会提示另存子工作流。
- **子工作流** `workflows/variants/{id}.json`：从母版复制，用于 LoRA / Style 调试存档。
- **Style**：当前实现为链末 LoRA `#16`；关闭时运行时绕过（model / 负向 CLIP 改接 `#15`）。元数据预留「正向 CLIP → Style 节点 → KSampler①」的 conditioning 扩展位。

也仍支持 UI 格式 json（若放入该目录），提交时会自动转换为 API；推荐统一使用 API 导出文件。

## 启动

完整步骤（含 PowerShell 一键命令、首次安装、排错）见 **[START.md](./START.md)**。

简要顺序：

1. **ComfyUI**：`python main.py`（仓库根目录）→ http://127.0.0.1:8188  
2. **后端**：`CustomProject/backEnd` → `python main.py` → http://127.0.0.1:8000（目录名是 `backEnd`，不是 `backend`）  
3. **前端**：`CustomProject/frontEnd` → `npm run dev` → http://127.0.0.1:5173（开发时用此地址，不是 8000）  

## 前端结构（shadcn-vue + 路由）

| 路由 | 页面 | 功能 |
|------|------|------|
| `/generate` | 抽卡 | 工作流、提示词预设导入/导出、Style、提交 |
| `/batch` | LoRA 批量 | 角色/Style LoRA 扫参、Style 与单张一致 |
| `/workflows` | 工作流配置 | 子工作流列表 + Checkpoint / LoRA 链增删改（非画布） |
| `/history` | 批量历史 | 历史记录列表与结果网格查看 |
| `/favorites` | 收藏 | 参数收藏、「用此配置生成」跳转并加载 |
| `/settings/prompts` | 提示词 | 全局默认 + **预设库**（正/负/随机组） |
| `/campaign` | 任务计划 | 串行执行多个批量步骤 |

```
frontEnd/src/
  layouts/AppLayout.vue      # 顶栏导航 + 健康状态
  stores/useAppStore.js      # 工作流 / 单张任务 / 模型列表
  stores/useBatchStore.js    # 批量任务 / 历史记录
  views/                     # generate · batch · history · favorites
  components/
    ui/                      # shadcn 基础组件
    layout/                  # WorkflowPicker、PageAlert
    generate/                # 单张生成子组件
    batch/                   # 批量表单、进度、网格、历史列表
    FavoritesPanel.vue
```

## 模型参考图（Checkpoint / LoRA）

将预览图放在 **ComfyUI 模型目录**（与 `GET /api/models/{folder}` 同路径：`ComfyUI/models/checkpoints` 或 `models/loras`）：

```
ComfyUI/models/checkpoints/
  my_ckpt.safetensors
  my_ckpt/                      # 推荐：与模型主文件名同名的文件夹（stem）
    WAI_总结.txt                # 首个 txt：选择框旁 ⓘ 悬停显示全文
    01.png
    cover.jpg
  my_ckpt.safetensors.png       # 备选：模型文件名 + 图片后缀（单张侧挂）

ComfyUI/models/loras/
  style/foo.safetensors
  style/foo/                    # 同上：stem 目录
    note.txt
    ref.png
```

前端选择 Checkpoint / LoRA / Style 时：下拉旁 **ⓘ** 悬停显示说明 txt；右侧显示该目录下全部参考图，支持左右切换与点击放大。API：

- `GET /api/models/{folder}?with_previews=1` — 列表含预览数量
- `GET /api/models/{folder}/previews?name=...` — 预览图列表 + `summary`（首个 txt 说明）
- `GET /api/model-previews/{folder}/{path}` — 读取图片文件

## 可编辑节点配置

编辑 `backEnd/editable_config.json` 可增加/减少「关键节点」类型与字段，例如 LoRA、KSampler、CLIP 等。

## API 概览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | ComfyUI 连接状态 |
| GET | `/api/workflows` | 工作流列表 |
| GET | `/api/workflows/{id}` | 工作流 + 可编辑节点 |
| PUT | `/api/workflows/{id}` | 保存参数到 `user/default/workflows_api/` 对应 json |
| POST | `/api/workflows/{id}/queue` | 提交到 ComfyUI 执行（返回 `prompt_id`、`client_id`） |
| GET | `/api/jobs/{prompt_id}` | 任务状态与输出图片列表 |
| GET | `/api/view` | 图片预览/下载（代理 ComfyUI） |
| DELETE | `/api/jobs/{prompt_id}/outputs` | 删除服务器输出图片 |
| POST | `/api/workflows/{id}/batch/preview` | 预览 LoRA A×B 网格计划 |
| POST | `/api/workflows/{id}/batch` | 启动 A×B 批量（后台串行执行） |
| GET | `/api/batches` | 历史批量记录列表（读 manifest） |
| GET | `/api/batches/{batch_id}` | 批量进度与二维网格结果 |
| POST | `/api/batches/{batch_id}/cancel` | 取消批量 |
| DELETE | `/api/batches/{batch_id}` | 删除本批输出目录与文件 |

## LoRA A×B 批量

前端 **「LoRA 批量」** 页（仅 **API 格式**工作流）：

- **列出工作流内全部 LoRA**：默认固定权重、不参与扫参；勾选「参与扫参」最多 **2 个** 组成 A×B（或单轴 1D）。
- 每个 LoRA 可改模型文件、固定 strength，或配置起始/步进/方向/档位数。
- **Checkpoint** 与参考图在批量页顶部单独配置。
- **Seed**：固定（便于只对比 LoRA）、递增、或每张随机。
- **默认扫参**：LoRA A 从 **0.3 累加**，LoRA B 从 **0.8 累减**（步进 0.1、4×4 档）。
- **命名**：可读策略，如 `g00_简称_w0.30_inc_x_简称_w0.80_dec_seed123`（`inc`/`dec` = 累加/累减）。
- **记录**：每批目录含 `run_config.json`（工作流参数 + 扫参策略）与 `manifest.json`。
- **结果**：行 = A 档位、列 = B 档位的图片网格；文件名与 manifest 含权重与 seed。

页内「参数会影响什么？」说明各参数对最终画面的作用；单张参数区各分组标题下也有简要提示。

### 批量记录存储（无需数据库）

每次批量在磁盘写入：

```
output/custom_batch/<batch_id>/run_config.json  # 本次工作流参数、A/B 扫参策略、命名说明
output/custom_batch/<batch_id>/manifest.json    # 进度 + 每项结果与图片路径
output/custom_batch/<batch_id>/*.png            # ComfyUI 生成的图
```

- `GET /api/batches`：列表（按时间倒序）
- `GET /api/batches/{id}`：详情 + 图片 URL（走 `/api/view` 代理）

前端「批量生成记录」可点击查看历史网格。服务重启后仍可从 manifest 恢复。

### 收藏

- 单张/批量结果点击 **☆** 收藏，再点 **★** 取消。
- **不复制图片**，仅 `user/default/favorites/favorites.json` 记录原图路径 + 完整 `overrides`（Checkpoint、LoRA、提示词、采样等）。
- 收藏页 **「用此配置生成」**：跳转到单张生成页，加载工作流与当时参数，可改提示词后「开始生成」。
- 原图删除后收藏记录仍在，但缩略图不可用。

## 配置

`backEnd/config.py` 可修改 ComfyUI 地址与 API 端口；工作流目录为 `CustomProject/workflows/`（见上文）。
