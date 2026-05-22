# CustomProject 启动命令

按顺序启动三个服务：**ComfyUI → 后端 → 前端**。  
以下路径以 ComfyUI 仓库根目录 `E:\ComfyUI-aki-v3\ComfyUI` 为例，请按你的实际路径调整。

## 拉取仓库后的目录

本仓库应放在 **ComfyUI 根目录下**（与官方 `main.py` 同级）：

```text
ComfyUI/                    ← 官方 ComfyUI（git clone）
  main.py
  models/
  output/
  CustomProject/            ← 本控制台（单独 git 仓库亦可）
    backEnd/
    frontEnd/
    workflows/
    config/
```

仅克隆 `CustomProject` 时，也需在本机安装并启动旁边的 ComfyUI，否则控制台无法生图。

---

## 端口一览

| 服务 | 地址 | 说明 |
|------|------|------|
| ComfyUI | http://127.0.0.1:8188 | 生图引擎，必须先启动 |
| 后端 API | http://127.0.0.1:8000 | FastAPI，API 文档：/docs |
| 前端页面 | http://127.0.0.1:5173 | Vue 开发服务器 |

---

## 首次使用（安装依赖）

只需执行一次。

### ComfyUI

使用你平时的 ComfyUI 启动方式即可（整合包启动器、`python main.py` 等）。

### 后端

**PowerShell：**

```powershell
cd E:\ComfyUI-aki-v3\ComfyUI\CustomProject\backEnd
python -m pip install -r requirements.txt
```

**CMD：**

```cmd
cd /d E:\ComfyUI-aki-v3\ComfyUI\CustomProject\backEnd
python -m pip install -r requirements.txt
```

> 目录名是 **`backEnd`**（注意大小写）。Linux / macOS 上 `backend` 会找不到路径。

### 前端

**PowerShell / CMD：**

```powershell
cd E:\ComfyUI-aki-v3\ComfyUI\CustomProject\frontEnd
npm install
```

---

## 日常启动（三个终端）

建议开 **3 个终端窗口**，分别运行下面命令，**不要关闭**，直到使用结束。

### 终端 1：ComfyUI

**PowerShell：**

```powershell
cd E:\ComfyUI-aki-v3\ComfyUI
python main.py
```

若使用 Aki 启动器，用启动器打开 ComfyUI 亦可，只要 `http://127.0.0.1:8188` 能访问。

---

### 终端 2：后端（FastAPI）

**PowerShell：**

```powershell
cd E:\ComfyUI-aki-v3\ComfyUI\CustomProject\backEnd
python main.py
```

**CMD：**

```cmd
cd /d E:\ComfyUI-aki-v3\ComfyUI\CustomProject\backEnd
python main.py
```

启动成功时终端会显示类似：

```text
Uvicorn running on http://127.0.0.1:8000
```

验证：

- 浏览器打开 http://127.0.0.1:8000/docs
- 或 PowerShell：`Invoke-RestMethod http://127.0.0.1:8000/api/health`

---

### 终端 3：前端（Vue + Vite）

**PowerShell / CMD：**

```powershell
cd E:\ComfyUI-aki-v3\ComfyUI\CustomProject\frontEnd
npm run dev
```

启动成功后终端会显示本地地址，一般为：

```text
http://127.0.0.1:5173/
```

在浏览器打开该地址即可使用控制台。

---

## 一键复制（PowerShell 三条命令）

分别粘贴到三个终端执行：

```powershell
# 终端 1 - ComfyUI
cd E:\ComfyUI-aki-v3\ComfyUI; python main.py
```

```powershell
# 终端 2 - 后端
cd E:\ComfyUI-aki-v3\ComfyUI\CustomProject\backEnd; python main.py
```

```powershell
# 终端 3 - 前端
cd E:\ComfyUI-aki-v3\ComfyUI\CustomProject\frontEnd; npm run dev
```

---

## 生产/预览构建（可选）

前端仅本地开发时一般不需要；若要打包静态文件：

```powershell
cd E:\ComfyUI-aki-v3\ComfyUI\CustomProject\frontEnd
npm run build
npm run preview
```

`preview` 默认端口可能与 `5173` 不同，以终端输出为准。

---

## 停止服务

在各终端按 `Ctrl + C` 停止对应进程。建议顺序：**前端 → 后端 → ComfyUI**。

---

## 常见问题

### 页面显示「ComfyUI: 未连接」

1. 确认终端 1 中 ComfyUI 已启动且无报错。
2. 浏览器访问 http://127.0.0.1:8188 是否正常。
3. 若 ComfyUI 端口不是 8188，修改 `CustomProject/backEnd/config.py` 中的 `COMFYUI_URL` 后重启后端。

### 工作流列表为空

将 **File → Export (API)** 导出的 json 放入 **`CustomProject/workflows/`**（或子目录 `workflows/variants/`）：

```text
E:\ComfyUI-aki-v3\ComfyUI\CustomProject\workflows\
E:\ComfyUI-aki-v3\ComfyUI\CustomProject\workflows\variants\
```

列表中的 id 为文件名（不含扩展名），例如 `First_api`、`my_variant`。

### 前端 `npm run dev` 报错

在 `frontEnd` 目录重新安装依赖：

```powershell
cd E:\ComfyUI-aki-v3\ComfyUI\CustomProject\frontEnd
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
Remove-Item -Force package-lock.json -ErrorAction SilentlyContinue
npm install
npm run dev
```

### 后端端口 8000 被占用

修改 `CustomProject/backEnd/config.py` 中的 `API_PORT`，并同步修改 `CustomProject/frontEnd/vite.config.js` 里 `proxy` 的 `target` 端口，然后重启后端与前端。

---

## 相关文件

| 文件 | 作用 |
|------|------|
| `backEnd/config.py` | ComfyUI 地址、API 端口 |
| `backEnd/editable_config.json` | 页面上展示哪些节点/字段 |
| `workflows/*.json`、`workflows/variants/*.json` | API 格式工作流 |
| `frontEnd/vite.config.js` | 前端开发代理 `/api` → 后端 |

更多功能说明见 [README.md](./README.md)。
