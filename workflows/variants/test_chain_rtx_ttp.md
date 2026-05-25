# 链测试·RTX+TTP

> `variants/test_chain_rtx_ttp.json`  
> 由 `test_chain_edit` 改版，二采用 **TTP**（对齐究极），一采与链测试优化版一致。

## 节点链（当前）

```
KSampler Adv（一采 euler cfg5）
  → VAEDecode(9) → RTX 1.5×(20) → 定标 1536×2240(22)
  → TTP 2×2(30,31) → VAEEncode(13) → KSampler Efficient(14, denoise 0.35)
  → VAEDecode(7) → TTP 拼回(36) → RTX 1.5×(21) → Save(8)
```

## 与链测试 `test_chain_edit` 差异

| 链测试 | 本流 |
|--------|------|
| 4x 模型 + 缩放到 1536×2240 | 仅 RTX + 定标 |
| 整图 VAEEncodeTiled + KSampler 30 步 | **TTP** 分块 + Efficient 15 步 |
| 无二采后 RTX | **TTP 拼回后再 RTX** |

## 一采（已与链测试对齐）

- `KSampler Adv. (Efficient)` + **`euler_ancestral`** + cfg **5** + `vae_decode=false`
- 解码 **`VAEDecode`**，接 Adv 输出索引 **3**（勿用 `dpmpp_2m_sde` 一采，易花屏）
- 预览 **#102** = RTX 后（等同究极「一采」）；**#101** = 纯解码对照

## 二采（对齐究极 TTP 段）

- `VAEEncode`（瓦片批次，**禁止**对 TTP 输出再用 `VAEEncodeTiled`）
- `KSampler (Efficient)`：15 步、euler_ancestral、exponential、cfg 6、**denoise 0.35**
- 解码 **`VAEDecode`**，接 Efficient 输出索引 **3**
- TTP：`width_factor=height_factor=2`，`overlap_rate=0.15`，输入须 **1536×2240**（看预览 **#108**）

## 预览节点

| 节点 | 阶段 |
|------|------|
| 101 | ①a 纯 VAE 解码 |
| 102 | ① 一采（RTX 后） |
| 108 | ②b TTP 输入 1536×2240 |
| 103 | ③ TTP 瓦片 batch |
| 104 | ④ 二采解码（拼回前） |
| 105 | ⑤ TTP 拼回 |
| 107 | ⑥ 最终 RTX（= Save） |

## 依赖

- Efficiency Nodes（Adv + Efficient）
- comfyui_ttp_toolset
- Nvidia RTX Nodes

## 可选扩展

需究极完整后处理时，在 **#36 与 #21 之间** 插入 FaceDetailer；默认本流不含，以减耗时与节点复杂度。
