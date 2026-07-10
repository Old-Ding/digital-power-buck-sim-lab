# 第 13 章报告：Q20 定点 C 与浮点 C 逐周期对照

本报告由 `scripts/run_fixed_point_parity.py` 生成。浮点基准来自 `src/digital_power_control.c`，定点结果来自 `src/digital_power_control_fixed.c`，两者由同一个 C 回放程序接收相同输入。

## 执行摘要

- 电脑端 C 编译器：`zig 0.16.0`
- 定点格式：有符号 32 位，20 个小数位，缩放因子 1048576
- 对照场景：5
- 逐周期比较行数：80400
- 公开抽样行数：4025
- 指标结果：PASS 74 / FAIL 0

C 双实现回放程序输出：

```text
SUMMARY,OK,rows=80400,input_overflow=0,fixed_overflow=0
```

定点单元测试输出：

```text
PASS,q20_scale_and_soft_start_constant
PASS,soft_start_first_step_without_overflow
PASS,positive_overflow_saturates_and_counts
PASS,negative_overflow_saturates_and_counts
SUMMARY,PASS,failures=0
```

## 格式候选

| 小数位 | 分辨率 | 正量程 | 8000 周期软启动误差 | 100°C 占正量程 | 结论 |
| ---: | ---: | ---: | ---: | ---: | --- |
| 16 | 1.52588e-05 | 32768 | -37.1094 mV | 0.305176% | 不选：软启动每周期增量过粗，8000 周期累计偏差约 37mV |
| 20 | 9.53674e-07 | 2048 | 1.0376 mV | 4.88281% | 采用：软启动累计误差约 1mV，100°C 阈值仅占正量程约 4.88% |
| 24 | 5.96046e-08 | 128 | 0.0839233 mV | 78.125% | 不选：100°C 已占正量程约 78.13%，温度和异常输入余量不足 |

## Q20 常量

| 名称 | 工程值 | raw | 还原值 | 量化误差 |
| --- | ---: | ---: | ---: | ---: |
| `vref_final` | 12 V | 12582912 | 12 | 0 |
| `soft_start_step` | 0.0015 V/cycle | 1573 | 0.00150012969971 | 1.297e-07 |
| `kp` | 0.05 1 | 52429 | 0.0500001907349 | 1.90735e-07 |
| `ki_step` | 0.0004 1/cycle | 419 | 0.000399589538574 | -4.10461e-07 |
| `duty_feedforward` | 0.5 1 | 524288 | 0.5 | 0 |
| `duty_max` | 0.65 1 | 681574 | 0.64999961853 | -3.8147e-07 |
| `ocp_threshold` | 6.5 A | 6815744 | 6.5 | 0 |
| `ovp_threshold` | 13.2 V | 13841203 | 13.1999998093 | -1.90735e-07 |
| `uvlo_threshold` | 18 V | 18874368 | 18 | 0 |
| `otp_threshold` | 100 degC | 104857600 | 100 | 0 |

## 场景结论

| 场景 | 状态 |
| --- | --- |
| `steady_12v` | PASS |
| `soft_start_40ms` | PASS |
| `load_step_50_100_50` | PASS |
| `ocp_latch_clear` | PASS |
| `uvlo_blocks_pwm` | PASS |

## 指标明细

