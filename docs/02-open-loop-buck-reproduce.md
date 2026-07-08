# 第 2 章复现说明：开环 Buck 功率级

本文档用于复现第 2 章的开环 Buck 功率级模型，包含模型、脚本、数据和波形的对应关系。

## 1. 复现目标

验证一个 24V 输入、12V/5A 输出的开环 Buck 功率级：

| 项目 | 目标 |
| --- | --- |
| 输入电压 | 24V |
| 开环占空比 | 0.5 |
| 开关频率 | 200kHz |
| 电感 | 22uH |
| 输出电容 | 100uF |
| 负载 | 2.4Ω |
| 稳态输出 | 约 12V |
| 稳态电感电流 | 约 5A |

## 2. 文件对应关系

| 文件 | 作用 |
| --- | --- |
| `models/plecs/buck_open_loop_24v_12v.plecs` | PLECS 开环 Buck 模型 |
| `scripts/export_open_loop_waveforms.py` | 通过 PLECS RPC 导出数据和波形图 |
| `waveforms/02-open-loop-data.csv` | PLECS 导出的原始波形数据 |
| `waveforms/02-open-loop-summary.csv` | 第二章关键指标汇总 |
| `waveforms/02-open-loop-startup-overview.png` | 启动暂态总览 |
| `waveforms/02-open-loop-mosfet-vds.png` | MOSFET Vds 局部开关波形 |
| `waveforms/02-open-loop-il.png` | 稳态电感电流纹波 |
| `waveforms/02-open-loop-vout.png` | 输出电压启动到稳态波形 |
| `blog/02-open-loop-buck.md` | 教程文章 |

## 3. 运行环境

| 工具 | 说明 |
| --- | --- |
| PLECS | 用于打开和运行 `.plecs` 模型 |
| PLECS RPC Server | 脚本默认连接 `localhost:1080` |
| Python 3 | 用于运行导出脚本 |
| matplotlib | 用于生成波形图 |

注意：仓库不包含 PLECS、MATLAB 或 Simulink 软件本体；这些工具需要读者自行安装并遵守对应商业软件许可。

脚本会把模型复制到 ASCII 工作目录后再调用 PLECS RPC。默认优先使用仓库内 `artifacts/plecs_work/`，如果仓库路径包含中文，则退到系统临时目录；也可以通过 `PLECS_WORK_DIR` 手动指定。

## 4. 复现步骤

1. 打开 PLECS RPC Server，确认 `1080` 端口可用。
2. 在仓库根目录运行：

```powershell
python scripts\export_open_loop_waveforms.py
```

3. 检查控制台输出是否包含以下量级：

| 指标 | 参考结果 |
| --- | --- |
| `startup_vout_peak_v` | 约 20.8V |
| `startup_inductor_current_peak_a` | 约 27.3A |
| `vout_avg_v` | 约 12V |
| `vout_ripple_pp_v` | 约 8.5mV |
| `inductor_current_avg_a` | 约 5A |
| `inductor_current_ripple_pp_a` | 约 1.31A |
| `mosfet_vds_min_v` | 0V |
| `mosfet_vds_max_v` | 24V |

## 5. 离线重绘模式

如果 PLECS RPC 没有启动，但 `waveforms/02-open-loop-data.csv` 已存在，脚本会进入离线重绘模式，使用已有 CSV 重新生成波形图，并明确提示：

```text
无法连接 PLECS RPC，本次使用已有 CSV 重新生成波形图；未重新运行 PLECS 仿真。
```

看到这条提示时，本次运行没有调用 PLECS，也没有产生新的仿真数据。如需重新仿真，请先启动 PLECS RPC Server，再运行导出脚本。

## 6. 第二章结论

开环模型的稳态输出接近 `D * Vin = 12V`，电感电流围绕 5A 呈连续纹波，MOSFET Vds 在 0V 和 24V 之间周期切换。启动阶段的 Vout/IL 过冲来自开环硬启动和 LC 自然响应，不是功率级接线错误。
