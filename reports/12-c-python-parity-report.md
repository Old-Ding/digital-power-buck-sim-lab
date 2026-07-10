# 第 12 章报告：Python 参考实现与真实 C 控制器逐周期对照

本报告由 `scripts/run_c_python_parity.py` 生成。Python 参考结果来自第 10 章同等离散算法测试台；C 结果来自编译后的 `src/digital_power_control.c`。

## 执行链

- 电脑端 C 编译器：`zig 0.16.0`
- 对照场景：5
- 逐周期比较行数：80400
- 公开抽样行数：4025
- 指标结果：PASS 55 / FAIL 0

C 回放程序输出：

```text
SUMMARY,OK,rows=80400
```

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
| `steady_12v` | `max_abs_vref_cmd_v_error` | 0 | 0.0015 | PASS |
| `steady_12v` | `max_abs_error_v_error` | 0 | 0.0015 | PASS |
| `steady_12v` | `max_abs_p_term_error` | 0 | 7.5e-05 | PASS |
| `steady_12v` | `max_abs_integrator_error` | 2.13333e-10 | 1e-06 | PASS |
| `steady_12v` | `max_abs_duty_raw_error` | 3.66667e-09 | 0.00015 | PASS |
| `steady_12v` | `max_abs_duty_cmd_error` | 3.66667e-09 | 0.00015 | PASS |
| `steady_12v` | `state_mismatch_count` | 0 | 0 | PASS |
| `steady_12v` | `fault_mismatch_count` | 0 | 0 | PASS |
| `steady_12v` | `pwm_mismatch_count` | 0 | 0 | PASS |
| `steady_12v` | `logic_flag_mismatch_count` | 0 | 0 | PASS |
| `soft_start_40ms` | `max_abs_vout_meas_v_error` | 5.22851e-07 | 1e-06 | PASS |
| `soft_start_40ms` | `max_abs_vref_cmd_v_error` | 0.0005587 | 0.0015 | PASS |
| `soft_start_40ms` | `max_abs_error_v_error` | 0.000558524 | 0.0015 | PASS |
| `soft_start_40ms` | `max_abs_p_term_error` | 2.79262e-05 | 7.5e-05 | PASS |
| `soft_start_40ms` | `max_abs_integrator_error` | 2.9541e-08 | 1e-06 | PASS |
| `soft_start_40ms` | `max_abs_duty_raw_error` | 5.12136e-05 | 0.00015 | PASS |
| `soft_start_40ms` | `max_abs_duty_cmd_error` | 5.12136e-05 | 0.00015 | PASS |
| `soft_start_40ms` | `state_mismatch_count` | 0 | 0 | PASS |
| `soft_start_40ms` | `fault_mismatch_count` | 0 | 0 | PASS |
| `soft_start_40ms` | `pwm_mismatch_count` | 0 | 0 | PASS |
| `soft_start_40ms` | `logic_flag_mismatch_count` | 0 | 0 | PASS |
| `load_step_50_100_50` | `max_abs_vout_meas_v_error` | 5.23828e-07 | 1e-06 | PASS |
| `load_step_50_100_50` | `max_abs_vref_cmd_v_error` | 0 | 0.0015 | PASS |
| `load_step_50_100_50` | `max_abs_error_v_error` | 4.77048e-07 | 0.0015 | PASS |
| `load_step_50_100_50` | `max_abs_p_term_error` | 2.50259e-08 | 7.5e-05 | PASS |
| `load_step_50_100_50` | `max_abs_integrator_error` | 1.21683e-08 | 1e-06 | PASS |
| `load_step_50_100_50` | `max_abs_duty_raw_error` | 7.92777e-08 | 0.00015 | PASS |
| `load_step_50_100_50` | `max_abs_duty_cmd_error` | 7.92777e-08 | 0.00015 | PASS |
| `load_step_50_100_50` | `state_mismatch_count` | 0 | 0 | PASS |
| `load_step_50_100_50` | `fault_mismatch_count` | 0 | 0 | PASS |
| `load_step_50_100_50` | `pwm_mismatch_count` | 0 | 0 | PASS |
| `load_step_50_100_50` | `logic_flag_mismatch_count` | 0 | 0 | PASS |
| `ocp_latch_clear` | `max_abs_vout_meas_v_error` | 4.53957e-07 | 1e-06 | PASS |
| `ocp_latch_clear` | `max_abs_vref_cmd_v_error` | 0.00019569 | 0.0015 | PASS |
| `ocp_latch_clear` | `max_abs_error_v_error` | 0.000195656 | 0.0015 | PASS |
| `ocp_latch_clear` | `max_abs_p_term_error` | 9.78282e-06 | 7.5e-05 | PASS |
| `ocp_latch_clear` | `max_abs_integrator_error` | 2.13333e-10 | 1e-06 | PASS |
| `ocp_latch_clear` | `max_abs_duty_raw_error` | 1.79424e-05 | 0.00015 | PASS |
| `ocp_latch_clear` | `max_abs_duty_cmd_error` | 1.79424e-05 | 0.00015 | PASS |
| `ocp_latch_clear` | `state_mismatch_count` | 0 | 0 | PASS |
| `ocp_latch_clear` | `fault_mismatch_count` | 0 | 0 | PASS |
| `ocp_latch_clear` | `pwm_mismatch_count` | 0 | 0 | PASS |
| `ocp_latch_clear` | `logic_flag_mismatch_count` | 0 | 0 | PASS |
| `uvlo_blocks_pwm` | `max_abs_vout_meas_v_error` | 4.53957e-07 | 1e-06 | PASS |
| `uvlo_blocks_pwm` | `max_abs_vref_cmd_v_error` | 0.00013297 | 0.0015 | PASS |
| `uvlo_blocks_pwm` | `max_abs_error_v_error` | 0.000132989 | 0.0015 | PASS |
| `uvlo_blocks_pwm` | `max_abs_p_term_error` | 6.6494e-06 | 7.5e-05 | PASS |
| `uvlo_blocks_pwm` | `max_abs_integrator_error` | 2.13333e-10 | 1e-06 | PASS |
| `uvlo_blocks_pwm` | `max_abs_duty_raw_error` | 1.21908e-05 | 0.00015 | PASS |
| `uvlo_blocks_pwm` | `max_abs_duty_cmd_error` | 1.21908e-05 | 0.00015 | PASS |
| `uvlo_blocks_pwm` | `state_mismatch_count` | 0 | 0 | PASS |
| `uvlo_blocks_pwm` | `fault_mismatch_count` | 0 | 0 | PASS |
| `uvlo_blocks_pwm` | `pwm_mismatch_count` | 0 | 0 | PASS |
| `uvlo_blocks_pwm` | `logic_flag_mismatch_count` | 0 | 0 | PASS |

## 如何解释

Python 参考实现和 C 控制器接收完全相同的逐周期输入。数值量按浮点误差容差比较；控制状态、故障、PWM 和逻辑标志要求逐周期一致。

## 边界

这份报告可以发现 Python 到 C 改写时的参数、执行顺序、状态迁移和输出差异。Python 参考实现仍然是软件模型，不是硬件测量真值；本报告不覆盖目标 MCU 编译、执行时间、定点化、ADC/PWM 寄存器或硬件闭环。