| 场景 | 指标 | 实际值 | 允许值 | 状态 |
| --- | --- | ---: | ---: | --- |
| `steady_12v` | `max_abs_vout_meas_v_error` | 0 | 1e-06 | PASS |
| `steady_12v` | `max_abs_vref_cmd_v_error` | 0 | 0.0011 | PASS |
| `steady_12v` | `max_abs_error_v_error` | 0 | 0.0011 | PASS |
| `steady_12v` | `max_abs_p_term_error` | 0 | 6e-05 | PASS |
| `steady_12v` | `max_abs_integrator_error` | 6.37916e-08 | 0.0001 | PASS |
| `steady_12v` | `max_abs_duty_raw_error` | 5.9912e-08 | 0.00015 | PASS |
| `steady_12v` | `max_abs_duty_cmd_error` | 5.9912e-08 | 0.00015 | PASS |
| `steady_12v` | `state_mismatch_count` | 0 | 0 | PASS |
| `steady_12v` | `fault_mismatch_count` | 0 | 0 | PASS |
| `steady_12v` | `pwm_mismatch_count` | 0 | 0 | PASS |
| `steady_12v` | `logic_flag_mismatch_count` | 0 | 0 | PASS |
| `steady_12v` | `arithmetic_overflow_count` | 0 | 0 | PASS |
| `steady_12v` | `input_conversion_overflow_count` | 0 | 0 | PASS |
| `steady_12v` | `max_raw_utilization_pct` | 4.88281 | 10 | PASS |
| `soft_start_40ms` | `max_abs_vout_meas_v_error` | 4.8183e-07 | 1e-06 | PASS |
| `soft_start_40ms` | `max_abs_vref_cmd_v_error` | 0.000478795 | 0.0011 | PASS |
| `soft_start_40ms` | `max_abs_error_v_error` | 0.000478983 | 0.0011 | PASS |
| `soft_start_40ms` | `max_abs_p_term_error` | 2.4414e-05 | 6e-05 | PASS |
| `soft_start_40ms` | `max_abs_integrator_error` | 7.06213e-05 | 0.0001 | PASS |
| `soft_start_40ms` | `max_abs_duty_raw_error` | 7.06908e-05 | 0.00015 | PASS |
| `soft_start_40ms` | `max_abs_duty_cmd_error` | 7.06908e-05 | 0.00015 | PASS |
| `soft_start_40ms` | `state_mismatch_count` | 0 | 0 | PASS |
| `soft_start_40ms` | `fault_mismatch_count` | 0 | 0 | PASS |
| `soft_start_40ms` | `pwm_mismatch_count` | 0 | 0 | PASS |
| `soft_start_40ms` | `logic_flag_mismatch_count` | 0 | 0 | PASS |
| `soft_start_40ms` | `arithmetic_overflow_count` | 0 | 0 | PASS |
| `soft_start_40ms` | `input_conversion_overflow_count` | 0 | 0 | PASS |
| `soft_start_40ms` | `max_raw_utilization_pct` | 4.88281 | 10 | PASS |
| `load_step_50_100_50` | `max_abs_vout_meas_v_error` | 5e-08 | 1e-06 | PASS |
| `load_step_50_100_50` | `max_abs_vref_cmd_v_error` | 0 | 0.0011 | PASS |
| `load_step_50_100_50` | `max_abs_error_v_error` | 5e-10 | 0.0011 | PASS |
| `load_step_50_100_50` | `max_abs_p_term_error` | 5.71875e-07 | 6e-05 | PASS |
| `load_step_50_100_50` | `max_abs_integrator_error` | 2.78994e-05 | 0.0001 | PASS |
| `load_step_50_100_50` | `max_abs_duty_raw_error` | 2.7895e-05 | 0.00015 | PASS |
| `load_step_50_100_50` | `max_abs_duty_cmd_error` | 2.7895e-05 | 0.00015 | PASS |
| `load_step_50_100_50` | `state_mismatch_count` | 0 | 0 | PASS |
| `load_step_50_100_50` | `fault_mismatch_count` | 0 | 0 | PASS |
| `load_step_50_100_50` | `pwm_mismatch_count` | 0 | 0 | PASS |
| `load_step_50_100_50` | `logic_flag_mismatch_count` | 0 | 0 | PASS |
| `load_step_50_100_50` | `arithmetic_overflow_count` | 0 | 0 | PASS |
| `load_step_50_100_50` | `input_conversion_overflow_count` | 0 | 0 | PASS |
| `load_step_50_100_50` | `max_raw_utilization_pct` | 4.88281 | 10 | PASS |
| `ocp_latch_clear` | `max_abs_vout_meas_v_error` | 4.8183e-07 | 1e-06 | PASS |
| `ocp_latch_clear` | `max_abs_vref_cmd_v_error` | 0.00047875 | 0.0011 | PASS |
| `ocp_latch_clear` | `max_abs_error_v_error` | 0.000478983 | 0.0011 | PASS |
| `ocp_latch_clear` | `max_abs_p_term_error` | 2.4414e-05 | 6e-05 | PASS |
| `ocp_latch_clear` | `max_abs_integrator_error` | 6.37916e-08 | 0.0001 | PASS |
| `ocp_latch_clear` | `max_abs_duty_raw_error` | 4.50318e-05 | 0.00015 | PASS |
| `ocp_latch_clear` | `max_abs_duty_cmd_error` | 4.50318e-05 | 0.00015 | PASS |
| `ocp_latch_clear` | `state_mismatch_count` | 0 | 0 | PASS |
| `ocp_latch_clear` | `fault_mismatch_count` | 0 | 0 | PASS |
| `ocp_latch_clear` | `pwm_mismatch_count` | 0 | 0 | PASS |
| `ocp_latch_clear` | `logic_flag_mismatch_count` | 0 | 0 | PASS |
| `ocp_latch_clear` | `arithmetic_overflow_count` | 0 | 0 | PASS |
| `ocp_latch_clear` | `input_conversion_overflow_count` | 0 | 0 | PASS |
| `ocp_latch_clear` | `max_raw_utilization_pct` | 4.88281 | 10 | PASS |
| `uvlo_blocks_pwm` | `max_abs_vout_meas_v_error` | 4.8183e-07 | 1e-06 | PASS |
| `uvlo_blocks_pwm` | `max_abs_vref_cmd_v_error` | 0.000478749 | 0.0011 | PASS |
| `uvlo_blocks_pwm` | `max_abs_error_v_error` | 0.000478983 | 0.0011 | PASS |
| `uvlo_blocks_pwm` | `max_abs_p_term_error` | 2.4414e-05 | 6e-05 | PASS |
| `uvlo_blocks_pwm` | `max_abs_integrator_error` | 6.37916e-08 | 0.0001 | PASS |
| `uvlo_blocks_pwm` | `max_abs_duty_raw_error` | 4.50318e-05 | 0.00015 | PASS |
| `uvlo_blocks_pwm` | `max_abs_duty_cmd_error` | 4.50318e-05 | 0.00015 | PASS |
| `uvlo_blocks_pwm` | `state_mismatch_count` | 0 | 0 | PASS |
| `uvlo_blocks_pwm` | `fault_mismatch_count` | 0 | 0 | PASS |
| `uvlo_blocks_pwm` | `pwm_mismatch_count` | 0 | 0 | PASS |
| `uvlo_blocks_pwm` | `logic_flag_mismatch_count` | 0 | 0 | PASS |
| `uvlo_blocks_pwm` | `arithmetic_overflow_count` | 0 | 0 | PASS |
| `uvlo_blocks_pwm` | `input_conversion_overflow_count` | 0 | 0 | PASS |
| `uvlo_blocks_pwm` | `max_raw_utilization_pct` | 4.88281 | 10 | PASS |
| `fixed_unit_tests` | `q20_scale_and_soft_start_constant` | 1 | 1 | PASS |
| `fixed_unit_tests` | `soft_start_first_step_without_overflow` | 1 | 1 | PASS |
| `fixed_unit_tests` | `positive_overflow_saturates_and_counts` | 1 | 1 | PASS |
| `fixed_unit_tests` | `negative_overflow_saturates_and_counts` | 1 | 1 | PASS |

## 结果边界

这份报告验证当前五个回放场景中，Q20 定点控制器与浮点 C 的数值误差、状态迁移、故障、PWM、逻辑标志和算术溢出。它不包含目标 MCU 指令耗时、ADC 码值换算、PWM 寄存器映射或硬件闭环。
