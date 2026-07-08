# 第 3 章复现说明：Buck 参数初步设计

本文档用于复现第 3 章的参数估算表格和图表。第 3 章不重新运行 PLECS 参数扫描，而是基于 Buck 公式生成 L/C/fsw 扫描结果，并读取第 2 章已有 PLECS 汇总数据做基准对照。

## 1. 复现目标

验证 24V 输入、12V/5A 输出 Buck 的初始参数选择：

| 项目 | 数值 |
| --- | --- |
| 输入电压 | 24V |
| 输出电压 | 12V |
| 输出电流 | 5A |
| 等效负载 | 2.4Ω |
| 开环占空比 | 0.5 |
| 基准电感 | 22uH |
| 基准输出电容 | 100uF |
| 基准开关频率 | 200kHz |

第 3 章的核心结论是：22uH、100uF、200kHz 可以作为后续闭环控制章节的基准参数。

## 2. 文件对应关系

| 文件 | 作用 |
| --- | --- |
| `blog/03-buck-parameter-design.md` | 第 3 章教程文章 |
| `scripts/export_parameter_sweep.py` | 生成公式估算 CSV 和图表 |
| `waveforms/03-parameter-sweep-summary.csv` | 参数扫描汇总表 |
| `assets/figures/03-parameter-design-flow.png` | 参数设计路线图 |
| `waveforms/03-base-estimate-vs-plecs.png` | 公式估算与第 2 章 PLECS 基准结果对照 |
| `waveforms/03-inductor-sweep.png` | 不同电感值下的电感纹波估算 |
| `waveforms/03-capacitor-sweep.png` | 不同输出电容下的输出纹波估算 |
| `waveforms/03-frequency-sweep.png` | 不同开关频率下的纹波估算 |
| `waveforms/03-lc-natural-frequency-map.png` | 不同 L/C 组合下的 LC 自然频率估算 |

## 3. 运行环境

| 工具 | 说明 |
| --- | --- |
| Python 3 | 用于运行估算脚本 |
| matplotlib | 用于生成图表 |

本章脚本不依赖 PLECS RPC。它会读取 `waveforms/02-open-loop-summary.csv` 中已有的第 2 章 PLECS 汇总数据，用于和公式估算做基准对照。

## 4. 复现步骤

在仓库根目录运行：

```powershell
python scripts\export_parameter_sweep.py
```

正常输出应包含：

```text
已生成第三章公式估算 CSV 和图表。
说明：本脚本没有重新运行 PLECS 参数扫描，只读取第二章已有 PLECS 汇总数据做基准对照。
base,formula_il_ripple_a=1.36364,formula_vout_ripple_mv=8.52273,...
```

运行后检查以下文件是否更新：

| 文件 | 检查点 |
| --- | --- |
| `waveforms/03-parameter-sweep-summary.csv` | 包含 `base_compare`、`l_sweep`、`c_sweep`、`fsw_sweep` |
| `waveforms/03-base-estimate-vs-plecs.png` | 能看到公式估算和 PLECS 基准对照 |
| `waveforms/03-inductor-sweep.png` | 能看到电感增大后 ΔIL 下降 |
| `waveforms/03-capacitor-sweep.png` | 能看到电容增大后 ΔVout 下降 |
| `waveforms/03-frequency-sweep.png` | 能看到 fsw 提高后纹波下降 |
| `waveforms/03-lc-natural-frequency-map.png` | 能看到不同 L/C 的自然频率变化 |

## 5. 本章使用的公式

等效负载：

> Rload = Vout / Iout

理想 Buck 占空比：

> D = Vout / Vin

电感电流纹波：

> ΔIL = (Vin - Vout) * D / (L * fsw)

输出电容纹波：

> ΔVout_C ≈ ΔIL / (8 * fsw * C)

LC 自然频率：

> f0 = 1 / (2π * sqrt(L * C))

这些公式用于初步估算，不等同于完整硬件设计。实际硬件还要考虑 MOSFET 损耗、二极管或同步管损耗、电感饱和电流、DCR、输出电容 ESR/ESL、热设计和保护策略。

## 6. 基准结果

基准参数为 22uH、100uF、200kHz：

| 指标 | 公式估算 | 第 2 章已有 PLECS 结果 |
| --- | --- | --- |
| 电感电流纹波 | 约 1.36A | 约 1.31A |
| 输出电压纹波 | 约 8.52mV | 约 8.50mV |

这说明公式估算和第 2 章已有仿真结果在量级上匹配，可以支撑第 3 章的参数选择说明。

## 7. 结果边界

第 3 章图表的来源是公式估算，不是 PLECS 参数扫描。读图时需要注意：

| 内容 | 结论边界 |
| --- | --- |
| L/C/fsw 扫描 | 用于看趋势和量级 |
| 公式估算和 PLECS 对照 | 只对基准参数做对照 |
| LC 自然频率 | 用于解释硬启动振铃关系 |
| 启动峰值 | 仍以第 2 章 PLECS 已有结果为准 |

如果需要得到不同 L/C/fsw 组合下的真实暂态峰值，需要在 PLECS 中逐组运行参数扫描，再导出对应波形。本章不把公式估算写成仿真扫描结果。
