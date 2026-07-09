# 第 7 章复现说明：保护状态机

本说明对应文章：`blog/07-protection-state-machine.md`

本章目标是复现保护状态机的故障注入结果，验证保护检测、故障锁存和 PWM 关断三层职责是否清晰。

## 复现边界

本章使用两类输出：

| 类型 | 文件 | 作用 |
| --- | --- | --- |
| Simulink 结构模型 | `scripts/export_simulink_protection_state_machine_snapshot.m` | 生成保护状态机数据流结构图 |
| MATLAB 故障注入模型 | `scripts/export_matlab_protection_state_machine_waveforms.m` | 生成状态迁移波形、故障优先级表和指标汇总 |

正文主波形对应 `waveforms/07-matlab-protection-*.png` 文件。

本章不需要运行 PLECS RPC。

原因是本章验证的是软件保护状态机的数据流和状态迁移，不是开关器件应力。MOSFET Vds、二极管电流、开关损耗、反向恢复和尖峰振铃仍然属于 PLECS 开关级验证范围，不在本章展开。

## 环境要求

必须具备：

| 工具 | 用途 |
| --- | --- |
| MATLAB R2024b 或相近版本 | 运行故障注入脚本，导出正文主波形 |
| Simulink | 生成保护状态机结构 `.slx` 模型和截图 |

推荐复现顺序：

| 顺序 | 命令 | 目的 |
| --- | --- | --- |
| 1 | `matlab -batch "run('scripts/export_simulink_protection_state_machine_snapshot.m'); exit"` | 生成 Simulink 结构模型和截图 |
| 2 | `matlab -batch "run('scripts/export_matlab_protection_state_machine_waveforms.m'); exit"` | 运行 MATLAB 故障注入模型并导出正文主波形 |

## 运行 Simulink 结构截图脚本

在仓库根目录运行：

```powershell
matlab -batch "run('scripts/export_simulink_protection_state_machine_snapshot.m'); exit"
```

如果 MATLAB 没有加入 PATH，在 Windows 上可以使用本机安装路径，例如：

```powershell
& 'D:\Program Files\MATLAB\R2024b\bin\matlab.exe' -batch "run('scripts/export_simulink_protection_state_machine_snapshot.m'); exit"
```

脚本会生成或更新：

| 文件 | 内容 |
| --- | --- |
| `models/simulink/buck_protection_state_machine_logic.slx` | 保护状态机数据流结构模型 |
| `assets/screenshots/07-simulink-protection-state-machine-logic.png` | 文章使用的结构截图 |

该图用于理解数据流：

```text
ADC measurements -> protection_check() -> power_state_machine_step()
state + duty -> PWM gate -> telemetry log
SOFT_START/RUN -> voltage loop -> duty candidate
```

## 运行 MATLAB 故障注入脚本

在仓库根目录运行：

```powershell
matlab -batch "run('scripts/export_matlab_protection_state_machine_waveforms.m'); exit"
```

如果 MATLAB 没有加入 PATH，可以使用完整路径：

```powershell
& 'D:\Program Files\MATLAB\R2024b\bin\matlab.exe' -batch "run('scripts/export_matlab_protection_state_machine_waveforms.m'); exit"
```

预期输出类似：

```text
已生成第 7 章保护状态机故障注入数据与图表。
run_fault,first_fault_ms=8,pwm_off_delay_us=0,latched_fault=OCP
clear_while_fault,ignored_clear_ms=8,recovery_ms=12
```

脚本会生成或更新以下文件：

| 文件 | 内容 |
| --- | --- |
| `waveforms/07-matlab-protection-state-machine-trace.csv` | RUN 状态 OCP 注入过程采样点 |
| `waveforms/07-matlab-protection-clear-while-fault-trace.csv` | OVP 仍存在时清故障过程采样点 |
| `waveforms/07-matlab-protection-priority-cases.csv` | 多故障组合优先级测试 |
| `waveforms/07-matlab-protection-state-machine-summary.csv` | 关键指标汇总 |
| `waveforms/07-matlab-protection-state-machine-overview.png` | RUN 状态 OCP 注入波形 |
| `waveforms/07-matlab-protection-latch-clear.png` | 故障仍存在时清故障波形 |
| `waveforms/07-matlab-protection-priority.png` | 故障优先级图 |

