# 第 17 章复现说明：实时/后台分层与 HAL 适配边界

## 目标

复现控制 ISR、后台服务和共享数据交换的职责边界，验证正常、disable、restart、OCP 与 ADC 读取失败场景中的 HAL 调用顺序。

## 环境

- Python 3
- matplotlib
- Zig、GCC、Clang 或 MSVC 中任一 C 编译器

当前验证环境为 Windows 11、Python 3、Zig 0.16.0。

## 最短命令

```powershell
python scripts\run_firmware_layering_tests.py
```

预期摘要：

```text
summary,pass=21,fail=0,phases=12,events=34
toolchain,zig,zig 0.16.0
ownership,isr=update+adc+pwm,background=communication+storage,shared=critical_sections
```

## 手动编译单元测试

```powershell
New-Item -ItemType Directory -Force artifacts\host-build\chapter17 | Out-Null

zig cc -std=c99 -O2 -Wall -Wextra -Werror `
  -I src -I tests `
  src\digital_power_adc_map.c `
  src\digital_power_control_fixed.c `
  src\digital_power_pwm_map.c `
  src\digital_power_control_isr.c `
  src\digital_power_firmware.c `
  tests\fake_digital_power_hal.c `
  tests\test_digital_power_firmware.c `
  -o artifacts\host-build\chapter17\digital_power_firmware_tests.exe

.\artifacts\host-build\chapter17\digital_power_firmware_tests.exe
```

预期 10 个单元测试全部 PASS。

## 回放阶段

| 阶段 | 期望调用 |
| --- | --- |
| `command_enable` | `critical_enter → critical_exit` |
| `startup_isr` | `pwm_update → adc_read → pwm_write` |
| `apply_isr` | `pwm_update → adc_read → pwm_write` |
| `background` | `communication → storage` |
| `telemetry_read` | `critical_enter → critical_exit` |
| `command_disable` | `critical_enter → critical_exit` |
| `disable_isr` | `pwm_update → adc_read → pwm_disable → pwm_write` |
| `command_restart` | `critical_enter → critical_exit` |
| `restart_queue_isr` | `pwm_update → adc_read → pwm_write` |
| `restart_apply_isr` | `pwm_update → adc_read → pwm_write` |
| `ocp_isr` | `pwm_update → adc_read → pwm_disable → pwm_write` |
| `adc_failure_isr` | `pwm_update → adc_read → pwm_disable → pwm_write` |

## 命令边界检查

后台发布 disable 后、ISR 到达前：

```text
active_command_enable  = 1
pending_command_enable = 0
command_pending        = 1
```

下一 ISR 后：

```text
active_command_enable = 0
command_pending       = 0
hal_active_enable     = 0
```

restart 先把 `hal_pending_enable` 置 1，下一次更新事件才把 `hal_active_enable` 置 1。

## 生成文件

| 文件 | 内容 |
| --- | --- |
| `waveforms/17-hal-events.csv` | 12 个阶段的 34 条 HAL 事件 |
| `waveforms/17-firmware-states.csv` | 命令、遥测和假硬件状态 |
| `waveforms/17-task-ownership.csv` | 三个职责层的事件计数矩阵 |
| `waveforms/17-layering-summary.csv` | 21 项 PASS/FAIL 指标 |
| `waveforms/17-hal-call-order.png` | HAL 调用顺序图 |
| `waveforms/17-task-ownership.png` | 职责矩阵图 |
| `reports/17-firmware-layering-report.md` | 完整报告 |

## 常见失败

### ISR 事件里出现 communication 或 storage

检查是否在控制中断中调用了协议解析、日志输出或 Flash 写入。把它们移到 `DpFirmware_BackgroundStep()` 对应的平台后台实现。

### OCP 先 pwm_write 再 pwm_disable

调整适配层顺序。立即关断当前 active 输出必须先执行，预装载写入只负责后续周期。

### 后台 disable 发布后立即修改 active_command

后台只能写 pending 命令。完整命令由下一次控制 ISR 在周期边界提交。

### 读取遥测时字段来自不同周期

复制整个快照时使用短临界区；离开临界区后再格式化、发送或保存。

### 临界区包含通信或 Flash 操作

缩小临界区，使其只覆盖结构复制。长时间屏蔽控制 ISR 会破坏第十六章的 5 us 周期约束。

### 假 HAL 通过但目标板没有 PWM

假 HAL 不包含目标寄存器。检查目标 HAL 的定时器时钟、ARR/CCR、预装载、主输出使能、ADC 触发和中断标志。
