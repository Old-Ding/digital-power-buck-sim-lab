# 第 12 章复现说明：Python 与 C 控制器逐周期对照

本说明用于复现第 12 章的固定输入回放、C 编译执行、Python/C 逐周期比较、CSV 汇总、图表和 Markdown 报告。

## 复现目标

使用第 10 章 Python 场景模型产生固定逐周期输入，把相同输入送给真实编译后的 `src/digital_power_control.c`，检查：

- 连续量的最大绝对误差是否在容差内
- 控制状态和故障码是否逐周期一致
- PWM 使能是否逐周期一致
- 饱和与积分允许标志是否逐周期一致

本流程不覆盖目标 MCU 编译、定点化、ADC/PWM 外设、ISR 执行时间、HIL 或硬件闭环。

## 文件职责

| 文件 | 职责 |
| --- | --- |
| `scripts/export_controller_c_style_tests.py` | 提供第 10 章 Python 参考控制器、平均功率级和场景输入 |
| `scripts/run_c_python_parity.py` | 生成回放输入、编译运行 C 程序、比较结果并生成公开证据 |
| `src/digital_power_control.c` | 被测 C 控制器实现 |
| `src/digital_power_control.h` | C 控制器接口、配置、状态和输入输出类型 |
| `tests/replay_digital_power_control.c` | 读取 CSV，调用 C 控制器，写出 C 结果 |

`run_c_python_parity.py` 和 `replay_digital_power_control.c` 都是本仓库为第 12 章编写的辅助文件。C 回放程序只执行输入并输出结果；最终 PASS/FAIL 由 Python 脚本根据本章容差判断。

## 环境要求

必须具备：

| 工具 | 用途 |
| --- | --- |
| Python 3 | 运行参考场景和对照脚本 |
| matplotlib | 生成对照图和误差图 |
| Zig、GCC、Clang 或 MSVC | 编译 C 控制器和回放入口 |

当前仓库已在 Windows 11、Python 3 和 Zig 0.16.0 环境验证。

脚本按顺序查找 `CC` 环境变量、Zig、GCC、Clang、`cc` 和 MSVC，并兼容 WinGet Zig 与 Visual Studio 2022 的常见安装位置。

## 最短复现命令

在仓库根目录运行：

```powershell
python scripts\run_c_python_parity.py
```

当前预期输出：

```text
已生成第 12 章 Python 与 C 控制器对照数据、图表和报告。
summary,pass=55,fail=0,scenarios=5,rows=80400
toolchain,zig,zig 0.16.0
max_error,duty_cmd=5.12136e-05,vref_cmd_v=0.0005587
```

脚本退出码为 0 表示所有比较项通过；存在 FAIL 时退出码为 1；未找到 C 编译器时退出码为 2。

## 分步复现

### 1. 准备固定回放输入

```powershell
python scripts\run_c_python_parity.py --prepare-only
```

预期输出：

```text
prepared,rows=80400,input=...\artifacts\host-build\chapter12\12-controller-replay-input.csv
```

该命令只生成输入，不执行 C 编译和对照判断。

### 2. 手动编译 C 回放程序

以下命令以 Zig 为例：

```powershell
New-Item -ItemType Directory -Force artifacts\host-build\chapter12 | Out-Null

zig cc -std=c99 -Wall -Wextra -Werror `
  -I src `
  src\digital_power_control.c `
  tests\replay_digital_power_control.c `
  -o artifacts\host-build\chapter12\digital_power_control_replay.exe
```

如果使用 GCC 或 Clang，把 `zig cc` 替换为 `gcc` 或 `clang`。使用 MSVC 时建议直接运行一键脚本，让脚本生成 `/W4 /WX` 形式的等价命令。

### 3. 直接运行 C 回放程序

```powershell
.\artifacts\host-build\chapter12\digital_power_control_replay.exe `
  .\artifacts\host-build\chapter12\12-controller-replay-input.csv `
  .\artifacts\host-build\chapter12\12-controller-c-output.csv
```

预期输出：

```text
SUMMARY,OK,rows=80400
```

这里的 `OK` 只表示输入已成功解析并完成 80,400 次 C 控制器调用，不表示 Python/C 对照已经通过。

### 4. 运行完整对照

```powershell
python scripts\run_c_python_parity.py
```

完整脚本会重新准备输入、编译 C 程序、运行回放、比较结果并覆盖更新第 12 章公开证据。

## 场景与数据量

