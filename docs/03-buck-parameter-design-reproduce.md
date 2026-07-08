# 第 3 章复现说明：Buck 参数初步设计

本文档用于复现第 3 章的公式估算结果和 PLECS 参数扫描结果。

第 3 章采用两条证据链：

> 公式估算：先判断 L、C、fsw 对纹波的趋势和量级
> PLECS 参数扫描：再用同一个开环 Buck 模型验证真实波形、纹波和启动峰值

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
| `models/plecs/buck_open_loop_24v_12v.plecs` | PLECS 开环 Buck 模型 |
| `scripts/export_parameter_sweep.py` | 生成公式估算 CSV 和图表 |
| `scripts/export_plecs_parameter_sweep.py` | 通过 PLECS RPC 运行真实参数扫描 |
| `waveforms/03-parameter-sweep-summary.csv` | 公式估算汇总表 |
| `waveforms/03-plecs-parameter-sweep-summary.csv` | PLECS 参数扫描汇总表 |
| `waveforms/03-base-estimate-vs-plecs.png` | 基准参数公式估算与 PLECS 结果对照 |
| `waveforms/03-plecs-inductor-sweep-il.png` | PLECS 不同电感下的稳态电感电流 |
| `waveforms/03-plecs-capacitor-sweep-vout.png` | PLECS 不同输出电容下的稳态输出纹波 |
| `waveforms/03-plecs-frequency-sweep.png` | PLECS 不同开关频率下的纹波对比 |
| `waveforms/03-plecs-lc-startup-peak-map.png` | PLECS 不同 L/C 组合下的硬启动峰值 |

## 3. 运行环境

| 工具 | 说明 |
| --- | --- |
| Python 3 | 用于运行导出脚本 |
| matplotlib | 用于生成图表 |
| PLECS Standalone | 用于运行 `.plecs` 模型 |
| PLECS RPC Server | `scripts/export_plecs_parameter_sweep.py` 默认连接 `localhost:1080` |

仓库不包含 PLECS、MATLAB 或 Simulink 软件本体；这些工具需要读者自行安装并遵守对应商业软件许可。

## 4. 公式估算复现

公式估算不依赖 PLECS。直接在仓库根目录运行：

```powershell
python scripts\export_parameter_sweep.py
```

正常输出应包含：

```text
已生成第三章公式估算 CSV 和图表。
说明：本脚本没有重新运行 PLECS 参数扫描，只读取第二章已有 PLECS 汇总数据做基准对照。
base,formula_il_ripple_a=1.36364,formula_vout_ripple_mv=8.52273,...
```

运行后检查：

| 文件 | 检查点 |
| --- | --- |
| `waveforms/03-parameter-sweep-summary.csv` | 包含 `base_compare`、`l_sweep`、`c_sweep`、`fsw_sweep` |
| `waveforms/03-base-estimate-vs-plecs.png` | 能看到公式估算和基准 PLECS 结果对照 |

## 5. PLECS 参数扫描复现

先启动 PLECS RPC Server，确认 `1080` 端口可用。

如果使用 PLECS Standalone，可以用 PLECS 自带的 `PLECS_server.exe` 启动 RPC。普通应用模式示例：

```powershell
Start-Process -FilePath "<你的 PLECS 安装路径>\PLECS_server.exe" -ArgumentList "-e" -WorkingDirectory "<你的 PLECS 安装路径>" -WindowStyle Hidden
```

不同电脑的安装路径可能不同，应以自己的 PLECS 安装路径为准。如果已经把 PLECS server 安装成系统服务，也可以直接按 PLECS 官方方式启动服务。

确认端口：

```powershell
Test-NetConnection -ComputerName localhost -Port 1080
```

然后运行真实参数扫描：

```powershell
python scripts\export_plecs_parameter_sweep.py
```

正常输出应包含：

```text
运行 PLECS: L10uH_C100uF_f200k
运行 PLECS: L22uH_C100uF_f200k
...
已完成 PLECS 参数扫描并导出 CSV 与波形图。
base,plecs_il_ripple_a=1.30941,plecs_vout_ripple_mv=8.49965,...
```

运行后检查：

| 文件 | 检查点 |
| --- | --- |
| `waveforms/03-plecs-parameter-sweep-summary.csv` | `source` 为 `plecs_rpc_simulation` |
| `waveforms/03-plecs-inductor-sweep-il.png` | 能看到 10uH、22uH、47uH 的 IL 波形 |
| `waveforms/03-plecs-capacitor-sweep-vout.png` | 能看到 47uF、100uF、220uF 的 Vout 纹波 |
| `waveforms/03-plecs-frequency-sweep.png` | 能看到 100kHz、200kHz、300kHz 的纹波趋势 |
| `waveforms/03-plecs-lc-startup-peak-map.png` | 能看到不同 L/C 组合下的启动峰值 |

默认情况下，脚本只提交汇总 CSV 和图表，不把每个工况的完整逐点波形 CSV 放进公开仓库。需要本地导出逐点数据时，可以设置：

```powershell
$env:EXPORT_PLECS_SWEEP_TRACES="1"
python scripts\export_plecs_parameter_sweep.py
```

逐点数据会写入 `artifacts/03_plecs_parameter_sweep_traces/`，该目录不会提交到 GitHub。

## 6. 本章使用的公式

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

## 7. 基准结果

基准参数为 22uH、100uF、200kHz：

| 指标 | 公式估算 | PLECS 参数扫描 |
| --- | --- | --- |
| 电感电流纹波 | 约 1.36A | 约 1.31A |
| 输出电压纹波 | 约 8.52mV | 约 8.50mV |
| 启动 Vout 峰值 | 不由纹波公式估算 | 约 20.8V |
| 启动 IL 峰值 | 不由纹波公式估算 | 约 27.3A |

这说明公式估算和 PLECS 参数扫描在稳态纹波量级上匹配，可以支撑第 3 章的参数选择说明。

## 8. 结果边界

第 3 章的 PLECS 参数扫描仍然是理想器件开环模型下的结果。读图时需要注意：

| 内容 | 结论边界 |
| --- | --- |
| L/C/fsw 扫描 | 用于验证当前理想模型下的趋势和量级 |
| 公式估算 | 用于设计前判断方向，不替代仿真 |
| PLECS 扫描 | 验证当前模型，不等同于真实硬件 |
| 启动峰值 | 反映开环硬启动，需要后续软启动和保护继续处理 |

如果加入 MOSFET 导通电阻、二极管压降、电感 DCR、输出电容 ESR 或同步整流，纹波、损耗和启动峰值都会变化，需要重新运行扫描。
