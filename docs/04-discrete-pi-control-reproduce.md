# 第 4 章复现说明：离散 PI 电压环

本说明对应文章：

> `blog/04-discrete-pi-control.md`

本章目标是复现离散 PI 电压环的平均模型结果，验证 Buck 输出在输入电压扰动和负载扰动后能回到 12V 附近。

## 复现边界

本章使用两类模型：

| 类型 | 文件 | 作用 |
| --- | --- | --- |
| Python 平均模型 | `scripts/export_discrete_pi_control.py` | 生成 CSV 数据、指标汇总和文章波形图 |
| Simulink 平均模型 | `models/simulink/buck_discrete_pi_voltage_loop.slx` | 展示离散 PI 控制器和 Buck 平均功率级的数据流 |

本章不需要运行 PLECS RPC。

原因是本章重点是离散 PI 控制逻辑，而不是 MOSFET Vds、二极管电流、开关纹波或器件应力。开关级验证仍然放在 PLECS 章节中处理。

## 环境要求

必须具备：

| 工具 | 用途 |
| --- | --- |
| Python 3 | 运行平均模型仿真脚本 |
| matplotlib | 生成波形图 |

可选具备：

| 工具 | 用途 |
| --- | --- |
| MATLAB R2024b 或相近版本 | 运行截图脚本 |
| Simulink | 生成 `.slx` 模型和模型截图 |

如果没有 MATLAB/Simulink，也可以只运行 Python 脚本复现数据和波形；文章中的 Simulink 截图用于说明控制数据流。

## 运行 Python 仿真

在仓库根目录运行：

```powershell
python scripts\export_discrete_pi_control.py
```

预期输出类似：

```text
已生成第 4 章离散 PI 控制仿真数据和图表。
pi,kp=0.05,ki=200,control_period_us=5,duty_max=0.647856,input_step_settling_ms=2.410250000000001,load_step_settling_ms=1.0052500000000018
```

脚本会生成或更新以下文件：

| 文件 | 内容 |
| --- | --- |
| `waveforms/04-discrete-pi-control-trace.csv` | PI 仿真的完整时序数据 |
| `waveforms/04-discrete-pi-control-summary.csv` | 关键指标汇总 |
| `waveforms/04-p-only-vs-pi-vin-step.png` | P-only 和 PI 的输入扰动对比 |
| `waveforms/04-pi-vin-load-transient.png` | PI 在输入扰动和负载扰动下的响应 |
| `waveforms/04-pi-error-integrator.png` | error 和 integrator 变化 |
| `waveforms/04-pi-sampling-points.png` | 离散采样点示意 |

## 运行 Simulink 截图脚本

如果 MATLAB 已加入 PATH，可以运行：

```powershell
matlab -batch "run('scripts/export_simulink_discrete_pi_snapshot.m'); exit"
```

如果 MATLAB 没有加入 PATH，在 Windows 上可以使用本机安装路径，例如：

```powershell
& 'D:\Program Files\MATLAB\R2024b\bin\matlab.exe' -batch "run('scripts/export_simulink_discrete_pi_snapshot.m'); exit"
```

脚本会生成或更新：

| 文件 | 内容 |
| --- | --- |
| `models/simulink/buck_discrete_pi_voltage_loop.slx` | Simulink 离散 PI 平均模型 |
| `assets/screenshots/04-simulink-discrete-pi-control.png` | 模型截图 |

该 Simulink 模型表达的是控制器和平均功率级的数据流：

> Vref/Vout -> 离散 PI -> duty -> Buck 平均功率级 -> Vout 反馈

其中 Vin 在 3ms 时从 24V 阶跃到 20V，Rload 在 7ms 时从 2.4Ω 阶跃到 1.6Ω。

## 关键参数

| 参数 | 数值 |
| --- | --- |
| Vin 初值 | 24V |
| Vin 阶跃后 | 20V |
| Vref | 12V |
| 负载初值 | 2.4Ω |
| 负载阶跃后 | 1.6Ω |
| L | 22uH |
| C | 100uF |
| fsw | 200kHz |
| 控制周期 | 5us |
| Dff | 0.5 |
| Kp | 0.05 |
| Ki | 200 |

本章脚本中故意没有加入 duty 限幅和抗积分饱和。第 5 章会单独处理这两个问题。

## 预期指标

`waveforms/04-discrete-pi-control-summary.csv` 中应包含以下量级的结果：

| 指标 | 预期结果 |
| --- | --- |
| P-only 输入阶跃后 Vout | 约 11.00V |
| PI 输入阶跃后 Vout | 约 12.00V |
| PI 负载阶跃后 Vout | 约 12.00V |
| 输入阶跃后 Vout 最低/最高 | 约 10.26V / 12.29V |
| 负载阶跃后 Vout 最低/最高 | 约 11.25V / 12.66V |
| duty 范围 | 约 0.504 - 0.648 |
| 输入阶跃 1% 恢复时间 | 约 2.41ms |
| 负载阶跃 1% 恢复时间 | 约 1.01ms |

这些指标用于验证脚本是否跑出了同一组结果。它们不是量产调参目标。

## 结果判断

复现完成后，建议按下面顺序检查：

| 检查项 | 判断方式 |
| --- | --- |
| P-only 是否留下稳态误差 | 查看 `04-p-only-vs-pi-vin-step.png` |
| PI 是否消除稳态误差 | 查看输入阶跃后 Vout 是否回到 12V 附近 |
| duty 是否随输入跌落抬升 | 查看 `04-pi-vin-load-transient.png` |
| 积分项是否参与修正 | 查看 `04-pi-error-integrator.png` |
| 控制器是否按离散周期更新 | 查看 `04-pi-sampling-points.png` |

如果只看 Vout，很容易误判控制器已经完全调好。第四章至少要同时检查 `Vout`、`duty`、`error` 和 `integrator`。

## 常见问题

### 1. 为什么不用 PLECS RPC

本章验证的是离散 PI 控制逻辑，平均模型更容易看清误差、积分项和 duty 的变化。开关级细节仍然需要 PLECS，但不放在本章重复展开。

### 2. 为什么没有 duty 限幅

这是本章的边界。第四章只验证最小闭环，避免把 PI、限幅、抗积分饱和和软启动混在一起。第 5 章再加入 duty 上下限和积分器边界。

### 3. 为什么初始积分项不是 0

模型中加入了 0.02Ω 串联电阻，5A 负载下会产生小压降。`initial_integrator_trim` 用于补偿这个压降，让仿真从接近 12V 的工作点开始。

### 4. 输出恢复到 12V 是否说明可以上硬件

不能。

本章只说明离散 PI 数据流成立。真实硬件还需要 duty 限幅、抗积分饱和、软启动、保护状态机、采样噪声处理、过流响应和硬件安全验证。