| 场景 | 控制周期数 | 主要检查 |
| --- | ---: | --- |
| `steady_12v` | 15,000 | 稳态 duty、积分器和状态 |
| `soft_start_40ms` | 13,000 | 软启动参考值累加和 RUN 切换 |
| `load_step_50_100_50` | 18,400 | 负载变化时 duty 与积分器动态 |
| `ocp_latch_clear` | 17,600 | OCP 锁存、清除条件和重启 |
| `uvlo_blocks_pwm` | 16,400 | UVLO 锁存和 PWM 关断 |

总计 80,400 个 5 us 控制周期。

## 比较条件

| 字段 | 容差或规则 |
| --- | ---: |
| `vout_meas_v` | 最大绝对误差 `1e-6` |
| `vref_cmd_v` | 最大绝对误差 `0.0015 V` |
| `error_v` | 最大绝对误差 `0.0015 V` |
| `p_term` | 最大绝对误差 `7.5e-5` |
| `integrator` | 最大绝对误差 `1e-6` |
| `duty_raw`、`duty_cmd` | 最大绝对误差 `1.5e-4` |
| `state`、`active_fault`、`latched_fault` | 逐周期完全一致 |
| `pwm_enable`、`saturation`、`allow_integrate` | 逐周期完全一致 |

## 生成文件

| 文件 | 内容 | 是否提交仓库 |
| --- | --- | --- |
| `waveforms/12-c-python-parity-summary.csv` | 55 项对照指标、容差和 PASS/FAIL | 是 |
| `waveforms/12-c-python-parity-samples.csv` | 每 0.1 ms 抽样的 Python/C 对照数据 | 是 |
| `waveforms/12-c-python-parity-overlay.png` | 四个动态场景的 Python/C 曲线叠加图 | 是 |
| `waveforms/12-c-python-parity-error.png` | 数值误差除以容差的归一化图 | 是 |
| `reports/12-c-python-parity-report.md` | 编译器、场景、指标和边界报告 | 是 |
| `artifacts/host-build/chapter12/12-controller-replay-input.csv` | 完整 C 回放输入 | 否，可重新生成 |
| `artifacts/host-build/chapter12/12-controller-c-output.csv` | 完整 C 输出 | 否，可重新生成 |
| `artifacts/host-build/chapter12/digital_power_control_replay.exe` | 本机 C 回放可执行文件 | 否，可重新编译 |

公开抽样 CSV 用于快速查看和绘图复核；PASS/FAIL 判断使用内存中的全部 80,400 行，不是只检查抽样数据。

## 当前预期指标

| 指标 | 预期结果 |
| --- | ---: |
| 场景数 | 5 |
| 比较周期数 | 80,400 |
| PASS / FAIL | 55 / 0 |
| 最大 `duty_cmd` 误差 | `5.12136e-05` |
| 最大 `vref_cmd_v` 误差 | `0.0005587 V` |
| 状态、故障、PWM 和逻辑标志错位 | 0 |

不同电脑端 C 编译器的浮点末位结果可能略有差异，但必须保持在仓库定义的容差内。

## 常见失败解释

### 1. 输出 `summary,BLOCKED,未找到 C 编译器`

Python 环境可用，但脚本没有找到 Zig、GCC、Clang 或 MSVC。安装编译器或通过 `CC` 环境变量指定编译器后重试。

### 2. 输出 `summary,FAIL,build_exit_code=...`

C 编译失败。先查看该摘要之前的完整编译器输出；本章启用了严格警告，警告也会导致构建失败。

### 3. C 回放程序返回 `parse error`

回放输入 CSV 的列数或格式已变化，而 `tests/replay_digital_power_control.c` 仍按旧格式解析。应同步检查生成脚本和 C 回放入口，不要手工忽略错误行。

### 4. 报告出现 `C output keys differ`

C 输出缺少或多出了场景/周期，通常表示 C 回放提前退出、重复输出或周期编号被改动。

### 5. 状态、故障或 PWM mismatch 大于 0

离散行为已经发生逐周期错位。先定位第一个错位周期，再检查故障检测、状态更新、清故障和 PWM 统一出口的执行顺序。

### 6. 只有浮点误差超过容差

先判断差异是否持续累积，再检查常量类型、运算顺序、`float`/`double` 转换和积分器更新。不要直接放宽容差；只有确认差异来自合理数值表示且不掩盖行为变化后，才能修改容差依据。

### 7. 为什么 C 输出不反馈给功率级

本章要隔离“Python 控制算法改写成 C 后是否发生变化”。固定相同输入可以排除功率级轨迹分叉的干扰。独立 C 闭环、目标 MCU 时序和真实功率级属于后续验证层级。
