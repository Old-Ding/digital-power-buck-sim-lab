# 第 5 章复现说明：duty 限幅和抗积分饱和

本说明对应文章：`blog/05-duty-limit-anti-windup.md`

本章目标是复现 duty 上下限和 anti-windup 的平均模型结果，观察 Vin 短时跌落导致 duty 饱和后，积分项是否继续累加，以及 Vin 恢复后的输出过冲差异。

## 复现边界

本章使用两类输出：

| 类型 | 文件 | 作用 |
| --- | --- | --- |
| MATLAB 离散平均模型 | `scripts/export_matlab_duty_limit_anti_windup_waveforms.m` | 生成正文主波形、原始数据和指标汇总 |
| Simulink 逻辑模型 | `models/simulink/buck_duty_limit_anti_windup_logic.slx` | 展示 duty 限幅和 anti-windup gate 的结构关系 |

正文主波形对应 `waveforms/05-matlab-*.png` 文件。

本章不需要运行 PLECS RPC。

原因是本章重点是控制器边界逻辑：`duty_raw`、`duty_cmd`、`integrator` 和 `saturation flag`。MOSFET Vds、二极管电流、开关损耗和尖峰振铃仍然属于 PLECS 开关级验证范围，不在本章展开。

## 环境要求

必须具备：

| 工具 | 用途 |
| --- | --- |
| MATLAB R2024b 或相近版本 | 运行平均模型仿真脚本，导出正文主波形 |
| Simulink | 生成控制逻辑 `.slx` 模型和截图 |

推荐复现顺序：

| 顺序 | 命令 | 目的 |
| --- | --- | --- |
| 1 | `matlab -batch "run('scripts/export_simulink_duty_limit_anti_windup_snapshot.m'); exit"` | 生成 Simulink 逻辑模型和截图 |
| 2 | `matlab -batch "run('scripts/export_matlab_duty_limit_anti_windup_waveforms.m'); exit"` | 运行 MATLAB 离散平均模型并导出正文主波形 |

## 运行 Simulink 逻辑截图脚本

在仓库根目录运行：

```powershell
matlab -batch "run('scripts/export_simulink_duty_limit_anti_windup_snapshot.m'); exit"
```

如果 MATLAB 没有加入 PATH，在 Windows 上可以使用本机安装路径，例如：

```powershell
& 'D:\Program Files\MATLAB\R2024b\bin\matlab.exe' -batch "run('scripts/export_simulink_duty_limit_anti_windup_snapshot.m'); exit"
```

脚本会生成或更新：

| 文件 | 内容 |
| --- | --- |
| `models/simulink/buck_duty_limit_anti_windup_logic.slx` | duty 限幅和 anti-windup 控制逻辑模型 |
| `assets/screenshots/05-simulink-duty-limit-anti-windup-logic.png` | 文章使用的控制结构截图 |

该图用于理解数据流：

```text
error -> PI raw duty -> Saturation -> duty_cmd -> Buck 平均功率级
raw duty / limited duty / error -> Anti-windup gate -> 积分项更新判断
```

## 运行 MATLAB 主仿真脚本

在仓库根目录运行：

```powershell
matlab -batch "run('scripts/export_matlab_duty_limit_anti_windup_waveforms.m'); exit"
```

如果 MATLAB 没有加入 PATH，可以使用完整路径：

```powershell
& 'D:\Program Files\MATLAB\R2024b\bin\matlab.exe' -batch "run('scripts/export_matlab_duty_limit_anti_windup_waveforms.m'); exit"
```

预期输出类似：

```text
已生成第 5 章 duty 限幅和抗积分饱和仿真数据与图表。
limit_no_aw,integrator_peak=0.669767,vout_max_after_return=14.6158,saturation_exit_after_return_ms=2.58
limit_aw,integrator_peak=0.0176382,vout_max_after_return=13.1259,saturation_exit_after_return_ms=0.22
```

脚本会生成或更新以下文件：

