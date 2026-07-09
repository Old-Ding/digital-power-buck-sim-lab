# 第 6 章复现说明：软启动

本说明对应文章：`blog/06-soft-start.md`

本章目标是复现软启动平均模型结果，比较直接 12V 阶跃参考、2ms 参考斜坡和 5ms 参考斜坡对启动过冲、电感电流峰值、duty 饱和和启动时间的影响。

## 复现边界

本章使用两类输出：

| 类型 | 文件 | 作用 |
| --- | --- | --- |
| MATLAB 离散平均模型 | `scripts/export_matlab_soft_start_waveforms.m` | 生成正文主波形、原始数据、指标汇总和斜坡时间扫描 |
| Simulink 逻辑模型 | `models/simulink/buck_soft_start_logic.slx` | 展示软启动参考值路径和电压环结构关系 |

正文主波形对应 `waveforms/06-matlab-soft-start-*.png` 文件。

本章不需要运行 PLECS RPC。

原因是本章重点是启动参考值如何进入控制器，以及 `Vref_cmd`、`Vout`、`IL`、`duty_cmd` 和 `saturation flag` 的启动趋势。MOSFET Vds、二极管电流、开关损耗、反向恢复和尖峰振铃仍然属于 PLECS 开关级验证范围，不在本章展开。

## 环境要求

必须具备：

| 工具 | 用途 |
| --- | --- |
| MATLAB R2024b 或相近版本 | 运行平均模型仿真脚本，导出正文主波形 |
| Simulink | 生成控制逻辑 `.slx` 模型和截图 |

推荐复现顺序：

| 顺序 | 命令 | 目的 |
| --- | --- | --- |
| 1 | `matlab -batch "run('scripts/export_simulink_soft_start_snapshot.m'); exit"` | 生成 Simulink 逻辑模型和截图 |
| 2 | `matlab -batch "run('scripts/export_matlab_soft_start_waveforms.m'); exit"` | 运行 MATLAB 离散平均模型并导出正文主波形 |

## 运行 Simulink 逻辑截图脚本

在仓库根目录运行：

```powershell
matlab -batch "run('scripts/export_simulink_soft_start_snapshot.m'); exit"
```

如果 MATLAB 没有加入 PATH，在 Windows 上可以使用本机安装路径，例如：

```powershell
& 'D:\Program Files\MATLAB\R2024b\bin\matlab.exe' -batch "run('scripts/export_simulink_soft_start_snapshot.m'); exit"
```

脚本会生成或更新：

| 文件 | 内容 |
| --- | --- |
| `models/simulink/buck_soft_start_logic.slx` | 软启动参考值路径和电压环控制逻辑模型 |
| `assets/screenshots/06-simulink-soft-start-logic.png` | 文章使用的控制结构截图 |

该图用于理解数据流：

```text
soft-start ramp -> Vref_cmd -> voltage loop -> duty limit -> averaged Buck plant
raw duty / limited duty / error -> anti-windup gate -> integrator update
```

## 运行 MATLAB 主仿真脚本

在仓库根目录运行：

```powershell
matlab -batch "run('scripts/export_matlab_soft_start_waveforms.m'); exit"
```

如果 MATLAB 没有加入 PATH，可以使用完整路径：

```powershell
& 'D:\Program Files\MATLAB\R2024b\bin\matlab.exe' -batch "run('scripts/export_matlab_soft_start_waveforms.m'); exit"
```

预期输出类似：

```text
已生成第 6 章软启动仿真数据与图表。
step_12v,peak_vout=18.6354,peak_il=28.3399,saturation_ms=0.075
ramp_5ms,peak_vout=12.0812,peak_il=5.24205,saturation_ms=0
```

脚本会生成或更新以下文件：

