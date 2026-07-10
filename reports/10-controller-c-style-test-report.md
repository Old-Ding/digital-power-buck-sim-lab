# 第 10 章测试报告：C 风格控制器场景验证

本报告由 `scripts/export_controller_c_style_tests.py` 生成，验证对象是 `src/digital_power_control.c/.h` 对应的固定周期控制器接口和同等离散算法测试台。

## 参数

| 参数 | 数值 |
| --- | --- |
| 控制周期 | 5.000 us |
| 目标输出 | 12.000 V |
| 软启动斜率 | 300.0 V/s |
| PI 参数 | Kp = 0.05, Ki = 80 |
| duty 限幅 | 0.000 - 0.650 |
| ADC IIR alpha | 1.000 |
| OCP / OVP / UVLO | 6.50 A / 13.20 V / 18.00 V |

## 场景结果

| 场景 | 指标 | 数值 | 状态 | 说明 |
| --- | --- | ---: | --- | --- |
| `steady_12v` | `tail_vout_mean_v` | 12 | PASS | 56ms 后 Vout 均值进入 1% 带内 |
| `steady_12v` | `tail_duty_mean` | 0.504167 | INFO | 稳态 duty 约等于 Vin 到 Vout 比值加损耗补偿 |
| `soft_start_40ms` | `vout_peak_v` | 12 | PASS | 软启动峰值不过高，并在约 40ms 进入 RUN |
| `soft_start_40ms` | `first_run_time_ms` | 40 | INFO | RUN 首次出现时间 |
| `load_step_50_100_50` | `undershoot_v` | 0.744259 | PASS | 50% 到 100% 负载上跳下陷 |
| `load_step_50_100_50` | `overshoot_v` | 0.783208 | INFO | 100% 到 50% 负载下跳过冲 |
| `load_step_50_100_50` | `recovery_up_ms` | 1.455 | INFO | 上跳后回到 1% 带内时间 |
| `load_step_50_100_50` | `recovery_down_ms` | 9.5 | INFO | 下跳后回到 1% 带内时间 |
| `ocp_latch_clear` | `first_ocp_time_ms` | 52 | PASS | OCP 锁存、关 PWM、故障未消失时不能清除，故障消失后 clear 进入重启路径 |
| `uvlo_blocks_pwm` | `uvlo_pwm_off` | 1 | PASS | Vin 低于 UVLO 时 PWM 统一出口关断 |
| `all` | `pass_count` | 5 | INFO | PASS 行数 |
| `all` | `fail_count` | 0 | INFO | FAIL 行数 |

## 边界

本报告验证固定周期控制器的数据流、状态机、限幅、软启动和故障锁存逻辑。第 10 章只运行 Python 同等算法测试台，没有执行 C 编译，因此本报告不声明完成 MCU 编译、定点化、寄存器驱动或 HIL 验证。
