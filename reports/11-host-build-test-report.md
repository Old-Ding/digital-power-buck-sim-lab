# 第 11 章报告：电脑端编译和单元测试检查

本报告由 `scripts/run_host_build_tests.py` 生成，用来判断第 10 章的 C 风格控制器是否已经具备电脑端编译和单元测试证据。

## 检查结果

| Gate | Status | Detail |
| --- | --- | --- |
| `toolchain` | PASS | 检测到 zig 0.16.0: C:\Users\ww\AppData\Local\Microsoft\WinGet\Packages\zig.zig_Microsoft.Winget.Source_8wekyb3d8bbwe\zig-x86_64-windows-0.16.0\zig.exe |
| `build` | PASS | 生成 D:\codex\digital-power-buck-sim-lab\artifacts\host-build\chapter11\digital_power_control_host_tests.exe |
| `unit_tests` | PASS | 电脑端单元测试通过 |
| `report` | PASS | 已生成 CSV、PNG 和 Markdown 报告 |

## 工具链

- 检测到的编译器：`zig 0.16.0`
- 编译器路径：`C:\Users\ww\AppData\Local\Microsoft\WinGet\Packages\zig.zig_Microsoft.Winget.Source_8wekyb3d8bbwe\zig-x86_64-windows-0.16.0\zig.exe`

## 编译命令

```powershell
C:\Users\ww\AppData\Local\Microsoft\WinGet\Packages\zig.zig_Microsoft.Winget.Source_8wekyb3d8bbwe\zig-x86_64-windows-0.16.0\zig.exe cc -std=c99 -Wall -Wextra -Werror -I D:\codex\digital-power-buck-sim-lab\src D:\codex\digital-power-buck-sim-lab\src\digital_power_control.c D:\codex\digital-power-buck-sim-lab\tests\test_digital_power_control_host.c -o D:\codex\digital-power-buck-sim-lab\artifacts\host-build\chapter11\digital_power_control_host_tests.exe
```

## 测试输出

```text
PASS,default_ts_ctrl,actual=5e-06,expected=5e-06,tolerance=1e-09
PASS,default_vref,actual=12,expected=12,tolerance=1e-06
PASS,default_duty_max,actual=0.65,expected=0.65,tolerance=1e-06
PASS,default_ocp,actual=6.5,expected=6.5,tolerance=1e-06
PASS,init_state_idle
PASS,init_fault_none
PASS,init_filter_seed,actual=12,expected=12,tolerance=1e-06
PASS,init_integrator_zero,actual=0,expected=0,tolerance=1e-06
PASS,soft_start_state
PASS,soft_start_pwm_enabled
PASS,soft_start_vref_first_step,actual=0.0015,expected=0.0015,tolerance=1e-07
PASS,soft_start_duty_small_positive
PASS,ocp_enters_fault
PASS,ocp_latched
PASS,ocp_pwm_disabled
PASS,ocp_duty_zero,actual=0,expected=0,tolerance=1e-06
PASS,ocp_clear_while_fault_stays_latched
PASS,ocp_clear_after_fault_removed
PASS,ocp_clear_restarts_soft_start
SUMMARY,PASS,failures=0
```

## 边界

读这份报告时，先看 `toolchain`、`build`、`unit_tests` 三个检查项。它们对应的是电脑端证据；不要把这个结果误读成定点化安全、MCU 寄存器适配、ISR 时序、HIL 或硬件闭环已经完成。
