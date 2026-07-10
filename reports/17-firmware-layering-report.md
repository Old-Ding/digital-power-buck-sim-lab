# 第 17 章报告：实时/后台任务与 HAL 适配边界

本报告由 `scripts/run_firmware_layering_tests.py` 生成。HAL 调用顺序、命令边界和任务归属来自真实编译执行的 C 固件编排层与假硬件适配器。

## 摘要

- 编译器：`zig 0.16.0`
- 指标：PASS 21 / FAIL 0

```text
PASS,isr_calls_only_realtime_hal_operations
PASS,background_calls_only_communication_and_storage
PASS,ocp_disable_precedes_preload_write
PASS,ocp_turns_off_fake_hardware
PASS,background_command_waits_for_isr_boundary
PASS,command_is_atomic_at_isr_boundary
PASS,adc_failure_uses_fail_safe_hal_order
PASS,adc_failure_is_visible_in_telemetry
PASS,telemetry_is_available
PASS,telemetry_copy_uses_critical_section
SUMMARY,PASS,failures=0
```

```text
SUMMARY,OK,phases=12,events=34,control_cycles=7
```

## 指标

| 场景 | 指标 | 实际值 | 期望 | 状态 | 说明 |
| --- | --- | ---: | ---: | --- | --- |
| `ownership` | `isr_realtime_operations_only` | 1 | 1 | PASS | ISR 事件中不得出现通信、存储或后台临界区 |
| `ownership` | `background_services_only` | 1 | 1 | PASS | 后台步骤只调用通信与存储服务 |
| `normal_isr` | `normal_hal_order` | 1 | 1 | PASS | 正常周期按更新、ADC、PWM 预装载顺序调用 HAL |
| `ocp_isr` | `disable_precedes_preload_write` | 1 | 1 | PASS | OCP 立即关断必须先于预装载写入 |
| `adc_failure` | `adc_failure_fail_safe_order` | 1 | 1 | PASS | ADC 读取失败时立即关断并写入关闭预装载 |
| `shared_exchange` | `commands_use_critical_section` | 1 | 1 | PASS | 后台命令使用短临界区完整发布 |
| `shared_exchange` | `telemetry_copy_uses_critical_section` | 1 | 1 | PASS | 后台遥测读取使用短临界区复制快照 |
| `command_boundary` | `disable_commits_at_next_isr` | 1 | 1 | PASS | 后台 disable 命令只在下一 ISR 边界提交 |
| `command_boundary` | `restart_waits_for_pwm_update` | 1 | 1 | PASS | 重新使能先写 pending，再由更新事件生效 |
| `adc_failure` | `failure_visible_and_pwm_off` | 1 | 1 | PASS | ADC 无效状态进入遥测且硬件 PWM 关闭 |
| `background` | `background_does_not_advance_control` | 1 | 1 | PASS | 后台步骤不得推进控制周期 |
| `firmware_unit_tests` | `isr_calls_only_realtime_hal_operations` | 1 | 1 | PASS | C 固件分层单元测试 |
| `firmware_unit_tests` | `background_calls_only_communication_and_storage` | 1 | 1 | PASS | C 固件分层单元测试 |
| `firmware_unit_tests` | `ocp_disable_precedes_preload_write` | 1 | 1 | PASS | C 固件分层单元测试 |
| `firmware_unit_tests` | `ocp_turns_off_fake_hardware` | 1 | 1 | PASS | C 固件分层单元测试 |
| `firmware_unit_tests` | `background_command_waits_for_isr_boundary` | 1 | 1 | PASS | C 固件分层单元测试 |
| `firmware_unit_tests` | `command_is_atomic_at_isr_boundary` | 1 | 1 | PASS | C 固件分层单元测试 |
| `firmware_unit_tests` | `adc_failure_uses_fail_safe_hal_order` | 1 | 1 | PASS | C 固件分层单元测试 |
| `firmware_unit_tests` | `adc_failure_is_visible_in_telemetry` | 1 | 1 | PASS | C 固件分层单元测试 |
| `firmware_unit_tests` | `telemetry_is_available` | 1 | 1 | PASS | C 固件分层单元测试 |
| `firmware_unit_tests` | `telemetry_copy_uses_critical_section` | 1 | 1 | PASS | C 固件分层单元测试 |

## 证据边界

假 HAL 可以验证谁调用 ADC/PWM、调用先后和共享数据边界。它没有具体 MCU 寄存器地址、DMA 标志、NVIC 配置或 Flash 驱动，因此本报告属于平台无关固件集成证据，不等于目标板外设已经工作。
