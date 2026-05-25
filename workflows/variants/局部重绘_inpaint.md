# 局部重绘（手动画蒙版）工作流说明

> API 文件：`variants/局部重绘_inpaint.json`  
> 节点：ComfyUI **内置**，无 WeiLin / Impact / TTP 依赖

---

## 手动画蒙版是什么？

**是。** 常见两种方式：

| 方式 | 谁画 | 结果 |
|------|------|------|
| **ComfyUI 里画** | 用户在 `LoadImage` 节点点 **MaskEditor**，在图上涂抹 | 蒙版存在 ComfyUI，或导出为 mask |
| **网页里画** | 自建前端：Canvas + 画笔，在图片上涂「要改的区域」 | 导出蒙版 PNG，再上传给 ComfyUI |

蒙版规则（本工作流 `LoadImageMask` + `red` 通道）：

- **白色区域** = 要重绘  
- **黑色区域** = 尽量保留原图  

原图、蒙版 **分辨率需一致**。

---

## 数据流（简图）

```
原图 LoadImage ──┐
                 ├── InpaintModelConditioning ── KSampler ── VAEDecode ── SaveImage
蒙版 LoadImageMask ┘         ↑
正向/负向 CLIP ──────────────┘
Checkpoint
```

- **蒙版**：告诉采样「只在哪些像素上加噪声、去噪」  
- **提示词**：告诉模型「画成什么」  
- **denoise（默认 0.55）**：重绘强度，越大改动越大  

---

## 在 ComfyUI 里怎么用（无需 CustomProject 前端）

1. 把 `局部重绘_inpaint.json` 拖进 ComfyUI，或从 variants 目录加载 API 格式。  
2. 节点 **原图**：上传/选择 `inpaint_source.png`（可先随便选一张再换）。  
3. 节点 **蒙版**：  
   - 方式 A：单独上传黑白蒙版 `inpaint_mask.png`（白=重绘）  
   - 方式 B：在原图节点用 Mask Editor 涂好后，把蒙版导出为图接到 `LoadImageMask`  
4. 改 **正向/负向提示词**、**seed**、**denoise**。  
5. Queue Prompt。

---

## CustomProject 控制台（已实现）

顶部导航 **「局部重绘」** → `/inpaint`：

1. 上传原图，在 Canvas 上涂抹红色区域（要重绘的部分）  
2. 填写正/负向提示词、seed、denoise、步数、CFG  
3. 点击「开始局部重绘」→ 自动上传原图+蒙版到 ComfyUI → 提交工作流  
4. **Ctrl+Z** 撤回涂抹；完成后 **滑块对比** 重绘前后  
5. 可选勾选 **RTX 1.5× 放大**（提交 `variants/局部重绘_inpaint_rtx`，需 RTX 插件；默认关）

后端：`POST /api/comfy/upload-image` 转发 ComfyUI `input` 目录。  
前端：`MaskPaintEditor.vue`、`InpaintView.vue`、`useInpaintStore.js`、`ImageBeforeAfterCompare.vue`。

### 是否默认加 RTX？

| | 默认 `局部重绘_inpaint` | 可选 `局部重绘_inpaint_rtx` |
|--|------------------------|------------------------------|
| 输出分辨率 | 与上传原图一致 | 约 1.5× |
| 速度 / 显存 | 更轻 | 更慢，需 RTX |
| 适用 | 修局部、改细节 | 修完后还想整张变大变清晰 |

与究极参考流不同：究极流 **两次 RTX**（中间 + 最终竖图）且含 TTP/修脸；局部重绘 **最多一次 RTX**，且仅在你勾选时启用。

---

## 前端如何实现涂抹蒙版（实现思路）

### UI

1. 用户上传一张 **原图**（`<input type="file">` 或拖拽）。  
2. 用 **Canvas**（或 `fabric.js` / `konva`）叠两层：  
   - 底层：显示原图  
   - 顶层：半透明红色画笔，用户涂「要改的区域」  
3. 提供画笔大小、橡皮、清空。  
4. 点击「生成」时：  
   - 从 Canvas 导出 **蒙版 PNG**（涂过的地方=白 `#FFFFFF`，未涂=黑 `#000000`）  
   - 原图导出为 PNG/JPEG（与 Canvas 同宽高）

### 与 ComfyUI 对接

ComfyUI 提供上传接口（需在 `input` 目录可见）：

```http
POST {COMFYUI_URL}/upload/image
Content-Type: multipart/form-data
字段: image=@文件, overwrite=true
```

返回里的 `name`（及可选 `subfolder`）写入工作流 API：

```json
"10": { "inputs": { "image": "返回的文件名.png" }, "class_type": "LoadImage" }
"11": { "inputs": { "image": "蒙版文件名.png", "channel": "red" }, "class_type": "LoadImageMask" }
```

CustomProject 后端建议新增（尚未实现）：

1. `POST /api/comfy/upload-image` → 转发 ComfyUI upload  
2. `POST /api/workflows/variants/局部重绘_inpaint/queue` 的 body 增加：  
   - `source_image`（multipart 或 base64）  
   - `mask_image`（multipart 或 base64）  
   - 排队前 patch 节点 `10`、`11` 的 `image` 字段  

### 可选简化

- **单文件带 Alpha**：只上传一张 PNG，透明区=重绘；工作流可改为仅用 `LoadImage` 的 **MASK 输出** 接到 `InpaintModelConditioning`，省掉 `LoadImageMask`。网页端用 Canvas 导出 **带 Alpha 的 PNG** 即可。

---

## 关键参数

| 节点 | 参数 | 默认 | 说明 |
|------|------|------|------|
| 30 KSampler | denoise | 0.55 | 0.35 微调，0.7+ 大改 |
| 30 | steps | 28 | 步数 |
| 30 | cfg | 6 | 提示词强度 |
| 1 | ckpt_name | waiIllustriousSDXL_v170 | 需 models/checkpoints 中存在 |

---

## 与「究极参考流」的区别

| | 究极参考流 | 本工作流 |
|--|------------|----------|
| 区域选择 | TTP 自动分块 / FaceDetailer 自动脸框 | **用户手画蒙版** |
| 是否文生图 | 是（从空 latent 开始） | **否**（必须有一张原图） |
| 依赖插件 | 多 | **仅 ComfyUI 核心** |

---

*若要在控制台增加「局部重绘」页，可按上文「前端 Canvas + 后端 upload + patch 节点」分步做，不必改本 JSON 核心结构。*
