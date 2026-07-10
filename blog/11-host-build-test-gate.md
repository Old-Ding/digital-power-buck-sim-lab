# 【数字电源/MATLAB+PLECS】如何进行 Buck 数字电源仿真（十一）如何先在电脑上验证 C 控制器能编译、能跑基础测试

第十章已经把 Buck 数字电源控制器从仿真脚本整理成 C 风格函数。到这一步，很多人会下意识想直接移到 MCU 工程里，然后开始配 ADC、PWM、中断和寄存器。

这里先不要急着上板。

如果 C 控制器本身就有头文件问题、参数初始化问题、状态机问题，直接上板以后看到的现象通常只会是“PWM 没出来”“一启动就进故障”“输出不对”。这时候问题可能在控制算法、采样换算、PWM 配置、中断周期、硬件接线中的任何一层，很难定位。

本章先做一件更小的事：**把 C 控制器当成普通 C 函数，先放在电脑上编译并运行基础测试。**

这里的几个词先说清楚：

| 词 | 在本章里的意思 |
| --- | --- |
| 电脑端 / Host | 不上 MCU，只在 Windows 电脑上编译运行 |
| 编译 | 检查 `digital_power_control.c` 能不能被真实 C 编译器编译 |
| 单元测试 | 写一个小测试程序，直接调用控制器函数，检查软启动、OCP 锁存、PWM 关断等基础行为 |
| 检查 / 门禁 | 进入定点化、ADC/PWM 映射、上板之前的一道检查 |

读完本章，目标很简单：在仓库根目录运行下面这一条命令：

```powershell
python scripts\run_host_build_tests.py
```

然后看到：

```text
summary,pass=4,blocked=0,skipped=0,fail=0
SUMMARY,PASS,failures=0
```

这说明第十章的 C 控制器至少已经通过电脑端编译和基础行为测试。它还不等于 MCU 工程完成，也不等于硬件可以直接上电。

