# 第 11 章复现说明：如何复现 C 控制器电脑端编译与单元测试检查

本说明对应文章：`blog/11-host-build-test-gate.md`

本章目标是复现一条上板前的软件检查流程：检测 C 编译器、编译第十章控制器、运行电脑端基础测试，并生成 CSV、PNG 和 Markdown 报告。

## 各文件的职责

| 角色 | 文件或工具 | 职责 |
| --- | --- | --- |
| 被测代码 | `src/digital_power_control.c` | 实现控制器状态和输出逻辑 |
| 测试程序 | `tests/test_digital_power_control_host.c` | 准备输入、调用控制器、判断 PASS/FAIL |
| C 编译器 | Zig、GCC、Clang 或 MSVC | 把两个 C 文件编译成电脑端测试程序 |
| 自动化脚本 | `scripts/run_host_build_tests.py` | 查找编译器、编译、运行测试并生成报告 |

`run_host_build_tests.py` 是本仓库为第十一章配套编写的脚本，不是 Windows、Zig、MATLAB 或 PLECS 自带文件。控制行为是否通过由 C 测试程序中的 `expect_true()` 和 `expect_close()` 决定，Python 脚本只负责执行和记录。

## 复现边界

| 项目 | 本章覆盖 |
| --- | --- |
| 工具链检测 | `CC`、`zig`、`gcc`、`clang`、`cc`、`cl`、WinGet Zig、Visual Studio 2022 常见 `cl.exe` 路径 |
| 编译对象 | `src/digital_power_control.c` |
| 测试入口 | `tests/test_digital_power_control_host.c` |
| 输出报告 | `reports/11-host-build-test-report.md` |

读本章结果时，先看 `toolchain`、`build`、`unit_tests` 三个检查项；不要把电脑端检查误读成定点化、HAL、ISR、HIL 或硬件闭环已经完成。

## 环境要求

必须具备：

| 工具 | 用途 |
| --- | --- |
| Python 3 | 运行检查脚本 |
| matplotlib | 生成检查结果图 |

可选工具：

| 工具 | 用途 |
| --- | --- |
| Zig 0.16.0 / `zig cc` | 本仓库当前验证过的 Windows 电脑端 C 编译器 |
| gcc / clang / cc | 电脑端编译 C 控制器和测试文件 |
| MSVC cl.exe | Windows 电脑端编译 |

Windows 上可以用 WinGet 安装 Zig：

```powershell
winget install --id zig.zig -e --scope user --accept-source-agreements --accept-package-agreements
```

如果没有 C 编译器，脚本仍会生成报告，但 `toolchain` 会是 `BLOCKED`，`build` 和 `unit_tests` 会是 `SKIPPED`。这表示构建还没有开始，不表示 C 源码已经失败。

## 先手动编译和运行

如果 Zig 已经加入 `PATH`，在仓库根目录运行：

```powershell
New-Item -ItemType Directory -Force artifacts\host-build\chapter11 | Out-Null

zig cc -std=c99 -Wall -Wextra -Werror `
  -I src `
  src\digital_power_control.c `
  tests\test_digital_power_control_host.c `
  -o artifacts\host-build\chapter11\digital_power_control_host_tests.exe

.\artifacts\host-build\chapter11\digital_power_control_host_tests.exe
```

最后一行应为：

```text
SUMMARY,PASS,failures=0
```

这两条命令分别对应“编译测试程序”和“运行测试程序”。如果 Zig 没有加入 `PATH`，可以使用完整的 `zig.exe` 路径，或者直接使用下一节的一键脚本自动查找。

## 一键运行

在仓库根目录运行：

```powershell
python scripts\run_host_build_tests.py
```

当前报告生成环境输出摘要：

```text
已生成第 11 章电脑端编译测试检查报告。
summary,pass=4,blocked=0,skipped=0,fail=0
toolchain,zig,zig 0.16.0
```

完整编译器路径和实际编译命令记录在 `reports/11-host-build-test-report.md`。

## 生成文件

| 文件 | 内容 |
| --- | --- |
| `reports/11-host-build-summary.csv` | 检查状态 CSV |
| `reports/11-host-build-test-report.md` | Markdown 测试报告 |
| `waveforms/11-host-build-gate.png` | 检查结果图 |
| `artifacts/host-build/chapter11/` | 编译临时目录，已被 `.gitignore` 忽略 |

## 当前结果

| Gate | Status | 说明 |
| --- | --- | --- |
| `toolchain` | PASS | 检测到 Zig 0.16.0 |
| `build` | PASS | 已生成电脑端测试可执行文件 |
| `unit_tests` | PASS | 电脑端单元测试通过 |
| `report` | PASS | 已生成 CSV、PNG 和 Markdown 报告 |

## 当前编译命令

本机检测到 Zig 后，脚本使用 `zig cc` 编译控制器和测试入口。完整路径以 `reports/11-host-build-test-report.md` 为准，命令结构如下：

```powershell
zig cc -std=c99 -Wall -Wextra -Werror -I src src\digital_power_control.c tests\test_digital_power_control_host.c -o artifacts\host-build\chapter11\digital_power_control_host_tests.exe
```

如果系统里使用 `gcc`、`clang` 或 MSVC `cl.exe`，脚本会按对应工具链生成等价命令。gcc/clang/Zig 使用 `-Wall -Wextra -Werror`，MSVC 使用 `/W4 /WX`。

当前测试程序输出的关键行如下：

```text
PASS,soft_start_vref_first_step,actual=0.0015,expected=0.0015,tolerance=1e-07
PASS,soft_start_duty_small_positive
PASS,ocp_enters_fault
PASS,ocp_latched
PASS,ocp_pwm_disabled
PASS,ocp_clear_while_fault_stays_latched
PASS,ocp_clear_after_fault_removed
PASS,ocp_clear_restarts_soft_start
SUMMARY,PASS,failures=0
```

## 常见问题

### 1. 如果结果是 BLOCKED，先看什么

先看本机是否能在 PowerShell 里找到 `zig`、`gcc`、`clang`、`cc` 或 `cl`。如果是 WinGet 安装的 Zig，脚本也会扫描 WinGet 常见安装目录。

### 2. BLOCKED 是不是 C 代码写错了

`BLOCKED` 表示工具链不存在或不可见，编译命令还没有执行。源码是否能编译，需要安装或配置 C 编译器后重新运行脚本。

### 3. 为什么要把 warning 当成错误

电脑端编译阶段越早暴露类型、初始化、头文件和接口问题，越不容易把问题带到 MCU 工程里。脚本对 gcc/clang 使用 `-Werror`，对 MSVC 使用 `/WX`。

### 4. 为什么不直接进入定点化

定点化依赖一个可编译、可测试的浮点基准版本。先让电脑端编译和单元测试检查跑起来，后面定点化才有对照基准。

### 5. 编译临时文件为什么不提交

`artifacts/host-build/chapter11/` 是本机生成目录，已经由 `.gitignore` 忽略。公开仓库只提交源码、脚本、报告和可复现图表。

### 6. Python 脚本是从哪里来的

它是本仓库为第十一章编写的自动化辅助文件，用来替代手动查找编译器、拼接编译命令、运行测试和整理报告。它不替代 C 测试程序中的预期条件，也不参与控制算法计算。
