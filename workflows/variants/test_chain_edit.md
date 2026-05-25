# 链测试 `test_chain_edit`

> API：`variants/test_chain_edit.json`

## 一采（已对齐究极管线）

```
KSampler Adv → VAEDecode → RTX 1.5× → 4x 模型 → 1536×2240 → 二采 KSampler → 保存
```

- 提示词 / Checkpoint / LoRA：沿用原链测试（`miaomiaoHarem` 等）。
- 预览 **#106** = RTX 后，等同究极界面「一采」；**#101** = 纯 VAE 解码对照。

## 实测：一采采样器与花屏

| 一采 `sampler_name` | 现象 |
|---------------------|------|
| **`euler_ancestral`**（默认） | 正常，与究极一采观感接近 |
| **`dpmpp_2m_sde`** | **易花屏**（同一 VAE、同一解码、同一 RTX） |

结论：**一采全噪声生成（denoise=1）时，采样器算法影响大于「KSampler vs Adv」**；本工作流一采请保持 `euler_ancestral`（与究极一致）。

二采仍为 `dpmpp_2m_sde` + denoise 0.35（在已有图上 img2img，通常无花屏问题）。

## 依赖

- Efficiency Nodes（`KSampler Adv. (Efficient)`）
- Nvidia RTX Nodes（`RTXVideoSuperResolution`）
- 4x 放大模型 `4x_foolhardy_Remacri.pth`
