# 第 16 章复现说明：控制 ISR 顺序与时间预算

## 目标

复现 PWM 更新、ADC 映射、Q20 控制和下一周期 PWM 排队的执行顺序，验证 OCP 立即关断与同步重启，并生成目标时间预算和 Windows 主机回归基准。

## 环境

- Python 3
- matplotlib
- Zig、GCC、Clang 或 MSVC 中任一 C 编译器

当前验证环境为 Windows 11、Python 3、Zig 0.16.0。

## 最短命令

```powershell
python scripts\run_isr_timing_tests.py
```

预期指标数量固定为：

```text
summary,pass=13,fail=0,info=4,cycles=6,batches=200
target,period_ns=5000,isr_budget_ns=3500,reserve_ns=1500
```

主机 P50/P99/最大值会随机器负载变化，状态始终为 INFO。

## 手动编译顺序单元测试

```powershell
New-Item -ItemType Directory -Force artifacts\host-build\chapter16 | Out-Null

zig cc -std=c99 -O2 -Wall -Wextra -Werror `
  -I src `
  src\digital_power_adc_map.c `
  src\digital_power_control_fixed.c `
  src\digital_power_pwm_map.c `
  src\digital_power_control_isr.c `
  tests\test_digital_power_control_isr.c `
  -o artifacts\host-build\chapter16\digital_power_control_isr_tests.exe

.\artifacts\host-build\chapter16\digital_power_control_isr_tests.exe
```

预期：

```text
PASS,previous_compare_applies_at_isr_entry
PASS,new_compare_waits_for_next_update
PASS,queued_compare_has_one_cycle_latency
PASS,nominal_adc_and_arithmetic_are_clean
PASS,ocp_latches_fault_and_commands_disable
PASS,ocp_disable_is_immediate
SUMMARY,PASS,failures=0
```

## 六周期回放场景

| 周期 | 场景 | 检查重点 |
| ---: | --- | --- |
| 0 | `normal` | 85 counts 先进入 active，新 compare 只进入 pending |
| 1 | `normal` | active 等于周期 0 的 pending |
| 2 | `ocp` | 约 7 A 触发 OCP，active enable 立即关闭 |
| 3 | `ocp` | compare 在更新事件归零，故障保持锁存 |
| 4 | `clear_fault` | enable 命令恢复，active enable 仍关闭 |
| 5 | `restart` | 更新事件后 active enable 同步恢复 |

回放输出位于 `waveforms/16-isr-sequence.csv`。

## 时间预算

| 阶段 | 预算 |
| --- | ---: |
| 更新事件与入口 | 250 ns |
| ADC 快照与映射 | 700 ns |
| 定点控制与保护 | 1700 ns |
| PWM 排队与关断 | 500 ns |
| 状态快照与退出 | 350 ns |
| ISR 合计 | 3500 ns |
| 抖动与抢占余量 | 1500 ns |

预算表是目标设计约束。目标 MCU 上应使用周期计数器、GPIO 翻转或示波器重新测量最坏执行时间。

## 主机基准方法

`tests/benchmark_digital_power_control_isr.c` 先预热 20,000 次，再执行 200 批，每批 10,000 次调用。每个 CSV 点是批次总耗时除以 10,000 的均摊值，不是单次中断最坏耗时。

当前一次运行得到：

| 指标 | 值 |
| --- | ---: |
| P50 | 45.40 ns/call |
| P95 | 50.06 ns/call |
| P99 | 59.36 ns/call |
| 最大批次均摊 | 60.57 ns/call |

不同电脑或后台负载会得到不同数值，不应把这些数值设为跨机器硬门限。

## 生成文件

| 文件 | 内容 |
| --- | --- |
| `waveforms/16-isr-budget.csv` | 5 us 周期预算分配 |
| `waveforms/16-isr-sequence.csv` | 六周期真实 C 回放 |
| `waveforms/16-isr-host-timing.csv` | 200 批主机均摊耗时 |
| `waveforms/16-isr-summary.csv` | PASS/FAIL/INFO 指标 |
| `waveforms/16-isr-sequence.png` | compare 与 enable 时序 |
| `waveforms/16-isr-budget-and-host-timing.png` | 目标预算和主机 INFO 基准 |
| `reports/16-isr-timing-report.md` | 测试报告 |

## 常见失败

### active compare 与本周期 pending 同时变化

检查中断编排是否先调用 `DpPwmMap_ApplyUpdateEvent()`，再运行控制器和 Queue。不要在 Queue 后再次应用更新事件。

### OCP 后 active enable 仍为 true

检查控制器是否输出 `pwm_enable=false`，以及 PWM 映射层的关闭路径是否立即清除 active enable。

### 清故障时 PWM 在周期中间重新打开

重新使能只能写入 pending enable，并等待下一更新事件；立即动作只用于关断。

### 主机基准偶发尖峰

主机调度、杀毒软件和后台任务都会影响批次耗时。先重复运行确认基线；不要通过删除数据点让曲线变得平滑。

### 目标 MCU 实测超过 3.5 us

先用分阶段 GPIO 或周期计数器定位耗时，再检查除法、64 位运算、未优化构建和中断内日志。不要只提高 5 us 总门限来掩盖超时。