| 文件 | 内容 |
| --- | --- |
| `waveforms/06-matlab-soft-start-trace.csv` | 三种启动方式的控制采样点数据 |
| `waveforms/06-matlab-soft-start-summary.csv` | 关键指标汇总 |
| `waveforms/06-matlab-soft-start-ramp-sweep.csv` | 不同斜坡时间的扫描数据 |
| `waveforms/06-matlab-soft-start-overview.png` | 软启动整体对比 |
| `waveforms/06-matlab-soft-start-current-stress.png` | 启动电感电流峰值和 duty 饱和对比 |
| `waveforms/06-matlab-soft-start-tracking-error.png` | 跟踪误差和积分项对比 |
| `waveforms/06-matlab-soft-start-ramp-sweep.png` | 斜坡时间扫描图 |

## 关键参数

| 参数 | 数值 |
| --- | --- |
| Vin | 24V |
| Vtarget | 12V |
| 负载 | 2.4Ω |
| L | 22uH |
| C | 100uF |
| fsw | 200kHz |
| 控制周期 | 5us |
| Kp | 0.05 |
| Ki | 200 |
| duty_min | 0 |
| duty_max | 0.55 |
| 对比方式 | 直接 12V 阶跃、2ms 斜坡、5ms 斜坡 |

本章模型从 0V 输出启动，并在功率级模型中加入非同步 Buck 启动边界：电感电流不允许反向。这个边界用于避免连续平均模型在启动阶段给出不符合二极管续流语境的反向电感电流。

## 预期指标

`waveforms/06-matlab-soft-start-summary.csv` 中应包含以下量级的结果：

| 指标 | 预期结果 |
| --- | --- |
| 直接 12V 阶跃 Vout 峰值 | 约 18.64V |
| 直接 12V 阶跃电感电流峰值 | 约 28.34A |
| 直接 12V 阶跃 duty 饱和总时长 | 约 0.075ms |
| 2ms 软启动 Vout 峰值 | 约 12.17V |
| 2ms 软启动电感电流峰值 | 约 5.51A |
| 5ms 软启动 Vout 峰值 | 约 12.08V |
| 5ms 软启动电感电流峰值 | 约 5.24A |
| 5ms 软启动 duty 饱和总时长 | 0ms |
| 5ms 软启动电流峰值降低量 | 约 23.10A |
| 5ms 软启动 Vout 过冲降低量 | 约 6.55V |

这些指标用于验证脚本是否跑出了同一组结果。它们不是量产软启动时间。

## 斜坡时间扫描

`waveforms/06-matlab-soft-start-ramp-sweep.csv` 用于比较不同软启动时间：

| 斜坡时间 | 主要趋势 |
| --- | --- |
| 0ms | 启动最快，但电感电流和 Vout 过冲最高 |
| 1ms - 3ms | 峰值大幅下降，启动时间仍较短 |
| 5ms | 峰值更低，波形平滑，适合作为本章教学点 |
| 8ms - 10ms | 峰值继续小幅下降，但启动时间明显变长 |

真实项目需要结合启动时间要求、负载电容、输入电压范围、限流阈值、保护状态机和上电时序重新选择软启动时间。

## 常见问题

### 1. 为什么本章 duty_min 设置为 0

第六章重点是启动参考值路径。启动初期 `Vref_cmd` 从 0V 开始，模型需要允许 PWM duty 从 0 开始爬升。真实硬件如果存在最小可用占空比、驱动死区或 PWM 使能延迟，应交给启动状态机和 PWM 更新层处理。

### 2. 软启动是不是替代 anti-windup

不是。

软启动控制参考值进入电压环的速度；anti-windup 控制积分项在 duty 饱和时是否继续累加。两个模块处理的是不同对象。

### 3. 为什么本章不用 PLECS RPC

本章验证的是控制器启动参考路径，不是开关器件应力。平均模型更适合观察 `Vref_cmd`、`Vout`、`IL`、`duty_cmd` 和 `saturation flag` 的关系。开关级波形仍然放到 PLECS 章节中验证。

### 4. 这是不是最终可上硬件启动方案

还不是。

第六章只处理正常启动路径里的参考值斜坡。真实硬件还需要保护状态机、限流、过压/欠压判断、故障锁存、PWM 关断路径、ADC 噪声处理和预偏置启动策略。
