# 第 10 章复现说明：从仿真控制器整理到 C 风格代码

本说明对应文章：`blog/10-controller-to-c.md`

本章目标是复现 C 风格控制器接口、场景测试、CSV 数据、PNG 图表和测试报告。

## 复现边界

本章验证的是固定周期控制器接口和离散算法顺序。

| 类型 | 文件 | 作用 |
| --- | --- | --- |
| C 风格控制器 | `src/digital_power_control.c/.h` | 展示 MCU 可迁移的接口、配置、状态和输出 |
| Python 测试台 | `scripts/export_controller_c_style_tests.py` | 运行同等离散算法场景测试 |
| 测试数据 | `waveforms/10-controller-c-style-trace.csv` | 导出每个控制周期的关键变量 |
| 指标汇总 | `waveforms/10-controller-c-style-summary.csv` | 导出 PASS/FAIL 和关键指标 |
| 测试报告 | `reports/10-controller-c-style-test-report.md` | 生成可阅读的测试报告 |

本章当前不声明完成 C 编译或 MCU 上板验证。

原因是本机没有 C 编译器，且本章没有接入 ADC、PWM、定时器和寄存器驱动。后续要继续补交叉编译、定点化、HAL 适配和 HIL 测试。

## 环境要求

必须具备：

| 工具 | 用途 |
| --- | --- |
| Python 3 | 运行测试脚本 |
| numpy | 数值处理 |
| matplotlib | 生成图表 |

不需要 MATLAB、PLECS 或 Simulink。

## 运行命令

在仓库根目录运行：

```powershell
python scripts\export_controller_c_style_tests.py
```

预期输出类似：

```text
已生成第 10 章 C 风格控制器测试数据、图表和报告。
summary,pass_count=5,fail_count=0
steady_12v,tail_vout_mean_v=12
load_step_50_100_50,undershoot_v=0.744259
ocp_latch_clear,first_ocp_time_ms=52
```

## 生成文件

脚本会生成或更新：

| 文件 | 内容 |
| --- | --- |
| `waveforms/10-controller-c-style-trace.csv` | 每个场景的周期采样点 |
| `waveforms/10-controller-c-style-summary.csv` | PASS/FAIL 和关键指标 |
| `waveforms/10-controller-c-style-scenarios.png` | 软启动、负载突变、OCP、UVLO 场景波形 |
| `waveforms/10-controller-c-style-telemetry.png` | 负载突变场景 telemetry |
| `waveforms/10-controller-c-style-pass-fail.png` | 测试报告汇总图 |
| `reports/10-controller-c-style-test-report.md` | Markdown 测试报告 |

## 默认参数

| 参数 | 数值 |
| --- | --- |
| 控制周期 | 5us |
| 目标输出 | 12V |
| 软启动斜率 | 300V/s |
| Kp | 0.05 |
| Ki | 80 |
| duty 限幅 | 0 - 0.65 |
| ADC alpha | 1.0 |
| OCP 阈值 | 6.5A |
| OVP 阈值 | 13.2V |
| UVLO 阈值 | 18V |

## 测试场景

| 场景 | 预期结果 |
| --- | --- |
| `steady_12v` | 56ms 后 Vout 均值进入 1% 带内 |
| `soft_start_40ms` | 约 40ms 进入 RUN，Vout 峰值不过高 |
| `load_step_50_100_50` | 负载上跳下陷约 0.744V，并能恢复 |
| `ocp_latch_clear` | 52ms 左右锁存 OCP，故障仍存在时 clear 不解除，故障消失后进入重启路径 |
| `uvlo_blocks_pwm` | Vin 低于 UVLO 时 PWM 统一出口关断 |

## 常见问题

### 1. 为什么本章不用 MATLAB 或 Simulink

第十章关注 C 风格接口和固定周期软件结构。Python 测试台更适合快速生成场景测试、CSV、图表和报告。前面章节已经用 MATLAB/PLECS/Simulink 验证过功率级和控制现象。

### 2. 为什么 `ADC alpha` 默认是 1.0

第九章已经验证过 IIR 滤波能降噪但会引入延迟。第十章先验证代码迁移基线，因此默认不加入 IIR 延迟。滤波仍然保留为配置项。

### 3. 为什么 OCP clear 后不是立刻 RUN

故障解除后控制器进入软启动路径，而不是直接恢复 RUN。这避免故障刚解除时立即给出大 duty。测试报告检查的是锁存、关 PWM、故障未消失不能 clear、故障消失后进入重启路径。

### 4. 为什么本章不编译 C 文件

当前本机没有 C 编译器。本章提供 C 风格源码和同等算法测试台，但不声明完成编译验证。后续可以用 GCC、Clang、MSVC 或嵌入式交叉编译器补上编译和单元测试。

### 5. 如何修改参数

修改 `scripts/export_controller_c_style_tests.py` 中的 `Config`，并同步检查 `src/digital_power_control.c` 中的默认参数。

如果修改 PI、软启动斜率或保护阈值，重新运行：

```powershell
python scripts\export_controller_c_style_tests.py
```

然后查看 `waveforms/10-controller-c-style-summary.csv` 和 `reports/10-controller-c-style-test-report.md`。
