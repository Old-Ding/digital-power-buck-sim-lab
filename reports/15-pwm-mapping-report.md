# 第 15 章报告：Q20 duty 到 PWM 定时器比较值映射

本报告由 `scripts/run_pwm_mapping_tests.py` 生成，所有比较值、影子更新和立即关断结果来自真实编译执行的 `src/digital_power_pwm_map.c`。

## 摘要

- 编译器：`zig 0.16.0`
- C 回放行数：640
- 指标：PASS 15 / FAIL 0

```text
SUMMARY,OK,rows=640
```

```text
PASS,center_aligned_170mhz_200khz_contract
PASS,half_duty_waits_for_update_event
PASS,half_duty_applies_at_update_event
PASS,duty_above_limit_is_clamped
PASS,disable_is_immediate
SUMMARY,PASS,failures=0
```

## 指标

| 场景 | 指标 | 实际值 | 限制 | 状态 | 说明 |
| --- | --- | ---: | ---: | --- | --- |
| `resolution_72mhz` | `max_abs_effective_duty_error` | 0.00277824 | 0.00277873 | PASS | 比较值取整误差不得超过半个定时器计数加一个 Q20 LSB |
| `resolution_100mhz` | `max_abs_effective_duty_error` | 0.00200031 | 0.00200095 | PASS | 比较值取整误差不得超过半个定时器计数加一个 Q20 LSB |
| `resolution_170mhz` | `max_abs_effective_duty_error` | 0.00117691 | 0.00117742 | PASS | 比较值取整误差不得超过半个定时器计数加一个 Q20 LSB |
| `duty_clamp_170mhz` | `negative_duty_clamp` | 1 | 1 | PASS | 负 duty 必须钳位到 0 |
| `duty_clamp_170mhz` | `high_duty_clamp` | 1 | 1 | PASS | 超过 65% 的 duty 必须钳位 |
| `duty_clamp_170mhz` | `max_compare_counts` | 276 | 276 | PASS | 65% Q20 duty 映射后的比较值不得超过 276 counts |
| `shadow_update_sequence` | `queue_does_not_change_active_compare` | 1 | 1 | PASS | 预装载写入不得在周期中间改变有效比较值 |
| `shadow_update_sequence` | `update_event_applies_pending` | 1 | 1 | PASS | 更新事件后 pending 标志必须清除 |
| `shadow_update_sequence` | `disable_is_immediate` | 1 | 1 | PASS | 保护关断不等待更新事件 |
| `all` | `arithmetic_overflow_count` | 0 | 0 | PASS | Q20 duty 到比较值的整数运算不得溢出 |
| `pwm_unit_tests` | `center_aligned_170mhz_200khz_contract` | 1 | 1 | PASS | PWM 映射 C 单元测试 |
| `pwm_unit_tests` | `half_duty_waits_for_update_event` | 1 | 1 | PASS | PWM 映射 C 单元测试 |
| `pwm_unit_tests` | `half_duty_applies_at_update_event` | 1 | 1 | PASS | PWM 映射 C 单元测试 |
| `pwm_unit_tests` | `duty_above_limit_is_clamped` | 1 | 1 | PASS | PWM 映射 C 单元测试 |
| `pwm_unit_tests` | `disable_is_immediate` | 1 | 1 | PASS | PWM 映射 C 单元测试 |

## 边界

本报告验证通用中心对齐 PWM 的周期计数、Q20 duty 舍入、65%限幅、100ns死区计数、影子寄存器更新和立即关断语义。它不等于具体 MCU 的 ARR/CCR/BDTR 寄存器已经配置，也不包含真实门极波形和死区测量。
