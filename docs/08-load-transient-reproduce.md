# 第 8 章复现说明：负载突变测试

本说明对应文章：`blog/08-load-transient.md`

本章目标是复现 Buck 数字电源在 50% -> 100% -> 50% 负载阶跃下的输出下陷、过冲、恢复时间和 duty 饱和诊断结果。

## 复现边界

本章使用两类输出：

| 类型 | 文件 | 作用 |
| --- | --- | --- |
| Simulink 测试台模型 | `scripts/export_simulink_load_transient_snapshot.m` | 生成负载突变测试台 `.slx` 和结构截图 |
| MATLAB 平均模型 | `scripts/export_matlab_load_transient_waveforms.m` | 生成负载阶跃波形、CSV 数据和指标汇总 |

正文主波形对应 `waveforms/08-matlab-load-transient-*.png` 文件。

本章不需要运行 PLECS RPC。

原因是本章验证的是闭环控制在负载阶跃下的平均动态响应，不是 MOSFET、二极管、电感电流纹波和开关尖峰。开关级器件应力仍然属于 PLECS 验证范围。

## 环境要求

必须具备：

| 工具 | 用途 |
| --- | --- |
| MATLAB R2024b 或相近版本 | 运行负载阶跃脚本，导出正文主波形 |
| Simulink | 生成负载突变测试台 `.slx` 模型和截图 |

推荐复现顺序：

| 顺序 | 命令 | 目的 |
| --- | --- | --- |
| 1 | `matlab -batch "run('scripts/export_simulink_load_transient_snapshot.m'); exit"` | 生成 Simulink 测试台模型和截图 |
| 2 | `matlab -batch "run('scripts/export_matlab_load_transient_waveforms.m'); exit"` | 运行 MATLAB 平均模型并导出正文主波形 |

## 运行 Simulink 测试台截图脚本

在仓库根目录运行：

```powershell
matlab -batch "run('scripts/export_simulink_load_transient_snapshot.m'); exit"
```

如果 MATLAB 没有加入 PATH，在 Windows 上可以使用本机安装路径，例如：

```powershell
& 'D:\Program Files\MATLAB\R2024b\bin\matlab.exe' -batch "run('scripts/export_simulink_load_transient_snapshot.m'); exit"
```

脚本会生成或更新：

| 文件 | 内容 |
| --- | --- |
| `models/simulink/buck_load_transient_testbench.slx` | 负载突变测试台结构模型 |
| `assets/screenshots/08-simulink-load-transient-testbench.png` | 文章使用的测试台截图 |

该图用于理解数据流：

```text
load_transient_case() -> averaged Buck plant
Vref/Vout -> voltage_loop_PI() -> duty_limit_anti_windup()
RUN state -> PWM gate -> averaged Buck plant
Vout/load/duty -> load transient metrics
```

## 运行 MATLAB 负载阶跃脚本

在仓库根目录运行：

```powershell
matlab -batch "run('scripts/export_matlab_load_transient_waveforms.m'); exit"
```

如果 MATLAB 没有加入 PATH，可以使用完整路径：

```powershell
& 'D:\Program Files\MATLAB\R2024b\bin\matlab.exe' -batch "run('scripts/export_matlab_load_transient_waveforms.m'); exit"
```

预期输出类似：

```text
已生成第 8 章负载突变仿真数据与图表。
chapter04_pi,undershoot=0.739313,recovery_up_ms=3.231,overshoot=3.56287,recovery_down_ms=NaN
load_transient_pi,undershoot=0.872225,recovery_up_ms=1.4045,overshoot=0.925421,recovery_down_ms=4.787
duty_limited,saturation_ms=6.325,steady_error_before_down=0.0277686
```

脚本会生成或更新以下文件：

| 文件 | 内容 |
| --- | --- |
| `waveforms/08-matlab-load-transient-trace.csv` | 负载阶跃采样点 |
| `waveforms/08-matlab-load-transient-summary.csv` | 关键指标汇总 |
| `waveforms/08-matlab-load-transient-overview.png` | `load_transient_pi` 主波形 |
| `waveforms/08-matlab-load-transient-vout-comparison.png` | 不同参数和边界条件对比 |
| `waveforms/08-matlab-load-transient-duty-diagnosis.png` | duty 限幅诊断图 |

## 关键参数

| 参数 | 数值 |
| --- | --- |
| 输入电压 | 24V |
| 目标输出 | 12V |
| 电感 | 22uH |
| 输出电容 | 100uF / 220uF 对比 |
| 控制周期 | 5us |
| 负载上跳时间 | 8ms |
| 负载下跳时间 | 16ms |
| 50% 负载电流 | 2.5A |
| 100% 负载电流 | 5A |
| 1% 恢复带宽 | ±0.12V |

## 对比工况

| 工况 | Kp | Ki | Co | duty 上限 |
| --- | --- | --- | --- | --- |
| `chapter04_pi` | 0.05 | 200 | 100uF | 0.65 |
| `load_transient_pi` | 0.02 | 80 | 100uF | 0.65 |
| `large_cap` | 0.02 | 80 | 220uF | 0.65 |
| `duty_limited` | 0.02 | 80 | 100uF | 0.503 |

## 预期指标

`waveforms/08-matlab-load-transient-summary.csv` 中应包含以下典型结果：

| 工况 | 上跳下陷 | 上跳恢复 | 下跳过冲 | 下跳恢复 |
| --- | --- | --- | --- | --- |
| `chapter04_pi` | 约 0.74V | 约 3.23ms | 约 3.56V | NaN |
| `load_transient_pi` | 约 0.87V | 约 1.40ms | 约 0.93V | 约 4.79ms |
| `large_cap` | 约 0.61V | 约 2.97ms | 约 0.63V | 约 13.96ms |
| `duty_limited` | 约 1.01V | 约 1.35ms | 约 0.90V | 约 3.38ms |

`NaN` 表示在本章 30ms 仿真窗口内没有重新进入并保持在 1% 带内。

## 常见问题

### 1. 为什么本章用 50% -> 100% -> 50%，不是 20% -> 100% -> 20%

50% -> 100% -> 50% 更适合作为第一版教学测试。它能清楚展示下陷、过冲、恢复时间和 duty 饱和，又不会把负载释放直接变成保护阈值测试。更重的 20% -> 100% -> 20% 可以作为后续保护余量或硬件压力测试。

### 2. 为什么 `chapter04_pi` 的下跳恢复时间是 NaN

第 4 章参数用于证明 PI 可以消除稳态误差，不是最终负载瞬态参数。本章 30ms 窗口内，`chapter04_pi` 在负载释放后没有稳定回到 1% 带内，因此恢复时间记录为 `NaN`。

### 3. 为什么 220uF 电容恢复时间反而更长

电容变大后，输出电压变化幅度变小，但能量存储也变大，环路对象发生变化。没有重新设计补偿时，恢复时间可能变长。

### 4. 怎么判断是 duty 限幅问题

同时看 `raw duty`、`duty_cmd` 和 `saturation`。如果 Vout 低于目标，raw duty 想继续上升，但 duty cmd 卡在 duty 上限，同时 saturation 为 1，优先检查 duty 上限、输入电压余量和功率级设计。

### 5. 这是不是最终硬件负载突变指标

本章结果属于平均模型下的控制逻辑测试，不能替代最终硬件负载突变指标。最终硬件还需要 PLECS 开关级验证、示波器负载阶跃测试、ADC 采样链路检查、保护阈值联调和热设计验证。
