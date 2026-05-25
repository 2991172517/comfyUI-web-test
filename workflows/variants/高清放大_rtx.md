# 高清放大（RTX）— 独立工作流

> `variants/高清放大_rtx.json`  
> **仅超分，不采样、不改提示词、不 Inpaint**

## 原理

与局部重绘 / 文生图不同：RTX Video Super Resolution 在**已有像素**上提分辨率、补细节，**不是** KSampler 扩散重绘。

## 节点链

```
LoadImage → RTXVideoSuperResolution（默认 1.5×）→ SaveImage
```

## Web 端

顶部导航 **「高清放大」** → `/upscale`：上传图片、设倍数、提交。

API overrides 示例：

- `10.image`：上传后的文件名
- `20.resize_type.scale`：放大倍数（如 1.5、2.0）
- 多次放大：多次 queue 本流，或在工作流里串联多个 RTX 节点（需改 JSON）

## 依赖

- NVIDIA RTX + ComfyUI RTX Nodes 插件