配套 GitHub 仓库：[digital-power-buck-sim-lab](https://github.com/Old-Ding/digital-power-buck-sim-lab)

第十章整理出来的控制器接口如下：

```c
void DpControl_DefaultConfig(DpControlConfig *cfg);
void DpControl_Init(DpControlContext *ctx, const DpControlConfig *cfg);
DpControlOutput DpControl_Step(DpControlContext *ctx,
                               const DpControlConfig *cfg,
                               const DpControlInput *in);
```

本章把这个 C 控制器放进一个电脑端测试工程里，让脚本自动完成三件事：

```text
找 C 编译器 -> 编译控制器和测试文件 -> 运行单元测试并生成报告
```

## 先看本章要跑通的结果

本章先验证三件事：

| 检查点 | 通过标准 |
| --- | --- |
| 找到 C 编译器 | `toolchain` 为 PASS |
| 编译控制器和测试入口 | `build` 为 PASS |
| 运行电脑端单元测试 | 输出 `SUMMARY,PASS,failures=0` |

读这章时先抓住两个文件：`tests/test_digital_power_control_host.c` 是测试入口，`scripts/run_host_build_tests.py` 是一键检查脚本。完整配套文件放在文末。

这一步能提前发现的问题如下：

| 上板后可能看到的现象 | 电脑端先检查什么 |
| --- | --- |
| MCU 工程里 C 文件编不过 | 先用 `zig cc` 编译 `digital_power_control.c` |
| 默认参数散落、不知道初值对不对 | 测 `DpControl_DefaultConfig()` |
| 初始化后状态不确定 | 测 `DpControl_Init()` |
| 过流后 PWM 没有关断 | 测 OCP 锁存和 `pwm_enable` 输出 |
| 清故障逻辑混乱 | 测故障存在和故障消失两种路径 |

## 第一步：写一个最小电脑端测试入口

先看测试入口文件：

```text
tests/test_digital_power_control_host.c
```

它不接 ADC，不接 PWM，也不接 MCU 寄存器。电脑端测试只做一件事：在电脑上直接调用控制器 C 函数，验证接口和状态行为。

测试里先准备一个名义输入：

```c
static DpControlInput nominal_input(void)
{
    DpControlInput in;
    in.enable = true;
    in.clear_fault = false;
    in.vin_v = 24.0f;
    in.vout_adc_v = 12.0f;
    in.iout_a = 5.0f;
    in.temperature_c = 45.0f;
    return in;
}
```

这个输入相当于正常工作点：24V 输入、12V 输出、5A 负载、无清故障请求、温度正常。

然后测试默认参数：

```c
static void test_default_config(void)
{
    DpControlConfig cfg;
    DpControl_DefaultConfig(&cfg);

    expect_close("default_ts_ctrl", cfg.ts_ctrl_s, 5.0e-6f, 1.0e-9f);
    expect_close("default_vref", cfg.vref_final_v, 12.0f, 1.0e-6f);
    expect_close("default_duty_max", cfg.duty_max, 0.65f, 1.0e-6f);
    expect_close("default_ocp", cfg.ocp_threshold_a, 6.5f, 1.0e-6f);
}
```

这一步检查的是第十章 `DefaultConfig()` 有没有把关键参数集中配置好。

## 第二步：测试控制器的最小行为

本章不把第十章的所有动态场景都搬进 C 单元测试。第十章已经用 Python 场景测试覆盖了稳态、软启动、负载突变、OCP、UVLO。

第十一章先覆盖四类最小电脑端行为：

| 测试 | 检查点 |
| --- | --- |
| 默认参数 | `ts_ctrl_s`、`vref_final_v`、`duty_max`、`ocp_threshold_a` |
| 初始化 | 初始状态、故障码、滤波初值、积分器 |
| 软启动首周期 | 0V 启动输入下，状态进入 `SOFT_START`、PWM 允许、参考值爬坡、duty 为小正值 |
| OCP 锁存和清故障路径 | OCP 进入故障、PWM 关断、故障存在时不能清除、故障消失后进入软启动 |

例如 OCP 测试的核心逻辑是：

```c
ctx.state = DP_STATE_RUN;
ctx.vref_cmd_v = cfg.vref_final_v;
ctx.integrator = 0.0f;

in.iout_a = 7.2f;
out = DpControl_Step(&ctx, &cfg, &in);

expect_true("ocp_enters_fault", out.state == DP_STATE_FAULT);
expect_true("ocp_latched", out.latched_fault == DP_FAULT_OCP);
expect_true("ocp_pwm_disabled", !out.pwm_enable);
expect_close("ocp_duty_zero", out.duty_cmd, 0.0f, 1.0e-6f);
```

这里验证的是状态机和 PWM 统一出口。过流以后，控制器应该进入 `FAULT`，锁存 `DP_FAULT_OCP`，并把 PWM 输出关掉。

故障还存在时，再发 `clear_fault`，锁存不能解除：

```c
in.clear_fault = true;
out = DpControl_Step(&ctx, &cfg, &in);
expect_true("ocp_clear_while_fault_stays_latched", out.latched_fault == DP_FAULT_OCP);
```

故障消失后再清除，才进入软启动路径：

```c
in.iout_a = 5.0f;
out = DpControl_Step(&ctx, &cfg, &in);
expect_true("ocp_clear_after_fault_removed", out.latched_fault == DP_FAULT_NONE);
expect_true("ocp_clear_restarts_soft_start", out.state == DP_STATE_SOFT_START);
```

这就是电脑端单元测试的价值：不用上板，也能先检查控制器函数的状态行为。

## 第三步：用脚本生成编译命令

手动敲编译命令很容易漏参数，所以本章用脚本统一处理：

```text
scripts/run_host_build_tests.py
```

脚本按下面顺序寻找 C 编译器：

| 优先级 | 工具链 |
| --- | --- |
| 1 | 环境变量 `CC` |
| 2 | PATH 里的 `zig` |
| 3 | `gcc` |
| 4 | `clang` |
| 5 | `cc` |
| 6 | `cl` |
| 7 | WinGet 安装目录里的 `zig.exe` |
| 8 | Visual Studio 2022 常见安装目录里的 `cl.exe` |

找到 Zig 时，脚本会使用 `zig cc` 调用 C 编译前端：

```powershell
zig cc -std=c99 -Wall -Wextra -Werror -I src src\digital_power_control.c tests\test_digital_power_control_host.c -o artifacts\host-build\chapter11\digital_power_control_host_tests.exe
```

找到 `gcc`、`clang` 或 `cc` 时，脚本生成的编译命令类似：

```powershell
gcc -std=c99 -Wall -Wextra -Werror -I src src\digital_power_control.c tests\test_digital_power_control_host.c -o artifacts\host-build\chapter11\digital_power_control_host_tests.exe
```

找到 MSVC `cl.exe` 时，脚本会使用：

```text
/W4 /WX
```

这里把 warning 当成 error。数字电源控制代码后面要迁移到 MCU，类型、初始化、头文件和接口 warning 都应该在电脑端阶段暴露。

## 第四步：运行一键检查脚本

在仓库根目录运行：

```powershell
python scripts\run_host_build_tests.py
```

当前报告生成环境的输出摘要是：

```text
已生成第 11 章电脑端编译测试检查报告。
summary,pass=4,blocked=0,skipped=0,fail=0
toolchain,zig,Zig 0.16.0 detected
```

完整编译器路径和实际编译命令记录在 `reports/11-host-build-test-report.md`。

脚本生成的检查结果图如下：

![第 11 章电脑端编译测试检查结果](../waveforms/11-host-build-gate.png)

图里的四个 gate 要分开读：

| Gate | 当前状态 | 含义 |
| --- | --- | --- |
| `toolchain` | PASS | 本机检测到 Zig 0.16.0，可作为电脑端 C 编译器 |
| `build` | PASS | 已编译 `src/digital_power_control.c` 和 `tests/test_digital_power_control_host.c` |
| `unit_tests` | PASS | 生成的电脑端测试程序运行通过 |
| `report` | PASS | CSV、PNG、Markdown 报告生成成功 |

这组结果说明第十章的 C 风格控制器已经通过电脑端编译和最小单元测试检查。这里说的是电脑端证据，不是目标 MCU 工具链或硬件闭环证据。

本次测试程序的关键输出如下：

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

## 第五步：看报告文件

脚本会生成三类证据：

```text
reports/11-host-build-summary.csv
reports/11-host-build-test-report.md
waveforms/11-host-build-gate.png
```

CSV 汇总内容如下：

| Gate | Status | Detail |
| --- | --- | --- |
| `toolchain` | PASS | 检测到 Zig 0.16.0 |
| `build` | PASS | 生成电脑端测试可执行文件 |
| `unit_tests` | PASS | 电脑端单元测试通过 |
| `report` | PASS | 已生成 CSV、PNG 和 Markdown 报告 |

读这张表时，优先看前三行：

```text
toolchain -> build -> unit_tests
```

`report PASS` 只说明报告文件生成成功；本章能判断 C 编译和测试通过，是因为 `build` 和 `unit_tests` 也同时进入 PASS。

## 如果没有编译器，怎么处理

如果另一台电脑没有 `zig`、`gcc`、`clang` 或 `cl`，还是运行同一个命令：

```powershell
python scripts\run_host_build_tests.py
```

这时流程会停在工具链检查：

```text
toolchain BLOCKED
-> build SKIPPED
-> unit_tests SKIPPED
-> report PASS
```

Windows 上可以用 WinGet 安装 Zig：

```powershell
winget install --id zig.zig -e --scope user --accept-source-agreements --accept-package-agreements
```

安装后重新运行检查脚本。如果 C 代码有语法问题、头文件路径问题、warning 或链接问题，`build` 会变成 `FAIL`。

如果编译通过，但控制器行为不符合测试预期，例如 OCP 没有锁存、故障未消失时被清除、PWM 没有关断，`unit_tests` 会变成 `FAIL`。

这道检查的目的就是把这些问题拦在电脑端阶段，而不是拖到 MCU 上电阶段。

## 不要误读本章结果

| 观察到的现象 | 教学结论 | 不要误读成 |
| --- | --- | --- |
| `toolchain PASS` | 电脑端已经找到 Zig 0.16.0 | 目标 MCU 工具链已经验证 |
| `build PASS` | C 控制器和电脑端测试入口可以在电脑端编译 | MCU 工程已经编译通过 |
| `unit_tests PASS` | 默认参数、初始化、软启动首周期和 OCP 锁存路径通过 | 第十章所有动态场景都已用 C 单元测试覆盖 |
| `report PASS` | CSV、PNG、Markdown 证据链生成成功 | 固件已经可上板 |

本章完成的是第二季的入口工程链路：用脚本把工具链、编译、单元测试和报告串起来。

## 本章配套文件

仓库入口：[https://github.com/Old-Ding/digital-power-buck-sim-lab](https://github.com/Old-Ding/digital-power-buck-sim-lab)

| 类型 | 文件 | 作用 |
| --- | --- | --- |
| 教程正文 | `blog/11-host-build-test-gate.md` | 本章文章 |
| 复现说明 | `docs/11-host-build-test-gate-reproduce.md` | 运行步骤和结果解释 |
| C 测试文件 | `tests/test_digital_power_control_host.c` | 电脑端单元测试 |
| 构建测试脚本 | `scripts/run_host_build_tests.py` | 检测工具链、编译、运行测试、生成报告 |
| CSV 汇总 | `reports/11-host-build-summary.csv` | 检查状态 |
| 测试报告 | `reports/11-host-build-test-report.md` | Markdown 报告 |
| 检查结果图 | `waveforms/11-host-build-gate.png` | 正文图表 |

运行方式：

```powershell
python scripts\run_host_build_tests.py
```

## 下一步

第二季后续应该按这个顺序推进：

| 顺序 | 内容 |
| --- | --- |
| 1 | 扩展 `unit_tests`，把第十章场景数据作为 oracle |
| 2 | 做 float baseline 和定点化对照 |
| 3 | 设计 ADC/PWM 标定、限幅和单位换算 |
| 4 | 拆分 ISR 实时层和后台状态机 |
| 5 | 再进入 MCU 工程、HIL 和实机闭环 |

对数字电源固件来说，先让电脑端检查稳定，再谈定点化和上板，风险会低很多。

## 技术交流

如果你在复现代码结构、配置 C 编译器或判断测试报告时遇到问题，可以加入技术交流群交流。

仓库中的源码、脚本、数据和图表可以直接使用；交流群主要用于复现答疑和后续技术讨论。

| 渠道 | 信息 |
| --- | --- |
| QQ 群 | 嵌入式交流群 |
| 加群链接 | [https://qm.qq.com/q/rygrSD2Ddu](https://qm.qq.com/q/rygrSD2Ddu) |
| 微信交流 | 微信入口会不定期更新，可在 QQ 群内获取 |

提问时建议附上 `reports/11-host-build-test-report.md`、终端输出、你安装的编译器名称和 `PATH` 配置截图。
