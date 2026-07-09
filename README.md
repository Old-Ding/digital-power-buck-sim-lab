# digital-power-buck-sim-lab

这是一个面向数字电源仿真的 Buck 电源学习项目。当前公开仓库只保留已经完成、可以复现的内容：教程文章、PLECS/Simulink 模型、导出脚本、原始数据和波形图。

## 当前规格

| 项目 | 目标值 |
| --- | --- |
| 拓扑 | Buck |
| 输入电压 | 24 V 标称值 |
| 输出电压 | 12 V |
| 输出电流 | 5 A |
| 输出功率 | 60 W |
| 开关频率 | 200 kHz |
| 当前阶段 | 负载突变测试 |

第一阶段只做低压 DC-DC，不涉及市电输入和隔离拓扑。

## 已完成内容

| 章节 | 内容 | 状态 |
| --- | --- | --- |
| 01 | 为什么从 Buck 开始做 MATLAB + PLECS 仿真 | 已完成 |
| 02 | PLECS 搭建开环 Buck 功率级 | 已完成，可复现 |
| 03 | Buck 电感、电容和开关频率参数设计 | 已完成，可复现 |
| 04 | 离散 PI 电压环 | 已完成，可复现 |
| 05 | duty 限幅和抗积分饱和 | 已完成，可复现 |
| 06 | 软启动 | 已完成，可复现 |
| 07 | 保护状态机 | 已完成，可复现 |
| 08 | 负载突变测试 | 已完成，可复现 |

第二章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/02-open-loop-buck.md` |
| 复现说明 | `docs/02-open-loop-buck-reproduce.md` |
| PLECS 模型 | `models/plecs/buck_open_loop_24v_12v.plecs` |
| 导出脚本 | `scripts/export_open_loop_waveforms.py` |
| 原始数据 | `waveforms/02-open-loop-data.csv` |
| 指标汇总 | `waveforms/02-open-loop-summary.csv` |
| 波形图 | `waveforms/02-open-loop-*.png` |

第三章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/03-buck-parameter-design.md` |
| 复现说明 | `docs/03-buck-parameter-design-reproduce.md` |
| 参数估算脚本 | `scripts/export_parameter_sweep.py` |
| PLECS 参数扫描脚本 | `scripts/export_plecs_parameter_sweep.py` |
| 公式估算汇总 | `waveforms/03-parameter-sweep-summary.csv` |
| PLECS 扫描汇总 | `waveforms/03-plecs-parameter-sweep-summary.csv` |
| 图表 | `waveforms/03-*.png`、`waveforms/03-plecs-*.png` |

第四章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/04-discrete-pi-control.md` |
| 复现说明 | `docs/04-discrete-pi-control-reproduce.md` |
| Simulink 平均模型 | `models/simulink/buck_discrete_pi_voltage_loop.slx` |
| Simulink 截图脚本 | `scripts/export_simulink_discrete_pi_snapshot.m` |
| Simulink 波形脚本 | `scripts/export_simulink_discrete_pi_waveforms.m` |
| Simulink 原始数据 | `waveforms/04-simulink-discrete-pi-control-trace.csv` |
| Simulink 指标汇总 | `waveforms/04-simulink-discrete-pi-control-summary.csv` |
| Simulink 主波形 | `waveforms/04-simulink-*.png` |
| Python 对照脚本 | `scripts/export_discrete_pi_control.py` |
| Python 对照数据 | `waveforms/04-discrete-pi-control-*.csv` |
| Python 对照波形 | `waveforms/04-p-only-vs-pi-vin-step.png`、`waveforms/04-pi-*.png` |

第五章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/05-duty-limit-anti-windup.md` |
| 复现说明 | `docs/05-duty-limit-anti-windup-reproduce.md` |
| MATLAB 主仿真脚本 | `scripts/export_matlab_duty_limit_anti_windup_waveforms.m` |
| Simulink 逻辑截图脚本 | `scripts/export_simulink_duty_limit_anti_windup_snapshot.m` |
| Simulink 逻辑模型 | `models/simulink/buck_duty_limit_anti_windup_logic.slx` |
| Simulink 逻辑截图 | `assets/screenshots/05-simulink-duty-limit-anti-windup-logic.png` |
| MATLAB 原始数据 | `waveforms/05-matlab-duty-limit-anti-windup-trace.csv` |
| MATLAB 指标汇总 | `waveforms/05-matlab-duty-limit-anti-windup-summary.csv` |
| MATLAB 主波形 | `waveforms/05-matlab-*.png` |

