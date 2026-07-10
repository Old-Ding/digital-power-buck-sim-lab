# 第 11 章复现说明：如何复现 C 控制器 Host 编译与单元测试门禁

本说明对应文章：`blog/11-host-build-test-gate.md`

本章目标是复现第二季入口门禁：检测 C 编译器、尝试编译第十章控制器、运行 host 单元测试，并生成 CSV、PNG 和 Markdown 报告。

## 复现边界

| 项目 | 本章覆盖 |
| --- | --- |
| 工具链检测 | `CC`、`gcc`、`clang`、`cc`、`cl`、Visual Studio 2022 常见 `cl.exe` 路径 |
| 编译对象 | `src/digital_power_control.c` |
| 测试入口 | `tests/test_digital_power_control_host.c` |
| 输出报告 | `reports/11-host-build-test-report.md` |

读本章结果时，先看 `toolchain`、`build`、`unit_tests` 三个门禁；不要把 host 门禁误读成定点化、HAL、ISR、HIL 或硬件闭环已经完成。

## 环境要求

必须具备：

| 工具 | 用途 |
| --- | --- |
| Python 3 | 运行门禁脚本 |
| matplotlib | 生成门禁图 |

可选工具：

| 工具 | 用途 |
| --- | --- |
| gcc / clang / cc | host 编译 C 控制器和测试文件 |
| MSVC cl.exe | Windows host 编译 |

如果没有 C 编译器，脚本仍会生成报告，但 `toolchain` 会是 `BLOCKED`，`build` 和 `unit_tests` 会是 `SKIPPED`。

## 运行命令

在仓库根目录运行：

```powershell
python scripts\run_host_build_tests.py
```

当前本机输出：

```text
已生成第 11 章 Host 编译测试门禁报告。
summary,pass=1,blocked=1,skipped=2,fail=0
toolchain,none,未找到 C 编译器
```

## 生成文件

| 文件 | 内容 |
| --- | --- |
| `reports/11-host-build-summary.csv` | 门禁状态 CSV |
| `reports/11-host-build-test-report.md` | Markdown 测试报告 |
| `waveforms/11-host-build-gate.png` | 门禁状态图 |
| `artifacts/host-build/chapter11/` | 编译临时目录，已被 `.gitignore` 忽略 |

## 当前结果

| Gate | Status | 说明 |
| --- | --- | --- |
| `toolchain` | BLOCKED | PATH 和常见安装目录中没有找到 gcc、clang 或 cl |
| `build` | SKIPPED | 缺少 C 编译器，未执行编译 |
| `unit_tests` | SKIPPED | 缺少可执行文件，未运行 host 单元测试 |
| `report` | PASS | 已生成 CSV、PNG 和 Markdown 报告 |

## 有编译器时的预期

如果系统里已经有 `gcc` 或 `clang`，脚本会尝试执行类似命令：

```powershell
gcc -std=c99 -Wall -Wextra -Werror -I src src\digital_power_control.c tests\test_digital_power_control_host.c -o artifacts\host-build\chapter11\digital_power_control_host_tests.exe
```

如果系统里有 MSVC `cl.exe`，脚本会使用 `/W4 /WX`。

编译成功后，脚本会运行生成的测试程序。测试程序会输出逐项 `PASS` / `FAIL`，最后输出：

```text
SUMMARY,PASS,failures=0
```

## 常见问题

### 1. 为什么当前结果是 BLOCKED

因为当前机器没有检测到 C 编译器。这个状态来自脚本检测结果，不是人工猜测。

### 2. BLOCKED 是不是 C 代码写错了

`BLOCKED` 表示工具链不存在或不可见，编译命令还没有执行。源码是否能编译，需要安装或配置 C 编译器后重新运行脚本。

### 3. 为什么要把 warning 当成错误

host 编译阶段越早暴露类型、初始化、头文件和接口问题，越不容易把问题带到 MCU 工程里。脚本对 gcc/clang 使用 `-Werror`，对 MSVC 使用 `/WX`。

### 4. 为什么不直接进入定点化

定点化依赖一个可编译、可测试的 float baseline。先让 host 编译和单元测试门禁跑起来，后面定点化才有对照基准。

### 5. 编译临时文件为什么不提交

`artifacts/host-build/chapter11/` 是本机生成目录，已经由 `.gitignore` 忽略。公开仓库只提交源码、脚本、报告和可复现图表。