| 文件 | 内容 |
| --- | --- |
| `waveforms/05-matlab-duty-limit-anti-windup-trace.csv` | 三种控制方式的完整时序数据 |
| `waveforms/05-matlab-duty-limit-anti-windup-summary.csv` | 关键指标汇总 |
| `waveforms/05-matlab-duty-limit-anti-windup-overview.png` | duty 限幅和 anti-windup 整体对比 |
| `waveforms/05-matlab-integrator-windup-comparison.png` | 积分项 windup 与饱和标志对比 |
| `waveforms/05-matlab-duty-raw-vs-limited.png` | raw duty 与 limited duty 对比 |
| `waveforms/05-matlab-recovery-after-vin-return.png` | Vin 恢复后的过冲和积分项对比 |

## 关键参数

| 参数 | 数值 |
| --- | --- |
| Vin 初值 | 24V |
| Vin 跌落值 | 20V |
| Vin 跌落时间 | 3ms |
| Vin 恢复时间 | 6ms |
| Vref | 12V |
| 负载 | 2.4Ω |
| L | 22uH |
| C | 100uF |
| fsw | 200kHz |
| 控制周期 | 5us |
| Kp | 0.05 |
| Ki | 200 |
| duty_min | 0.05 |
| duty_max | 0.55 |
| Vin 跌落时维持 12V 的所需 duty | 约 0.605 |

因为所需 duty 约 0.605 高于 `duty_max = 0.55`，所以 Vin 跌落期间控制器一定会进入上限饱和。本章正是利用这个工况观察积分项是否 windup。

## 预期指标

`waveforms/05-matlab-duty-limit-anti-windup-summary.csv` 中应包含以下量级的结果：

| 指标 | 预期结果 |
| --- | --- |
| duty 上限 | 0.55 |
| Vin 跌落时所需 duty | 约 0.605 |
| 只加限幅时 integrator 峰值 | 约 0.670 |
| 加 anti-windup 后 integrator 峰值 | 约 0.0176 |
| 只加限幅时 raw duty 峰值 | 约 1.218 |
| 加 anti-windup 后 raw duty 峰值 | 约 0.614 |
| 只加限幅时 Vin 恢复后 Vout 峰值 | 约 14.62V |
| 加 anti-windup 后 Vin 恢复后 Vout 峰值 | 约 13.13V |
| 过冲降低量 | 约 1.49V |
| 只加限幅时 Vin 恢复后退出饱和 | 约 2.58ms |
| 加 anti-windup 后 Vin 恢复后退出饱和 | 约 0.22ms |

这些指标用于验证脚本是否跑出了同一组结果。它们不是量产调参目标。

## 结果判断

复现完成后，建议按下面顺序检查：

| 检查项 | 判断方式 |
| --- | --- |
| duty 是否被限制 | 查看 `05-matlab-duty-limit-anti-windup-overview.png` 中 duty_cmd 是否卡在 0.55 |
| 是否发生 windup | 查看 `05-matlab-integrator-windup-comparison.png` 中 limit only 的 integrator 是否持续升高 |
| raw duty 是否远离上限 | 查看 `05-matlab-duty-raw-vs-limited.png` |
| Vin 恢复后是否降低过冲 | 查看 `05-matlab-recovery-after-vin-return.png` |
| 指标是否一致 | 查看 `05-matlab-duty-limit-anti-windup-summary.csv` |

如果 `duty_cmd` 被限制了，但 `integrator` 和 `duty_raw` 仍然持续增大，就说明只是做了输出限幅，没有处理积分饱和。

## 常见问题

### 1. 为什么 Vin 跌落到 20V，而 duty_max 只有 0.55

这是为了制造一个明确触发 duty 上限的教学工况。20V 输入下维持 12V 输出需要约 0.605 duty，而本章限制为 0.55，所以控制器一定会进入饱和区间。

### 2. 为什么 anti-windup 不能让 Vin 跌落期间仍然稳定 12V

因为 `Vin * duty_max` 本身不够。Anti-windup 不能突破物理上限，它只是保护积分项，避免工况恢复后被历史积分拖住。

### 3. 为什么本章不用 PLECS RPC

本章验证的是控制器内部状态边界，不是开关器件应力。平均模型更适合看 `duty_raw`、`duty_cmd`、`integrator` 和 `saturation flag`。开关级波形仍然放到 PLECS 章节中验证。

### 4. 这是不是最终可上硬件代码

还不是。

第五章只处理 duty 限幅和 anti-windup。真实硬件还需要软启动、保护状态机、限流、过压/欠压判断、PWM 更新时序、ADC 噪声处理和故障关断路径。