第六章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/06-soft-start.md` |
| 复现说明 | `docs/06-soft-start-reproduce.md` |
| MATLAB 主仿真脚本 | `scripts/export_matlab_soft_start_waveforms.m` |
| Simulink 逻辑截图脚本 | `scripts/export_simulink_soft_start_snapshot.m` |
| Simulink 逻辑模型 | `models/simulink/buck_soft_start_logic.slx` |
| Simulink 逻辑截图 | `assets/screenshots/06-simulink-soft-start-logic.png` |
| MATLAB 原始数据 | `waveforms/06-matlab-soft-start-trace.csv` |
| MATLAB 指标汇总 | `waveforms/06-matlab-soft-start-summary.csv` |
| MATLAB 斜坡扫描 | `waveforms/06-matlab-soft-start-ramp-sweep.csv` |
| MATLAB 主波形 | `waveforms/06-matlab-soft-start-*.png` |

第七章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/07-protection-state-machine.md` |
| 复现说明 | `docs/07-protection-state-machine-reproduce.md` |
| MATLAB 故障注入脚本 | `scripts/export_matlab_protection_state_machine_waveforms.m` |
| Simulink 结构截图脚本 | `scripts/export_simulink_protection_state_machine_snapshot.m` |
| Simulink 结构模型 | `models/simulink/buck_protection_state_machine_logic.slx` |
| Simulink 结构截图 | `assets/screenshots/07-simulink-protection-state-machine-logic.png` |
| MATLAB 原始数据 | `waveforms/07-matlab-protection-state-machine-trace.csv`、`waveforms/07-matlab-protection-clear-while-fault-trace.csv` |
| MATLAB 优先级数据 | `waveforms/07-matlab-protection-priority-cases.csv` |
| MATLAB 指标汇总 | `waveforms/07-matlab-protection-state-machine-summary.csv` |
| MATLAB 主波形 | `waveforms/07-matlab-protection-*.png` |