## 关键参数

| 参数 | 数值 |
| --- | --- |
| 状态机周期 | 50us |
| 软启动时间 | 5ms |
| 目标输出电压 | 12V |
| 标称输入电压 | 24V |
| 标称输出电流 | 5A |
| OCP 阈值 | 6.5A |
| OVP 阈值 | 13.2V |
| UVLO 阈值 | 18V |
| OTP 阈值 | 95°C |
| 故障优先级 | OCP -> OVP -> UVLO -> OTP |

## 动态故障注入工况

### RUN 状态 OCP 注入

| 时间 | 事件 |
| --- | --- |
| 0.5ms | enable 命令有效 |
| 0.5ms - 5.5ms | 进入软启动 |
| 5.55ms | 进入 RUN |
| 8ms - 9ms | 注入 OCP，Iout = 7.2A |
| 12ms | 清故障命令 |
| 14ms | 再次 enable |
| 19.05ms | 重新进入 RUN |

预期指标：

| 指标 | 预期结果 |
| --- | --- |
| 首次 OCP 检测时间 | 8ms |
| PWM 关断延迟 | 0us |
| 锁存故障码 | OCP |
| 清故障进入恢复时间 | 12ms |
| 重新进入 RUN 时间 | 19.05ms |

### OVP 仍存在时清故障

| 时间 | 事件 |
| --- | --- |
| 6ms - 11ms | 注入 OVP，Vout = 14V |
| 8ms | 第一次 CLEAR_FAULT |
| 11ms | OVP 注入结束 |
| 12ms | 第二次 CLEAR_FAULT |

预期结果：

| 检查项 | 预期结果 |
| --- | --- |
| 8ms CLEAR_FAULT | 不解除锁存 |
| 12ms CLEAR_FAULT | 进入 RECOVERY |
| 锁存故障码 | OVP |

## 故障优先级测试

`waveforms/07-matlab-protection-priority-cases.csv` 应包含以下结果：

| 工况 | 预期故障码 |
| --- | --- |
| `normal` | NONE |
| `uvlo_only` | UVLO |
| `ovp_only` | OVP |
| `ocp_only` | OCP |
| `otp_only` | OTP |
| `ocp_ovp_uvlo` | OCP |
| `ovp_uvlo` | OVP |
| `uvlo_otp` | UVLO |

如果结果不同，优先检查保护优先级是否仍然是：

```text
OCP -> OVP -> UVLO -> OTP
```

## 常见问题

### 1. 为什么本章状态机周期是 50us

本章关注状态迁移和故障锁存，不关注 200kHz PWM 每个开关周期的电感纹波。50us 用于让状态波形更容易阅读。真实项目需要按控制任务周期、保护响应时间和硬件关断路径重新定义。

### 2. 为什么 PWM 关断延迟是 0us

这里的 0us 指模型内故障检测、状态机更新和 PWM gate 更新发生在同一次离散步。真实 MCU 上需要继续考虑 ADC 采样、任务调度、PWM 影子寄存器加载点和硬件驱动关断延迟。

### 3. 为什么 CLEAR_FAULT 不能强制清掉仍存在的故障

`CLEAR_FAULT` 只表达清除已消失故障锁存的请求。如果检测层仍然输出 OVP/OCP/UVLO/OTP，状态机应继续留在 `FAULT_LATCH`，否则会出现故障仍在但软件恢复输出的风险。

### 4. 这是不是最终硬件保护方案

本章只证明软件状态机职责链清楚，不能替代最终硬件保护验证。真实硬件还需要逐周期限流、驱动器故障脚、采样异常处理、ADC 噪声去抖、PWM 硬件关断路径和故障现场记录策略。
