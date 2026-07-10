# 【数字电源/MATLAB+PLECS】如何进行 Buck 数字电源仿真（十一）第二季先建立 C 编译和单元测试门禁

前面第十章已经把 Buck 数字电源控制器整理成了 C 风格接口：

```text
DpControl_DefaultConfig()
DpControl_Init()
DpControl_Step()
```

这一步很关键，但它还只是“像固件”。进入第二季以后，判断标准要变严格：

```text
代码能不能被真实 C 编译器编译？
有没有 host 单元测试？
测试输出能不能生成报告？
报告能不能作为 GitHub 和文章里的证据？
```

第十一章先做这件事。

配套 GitHub 仓库：[digital-power-buck-sim-lab](https://github.com/Old-Ding/digital-power-buck-sim-lab)

本章新增 host 侧测试文件、构建测试脚本、CSV 汇总、PNG 门禁图和 Markdown 报告。当前这台机器没有检测到 C 编译器，所以本章的真实结果是 `toolchain BLOCKED`，`build` 和 `unit_tests` 被跳过。

这个结果并不尴尬，反而是第二季应该有的工程边界：没有编译器，就不能声称 C 代码已经编译通过。

## 第二季为什么先做门禁

很多数字电源教程会从仿真直接跳到“上板”，中间缺一层软件工程证据。

这层证据至少包括：

| 门禁 | 要回答的问题 |
| --- | --- |
| `toolchain` | 本机或 CI 上有没有真实 C 编译器 |
| `build` | `src/digital_power_control.c` 能不能被编译 |
| `unit_tests` | 控制器关键行为有没有 host 测试 |
| `report` | 构建和测试结果能不能留下可追溯报告 |

如果没有这层门禁，后面讲定点化、ADC 标定、PWM 映射、ISR 分层和 HAL 适配都会悬空。

第十一章的重点不是让 MCU 跑起来，而是先建立一个判断标准：

```text
能编译，才继续谈测试；
测试通过，才继续谈定点化；
定点化有对照，才继续谈 MCU 集成。
```

## 本章新增了什么

本章新增两个核心文件：

| 文件 | 作用 |
| --- | --- |
| `tests/test_digital_power_control_host.c` | host 侧单元测试入口 |
| `scripts/run_host_build_tests.py` | 检测编译器、编译、运行测试、生成报告 |

测试文件覆盖四类最小行为：

| 测试 | 检查点 |
| --- | --- |
| 默认参数 | `ts_ctrl_s`、`vref_final_v`、`duty_max`、`ocp_threshold_a` |
| 初始化 | 初始状态、故障码、滤波初值、积分器 |
| 软启动首周期 | 状态进入 `SOFT_START`、PWM 允许、参考值爬坡、duty 低限幅 |
| OCP 锁存和清故障路径 | OCP 进入故障、PWM 关断、故障存在时不能清除、故障消失后进入软启动 |

这些测试不是完整控制性能验证。完整动态行为已经在第十章用场景测试和 CSV 做过。本章只验证 C 接口最关键的可编译、可调用、可测试路径。

## 脚本怎么判断工具链

运行命令：

```powershell
python scripts\run_host_build_tests.py
```

脚本会按这个顺序找编译器：

| 优先级 | 工具链 |
| --- | --- |
| 1 | 环境变量 `CC` |
| 2 | `gcc` |
| 3 | `clang` |
| 4 | `cc` |
| 5 | `cl` |
| 6 | Visual Studio 2022 常见安装目录里的 `cl.exe` |

如果找到 `gcc` / `clang` / `cc`，脚本会生成类似这样的命令：

```powershell
gcc -std=c99 -Wall -Wextra -Werror -I src src\digital_power_control.c tests\test_digital_power_control_host.c -o artifacts\host-build\chapter11\digital_power_control_host_tests.exe
```

如果找到 MSVC `cl.exe`，脚本会使用 `/W4 /WX` 编译。

这里有一个细节：脚本没有把 warning 当成可以忽略的小问题，而是用 `-Werror` 或 `/WX` 把 warning 提升为构建失败。数字电源控制代码后续要上 MCU，类型、初始化和接口 warning 都应该尽早暴露。

## 当前本机运行结果

当前运行输出如下：

```text
已生成第 11 章 Host 编译测试门禁报告。
summary,pass=1,blocked=1,skipped=2,fail=0
toolchain,none,未找到 C 编译器
```

脚本生成的门禁图如下：

![第 11 章 Host 编译测试门禁](../waveforms/11-host-build-gate.png)

这张图要这样读：

| Gate | 当前状态 | 读法 |
| --- | --- | --- |
| `toolchain` | BLOCKED | 本机没有找到 C 编译器 |
| `build` | SKIPPED | 因为没有编译器，所以没有执行编译 |
| `unit_tests` | SKIPPED | 因为没有可执行文件，所以没有运行测试 |
| `report` | PASS | CSV、PNG、Markdown 报告生成成功 |

这组状态说明工程门禁在第一层就拦住了流程：当前环境还不具备 C 编译条件，所以源码是否能通过编译还没有进入判断阶段。

## 报告怎么看

脚本会生成：

```text
reports/11-host-build-summary.csv
reports/11-host-build-test-report.md
waveforms/11-host-build-gate.png
```

报告里的核心表格是：

| Gate | Status | Detail |
| --- | --- | --- |
| `toolchain` | BLOCKED | PATH 和常见安装目录中没有找到 gcc、clang 或 cl |
| `build` | SKIPPED | 缺少 C 编译器，未执行编译 |
| `unit_tests` | SKIPPED | 缺少可执行文件，未运行 host 单元测试 |
| `report` | PASS | 已生成 CSV、PNG 和 Markdown 报告 |

读这组结果时，重点不是 `report PASS`，而是 `toolchain BLOCKED`。

`report PASS` 只说明证据链文件生成成功；它不代表 C 编译通过。

## 有编译器以后会发生什么

当本机或 CI 配好 `gcc`、`clang` 或 `cl` 后，同一个命令会继续往下走：

```text
toolchain PASS
-> build PASS 或 FAIL
-> unit_tests PASS 或 FAIL
-> report PASS
```

如果 C 代码有语法问题、头文件路径问题、warning、链接问题，`build` 会变成 `FAIL`。

如果编译成功但行为不符合预期，例如 OCP 不锁存、clear fault 路径错误，`unit_tests` 会变成 `FAIL`。

这就是门禁的意义：不要把问题拖到 MCU 上电时才发现。

## 不要误读本章结果

| 观察到的现象 | 教学结论 | 不要误读成 |
| --- | --- | --- |
| `toolchain BLOCKED` | 当前机器缺 C 编译器 | C 源码本身已经编译失败 |
| `build SKIPPED` | 没有执行编译命令 | C 编译已经通过 |
| `unit_tests SKIPPED` | 没有可执行文件可运行 | 单元测试已经通过 |
| `report PASS` | 报告文件生成成功 | 固件已经可上板 |

第十一章完成的是第二季的入口门禁。它把主观判断变成脚本输出：工具链是否存在、编译是否执行、测试是否运行，都要留下可复现证据。

## 本章配套文件

仓库入口：[https://github.com/Old-Ding/digital-power-buck-sim-lab](https://github.com/Old-Ding/digital-power-buck-sim-lab)

| 类型 | 文件 | 作用 |
| --- | --- | --- |
| 教程正文 | `blog/11-host-build-test-gate.md` | 本章文章 |
| 复现说明 | `docs/11-host-build-test-gate-reproduce.md` | 运行步骤和结果解释 |
| C 测试文件 | `tests/test_digital_power_control_host.c` | host 侧单元测试 |
| 构建测试脚本 | `scripts/run_host_build_tests.py` | 检测工具链、编译、运行测试、生成报告 |
| CSV 汇总 | `reports/11-host-build-summary.csv` | 门禁状态 |
| 测试报告 | `reports/11-host-build-test-report.md` | Markdown 报告 |
| 门禁图 | `waveforms/11-host-build-gate.png` | 正文图表 |

运行方式：

```powershell
python scripts\run_host_build_tests.py
```

## 下一步

第十一章把第二季的门禁建起来了。

下一步有两种路线：

| 条件 | 下一步 |
| --- | --- |
| 本机先安装 C 编译器 | 重新运行第十一章脚本，让 `build` 和 `unit_tests` 进入 PASS/FAIL |
| 先继续设计测试体系 | 第十二章扩展 host 单元测试，把第十章的场景数据作为 oracle |

对数字电源固件来说，最优路线是先让 `toolchain -> build -> unit_tests` 全部能跑，再进入定点化和 MCU 适配。

## 技术交流

如果你在复现代码结构、配置 C 编译器或判断测试报告时遇到问题，可以加入技术交流群交流。

仓库中的源码、脚本、数据和图表可以直接使用；交流群主要用于复现答疑和后续技术讨论。

| 渠道 | 信息 |
| --- | --- |
| QQ 群 | 嵌入式交流群 |
| 加群链接 | [https://qm.qq.com/q/rygrSD2Ddu](https://qm.qq.com/q/rygrSD2Ddu) |
| 微信交流 | 微信入口会不定期更新，可在 QQ 群内获取 |

提问时建议附上 `reports/11-host-build-test-report.md`、终端输出、你安装的编译器名称和 `PATH` 配置截图。