第八章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/08-load-transient.md` |
| 复现说明 | `docs/08-load-transient-reproduce.md` |
| MATLAB 负载阶跃脚本 | `scripts/export_matlab_load_transient_waveforms.m` |
| Simulink 测试台截图脚本 | `scripts/export_simulink_load_transient_snapshot.m` |
| Simulink 测试台模型 | `models/simulink/buck_load_transient_testbench.slx` |
| Simulink 测试台截图 | `assets/screenshots/08-simulink-load-transient-testbench.png` |
| MATLAB 原始数据 | `waveforms/08-matlab-load-transient-trace.csv` |
| MATLAB 指标汇总 | `waveforms/08-matlab-load-transient-summary.csv` |
| MATLAB 主波形 | `waveforms/08-matlab-load-transient-*.png` |

## 复现方式

在仓库根目录运行：

```powershell
python scripts\export_open_loop_waveforms.py
```

如果 PLECS RPC 已启动，脚本会调用 PLECS 导出仿真数据和波形图。如果 PLECS RPC 没有启动，但已有 CSV 数据存在，脚本会基于 CSV 重新生成波形图，并明确提示“未重新运行 PLECS 仿真”。

第 3 章的参数估算图表运行：

```powershell
python scripts\export_parameter_sweep.py
```

这个脚本不重新运行 PLECS 参数扫描，只生成公式估算表格和图表，并读取第 2 章已有 PLECS 汇总数据做基准对照。

第 3 章的 PLECS 参数扫描运行：

```powershell
python scripts\export_plecs_parameter_sweep.py
```

运行前需要启动 PLECS RPC Server，并确认 `localhost:1080` 可用。该脚本会对 `Lo`、`Co`、`fsw` 做真实参数扫描，导出 `waveforms/03-plecs-*` 结果。

第 4 章的 Simulink 模型截图生成运行：

```powershell
matlab -batch "run('scripts/export_simulink_discrete_pi_snapshot.m'); exit"
```

第 4 章的 Simulink 主波形导出运行：

```powershell
matlab -batch "run('scripts/export_simulink_discrete_pi_waveforms.m'); exit"
```

第 4 章的 Python 离散 PI 对照脚本运行：

```powershell
python scripts\export_discrete_pi_control.py
```

第 4 章不需要启动 PLECS RPC。该章重点验证离散 PI 控制器的数据流、采样周期、积分项和 duty 更新；正文主波形来自 Simulink 模型 `Scope mux` 导出的仿真数据，开关级波形仍在 PLECS 章节中验证。

第 5 章的 Simulink 逻辑截图生成运行：

```powershell
matlab -batch "run('scripts/export_simulink_duty_limit_anti_windup_snapshot.m'); exit"
```

第 5 章的 MATLAB 主波形导出运行：

```powershell
matlab -batch "run('scripts/export_matlab_duty_limit_anti_windup_waveforms.m'); exit"
```

第 5 章不需要启动 PLECS RPC。该章重点验证 duty 上下限、`duty_raw`/`duty_cmd` 分离、积分项 windup 和条件积分 anti-windup；正文主波形来自 MATLAB 离散平均模型导出的数据，开关级波形仍在 PLECS 章节中验证。

第 6 章的 Simulink 逻辑截图生成运行：

```powershell
matlab -batch "run('scripts/export_simulink_soft_start_snapshot.m'); exit"
```

第 6 章的 MATLAB 主波形导出运行：

```powershell
matlab -batch "run('scripts/export_matlab_soft_start_waveforms.m'); exit"
```

第 6 章不需要启动 PLECS RPC。该章重点验证软启动参考值斜坡、启动过冲、电感电流峰值、duty 饱和和斜坡时间取舍；正文主波形来自 MATLAB 离散平均模型导出的数据，开关级波形仍在 PLECS 章节中验证。

第 7 章的 Simulink 结构截图生成运行：

```powershell
matlab -batch "run('scripts/export_simulink_protection_state_machine_snapshot.m'); exit"
```

第 7 章的 MATLAB 故障注入波形导出运行：

```powershell
matlab -batch "run('scripts/export_matlab_protection_state_machine_waveforms.m'); exit"
```

第 7 章不需要启动 PLECS RPC。该章重点验证保护检测、故障锁存、PWM 统一关断和故障优先级；正文主波形来自 MATLAB 状态机故障注入模型导出的数据，开关级器件应力仍在 PLECS 章节中验证。

第 8 章的 Simulink 测试台截图生成运行：

```powershell
matlab -batch "run('scripts/export_simulink_load_transient_snapshot.m'); exit"
```

第 8 章的 MATLAB 负载阶跃波形导出运行：

```powershell
matlab -batch "run('scripts/export_matlab_load_transient_waveforms.m'); exit"
```

第 8 章不需要启动 PLECS RPC。该章重点验证负载 50% -> 100% -> 50% 时的输出下陷、过冲、恢复时间和 duty 饱和诊断；正文主波形来自 MATLAB 平均模型导出的数据，开关级器件应力仍在 PLECS 章节中验证。

## 第二章结果

| 指标 | 结果 |
| --- | --- |
| 稳态输出电压 | 约 12 V |
| 稳态电感电流 | 约 5 A |
| MOSFET Vds | 0 V / 24 V 周期切换 |
| 启动 Vout 峰值 | 约 20.8 V |
| 启动 IL 峰值 | 约 27.3 A |

启动过冲来自开环硬启动和 LC 自然响应，不代表功率级接线错误。后续章节会用软启动和闭环控制继续处理这个问题。

## 第三章结果

| 指标 | 结果 |
| --- | --- |
| 满载等效负载 | 2.4Ω |
| 理想 Buck 开环占空比 | 0.5 |
| 22uH 下电感纹波估算 | 约 1.36A |
| PLECS 扫描电感纹波 | 约 1.31A |
| 100uF 下输出纹波估算 | 约 8.52mV |
| PLECS 扫描输出纹波 | 约 8.50mV |
| 22uH / 100uF LC 自然频率 | 约 3.39kHz |
| PLECS 扫描启动 Vout 峰值 | 约 20.8V |
| PLECS 扫描启动 IL 峰值 | 约 27.3A |

第 3 章通过公式估算解释 L、C 和 fsw 的趋势，再用 PLECS RPC 参数扫描验证稳态纹波和开环硬启动峰值。

## 第四章结果

| 指标 | 结果 |
| --- | --- |
| 控制周期 | 5us |
| PI 参数 | Kp = 0.05，Ki = 200 |
| 输入扰动 | Vin 24V -> 20V |
| 负载扰动 | 5A -> 7.5A |
| P-only 输入阶跃后 Vout | 约 11.00V |
| PI 输入阶跃后 Vout | 约 12.00V |
| PI 负载阶跃后 Vout | 约 12.00V |
| PI duty 范围 | 约 0.504 - 0.646 |
| 输入阶跃 1% 恢复时间 | 约 2.22ms |
| 负载阶跃 1% 恢复时间 | 约 0.91ms |

第 4 章通过平均模型验证离散 PI 电压环的数据流：采样 Vout、计算误差、更新积分项、输出 duty，再反馈到 Buck 平均功率级。该章故意不加入 duty 限幅和抗积分饱和，相关问题放到第 5 章单独处理。

## 第五章结果

| 指标 | 结果 |
| --- | --- |
| duty 上限 | 0.55 |
| Vin 跌落工况 | 24V -> 20V -> 24V |
| Vin 跌落时维持 12V 所需 duty | 约 0.605 |
| 只加限幅时 integrator 峰值 | 约 0.670 |
| 加 anti-windup 后 integrator 峰值 | 约 0.0176 |
| 只加限幅时 raw duty 峰值 | 约 1.218 |
| 加 anti-windup 后 raw duty 峰值 | 约 0.614 |
| 只加限幅时 Vin 恢复后 Vout 峰值 | 约 14.62V |
| 加 anti-windup 后 Vin 恢复后 Vout 峰值 | 约 13.13V |
| Vin 恢复后退出饱和时间 | 约 2.58ms -> 0.22ms |

第 5 章通过 MATLAB 离散平均模型验证 duty 限幅和 anti-windup 的职责边界：Saturation 限制实际 PWM 输出，anti-windup 限制积分项继续向饱和方向累加。

## 第六章结果

| 指标 | 结果 |
| --- | --- |
| 目标输出 | 12V |
| 对比方式 | 直接 12V 阶跃、2ms 斜坡、5ms 斜坡 |
| 直接 12V 阶跃 Vout 峰值 | 约 18.64V |
| 直接 12V 阶跃电感电流峰值 | 约 28.34A |
| 直接 12V 阶跃 duty 饱和总时长 | 约 0.075ms |
| 2ms 软启动 Vout 峰值 | 约 12.17V |
| 2ms 软启动电感电流峰值 | 约 5.51A |
| 5ms 软启动 Vout 峰值 | 约 12.08V |
| 5ms 软启动电感电流峰值 | 约 5.24A |
| 5ms 软启动电流峰值降低量 | 约 23.10A |
| 5ms 软启动 Vout 过冲降低量 | 约 6.55V |

第 6 章通过 MATLAB 离散平均模型验证软启动参考值路径：软启动不改变最终目标 12V，而是让目标电压以可控斜率进入电压环，从而降低启动过冲和电感电流峰值。

## 第七章结果

| 指标 | 结果 |
| --- | --- |
| 状态机周期 | 50us |
| 故障优先级 | OCP -> OVP -> UVLO -> OTP |
| OCP 阈值 | 6.5A |
| OVP 阈值 | 13.2V |
| UVLO 阈值 | 18V |
| RUN 状态首次 OCP 检测时间 | 8ms |
| PWM 关断延迟 | 0us |
| 锁存故障码 | OCP |
| 清故障进入恢复时间 | 12ms |
| 重新进入 RUN 时间 | 19.05ms |
| OVP 仍存在时 CLEAR_FAULT | 不解除锁存 |

第 7 章通过 MATLAB 故障注入模型验证保护状态机职责边界：保护检测层输出唯一故障码，状态机锁存故障，PWM gate 在非运行态统一关断输出。

## 第八章结果

| 指标 | 结果 |
| --- | --- |
| 负载阶跃 | 50% -> 100% -> 50% |
| 50% 负载电流 | 2.5A |
| 100% 负载电流 | 5A |
| 1% 恢复带宽 | ±0.12V |
| `load_transient_pi` 上跳下陷 | 约 0.87V |
| `load_transient_pi` 上跳 1% 恢复时间 | 约 1.40ms |
| `load_transient_pi` 下跳过冲 | 约 0.93V |
| `load_transient_pi` 下跳 1% 恢复时间 | 约 4.79ms |
| `chapter04_pi` 下跳过冲 | 约 3.56V |
| `chapter04_pi` 下跳恢复 | 30ms 窗口内未恢复 |
| 220uF 电容上跳下陷 | 约 0.61V |
| 220uF 电容下跳过冲 | 约 0.63V |
| duty 上限不足工况重载饱和时间 | 约 6.33ms |

第 8 章通过 MATLAB 平均模型验证负载突变测试方法：负载上跳重点看 Vout 下陷、峰值电感电流和 duty 上限；负载下跳重点看 Vout 过冲、恢复时间和 duty 下限。该章同时用 raw duty、duty cmd 和 saturation flag 区分 PI 参数、电容储能和 duty 限幅问题。

## 仓库结构

```text
assets/             教程图片和仿真工具截图
blog/               已完成教程
docs/               已完成章节的复现说明
models/plecs/       PLECS 模型
models/simulink/    Simulink 平均模型
scripts/            可复现脚本
waveforms/          仿真原始数据、指标和波形图
```

当前仓库只展示已完成内容，未完成主题不会提前放入公开目录。

## 后续计划

| 顺序 | 内容 |
| --- | --- |
| 09 | ADC 噪声和 duty 抖动 |
| 10 | 从仿真控制器整理到 C 风格代码 |

后续主题会在完成模型、数据、波形和说明后加入本仓库。

## 技术交流

如果你在复现模型、搭建 PLECS 电路或判断波形时遇到问题，可以加入技术交流群交流。

本仓库中的模型、脚本、数据和波形可以直接使用，不需要加群获取；交流群主要用于复现答疑和后续技术交流。

| 渠道 | 信息 |
| --- | --- |
| QQ 群 | 嵌入式交流群：1056095456 |
| 加群链接 | [https://qm.qq.com/q/rygrSD2Ddu](https://qm.qq.com/q/rygrSD2Ddu) |
| 微信交流 | 微信入口会不定期更新，可在 QQ 群内获取 |

提问时建议附上拓扑截图、关键参数、仿真波形和报错信息，方便定位问题。

## 许可

本仓库代码和文档采用 MIT License。PLECS、MATLAB/Simulink 等商业软件本体不包含在本仓库中，使用者需要自行安装并遵守对应软件许可。
