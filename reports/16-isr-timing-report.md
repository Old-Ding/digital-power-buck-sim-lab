# 第 16 章报告：控制 ISR 执行顺序与时间预算

本报告由 `scripts/run_isr_timing_tests.py` 生成。顺序与故障行为来自真实编译执行的 C 编排层；主机计时只作为回归信息。

## 摘要

- 编译器：`zig 0.16.0`
- 指标：PASS 13 / FAIL 0 / INFO 4
- 控制周期：5.0 us
- ISR 目标预算：3.5 us

```text
PASS,previous_compare_applies_at_isr_entry
PASS,new_compare_waits_for_next_update
PASS,queued_compare_has_one_cycle_latency
PASS,nominal_adc_and_arithmetic_are_clean
PASS,ocp_latches_fault_and_commands_disable
PASS,ocp_disable_is_immediate
SUMMARY,PASS,failures=0
```

```text
SUMMARY,OK,cycles=6
SUMMARY,OK,batches=200,iterations_per_batch=10000,checksum=552552099
```

## 指标

| 场景 | 指标 | 实际值 | 限制/参考 | 状态 | 说明 |
| --- | --- | ---: | ---: | --- | --- |
| `isr_sequence` | `initial_update_applies_preload` | 1 | 1 | PASS | 中断入口先应用上一周期预装载值 |
| `isr_sequence` | `one_cycle_compare_latency` | 1 | 1 | PASS | 本周期计算的 compare 在下一更新事件生效 |
| `ocp` | `active_pwm_disable_immediate` | 1 | 1 | PASS | OCP 周期内立即清除 active enable |
| `fault_clear` | `restart_waits_for_update` | 1 | 1 | PASS | 重新使能等待下一更新事件 |
| `normal` | `mapping_and_arithmetic_clean` | 1 | 1 | PASS | 正常输入无钳位和整数溢出 |
| `target_budget` | `allocated_isr_ns` | 3500 | 3500 | PASS | 目标 MCU 的中断执行预算，不是主机实测值 |
| `target_budget` | `reserve_ns` | 1500 | 1500 | PASS | 为中断延迟、抖动和高优先级抢占保留的余量 |
| `host_benchmark` | `host_batch_p50_ns_per_call` | 44.71 | 5000 | INFO | 主机批次均摊耗时，仅用于回归，不判定 MCU 5us 截止时间 |
| `host_benchmark` | `host_batch_p95_ns_per_call` | 55.3295 | 5000 | INFO | 主机批次均摊耗时，仅用于回归，不判定 MCU 5us 截止时间 |
| `host_benchmark` | `host_batch_p99_ns_per_call` | 60.0179 | 5000 | INFO | 主机批次均摊耗时，仅用于回归，不判定 MCU 5us 截止时间 |
| `host_benchmark` | `host_batch_max_ns_per_call` | 63.48 | 5000 | INFO | 主机批次均摊耗时，仅用于回归，不判定 MCU 5us 截止时间 |
| `isr_unit_tests` | `previous_compare_applies_at_isr_entry` | 1 | 1 | PASS | C 中断编排单元测试 |
| `isr_unit_tests` | `new_compare_waits_for_next_update` | 1 | 1 | PASS | C 中断编排单元测试 |
| `isr_unit_tests` | `queued_compare_has_one_cycle_latency` | 1 | 1 | PASS | C 中断编排单元测试 |
| `isr_unit_tests` | `nominal_adc_and_arithmetic_are_clean` | 1 | 1 | PASS | C 中断编排单元测试 |
| `isr_unit_tests` | `ocp_latches_fault_and_commands_disable` | 1 | 1 | PASS | C 中断编排单元测试 |
| `isr_unit_tests` | `ocp_disable_is_immediate` | 1 | 1 | PASS | C 中断编排单元测试 |

## 证据边界

顺序测试可以判断上一周期 compare 是否先应用、OCP 是否在同一次调用中关闭 active enable。3.5 us 是目标分配预算，Windows 主机批次耗时是回归基线；只有目标 MCU 构建后的周期计数器或示波器测量才能判断 5 us 截止时间是否满足。
