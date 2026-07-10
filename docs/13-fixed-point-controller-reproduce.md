# 第 13 章复现说明：浮点 C 与 Q20 定点 C 对照

本说明用于复现第 13 章的定点格式选择、定点单元测试、五场景双实现回放、误差比较、溢出检查、CSV、图表和 Markdown 报告。

## 复现目标

使用第 12 章已经验证的浮点 C 控制器作为基准，检查 Q20 定点控制器：

- 连续量误差是否低于公开容差
- 状态、故障、PWM 和逻辑标志是否逐周期一致
- 正常回放是否没有输入转换或定点算术溢出
- 主动构造正负越界时是否会饱和并记录溢出
- 配置、输入、状态和输出 raw 是否保留足够 32 位范围余量

本流程不覆盖 ADC 码值换算、PWM 寄存器映射、目标 MCU 编译、执行时间、HIL 或硬件闭环。

## 定点约定

| 项目 | 数值 |
| --- | ---: |
| 存储类型 | 有符号 `int32_t` |
| 小数位 | 20 |
| 缩放因子 | `2^20 = 1,048,576` |
| 最小分辨率 | `9.536743e-7` |
| 工程值范围 | 约 `-2048` 至 `+2048` |
| 乘法中间量 | `int64_t` |
| 结果策略 | 对称四舍五入、32 位饱和、溢出计数 |

## 文件职责

| 文件 | 职责 |
| --- | --- |
| `src/digital_power_control.c` | 第 12 章浮点 C 行为基准 |
| `src/digital_power_control_fixed.c` | Q20 定点控制器和统一定点算术层 |
| `src/digital_power_control_fixed.h` | 定点配置、输入、状态和输出接口 |
| `tests/test_digital_power_control_fixed.c` | 格式、软启动和正负溢出边界测试 |
| `tests/replay_digital_power_control_fixed.c` | 同时执行浮点 C 和定点 C 的 CSV 回放入口 |
| `scripts/run_fixed_point_parity.py` | 生成格式数据、编译运行、比较、绘图和写报告 |

## 环境要求

必须具备：

| 工具 | 用途 |
| --- | --- |
| Python 3 | 运行场景生成和自动化比较 |
| matplotlib | 生成两张结果图 |
| Zig、GCC、Clang 或 MSVC | 编译浮点、定点控制器和测试入口 |

当前验证环境为 Windows 11、Python 3 和 Zig 0.16.0。

## 最短复现命令

在仓库根目录运行：

```powershell
python scripts\run_fixed_point_parity.py
```

当前预期输出：

```text
已生成第 13 章浮点 C 与 Q20 定点 C 对照数据、图表和报告。
summary,pass=74,fail=0,scenarios=5,rows=80400
toolchain,zig,zig 0.16.0
fixed_format,frac_bits=20,scale=1048576,max_raw_use_pct=4.88281
max_error,duty_cmd=7.06908e-05,vref_cmd_v=0.000478795,integrator=7.06213e-05
```

脚本退出码为 0 表示定点单元测试和全部对照指标通过；存在构建、测试或比较失败时返回非 0。

## 分步复现

### 1. 生成格式表和固定回放输入

```powershell
python scripts\run_fixed_point_parity.py --prepare-only
```

预期输出：

```text
prepared,rows=80400,input=...\artifacts\host-build\chapter13\13-controller-replay-input.csv
fixed_format,frac_bits=20,scale=1048576
```

该命令同时更新：

- `waveforms/13-fixed-point-format.csv`
- `waveforms/13-fixed-point-constants.csv`

### 2. 手动编译并运行定点边界测试

以 Zig 为例：

```powershell
New-Item -ItemType Directory -Force artifacts\host-build\chapter13 | Out-Null

zig cc -std=c99 -Wall -Wextra -Werror `
  -I src `
  src\digital_power_control_fixed.c `
  tests\test_digital_power_control_fixed.c `
  -o artifacts\host-build\chapter13\digital_power_control_fixed_tests.exe

.\artifacts\host-build\chapter13\digital_power_control_fixed_tests.exe
```

预期输出：

```text
PASS,q20_scale_and_soft_start_constant
PASS,soft_start_first_step_without_overflow
PASS,positive_overflow_saturates_and_counts
PASS,negative_overflow_saturates_and_counts
SUMMARY,PASS,failures=0
```

### 3. 手动编译双实现回放程序

```powershell
zig cc -std=c99 -Wall -Wextra -Werror `
  -I src `
  src\digital_power_control.c `
  src\digital_power_control_fixed.c `
  tests\replay_digital_power_control_fixed.c `
  -lm `
  -o artifacts\host-build\chapter13\digital_power_control_fixed_replay.exe
```

### 4. 直接运行 80,400 周期回放

```powershell
.\artifacts\host-build\chapter13\digital_power_control_fixed_replay.exe `
  .\artifacts\host-build\chapter13\13-controller-replay-input.csv `
  .\artifacts\host-build\chapter13\13-fixed-point-output.csv
```

预期输出：

```text
SUMMARY,OK,rows=80400,input_overflow=0,fixed_overflow=0
```

`OK` 表示 C 程序完成全部输入，不代表误差已经通过。PASS/FAIL 由 Python 脚本比较浮点与定点输出后产生。

### 5. 运行完整对照

```powershell
python scripts\run_fixed_point_parity.py
```

完整流程会重新执行格式生成、两个 C 构建、边界测试、双实现回放、逐周期比较、绘图和报告生成。

## 对照场景

| 场景 | 控制周期数 | 重点 |
| --- | ---: | --- |
| `steady_12v` | 15,000 | 稳态积分器和 duty 量化 |
| `soft_start_40ms` | 13,000 | 小增量累计和 RUN 切换时刻 |
| `load_step_50_100_50` | 18,400 | 动态积分器和 duty 误差 |
| `ocp_latch_clear` | 17,600 | OCP 锁存、清除和软启动恢复 |
| `uvlo_blocks_pwm` | 16,400 | UVLO 锁存、PWM 关断和恢复 |

## 比较条件

| 字段 | 容差或规则 |
| --- | ---: |
| `vout_meas_v` | 最大绝对误差 `1e-6` |
| `vref_cmd_v`、`error_v` | 最大绝对误差 `0.0011 V` |
| `p_term` | 最大绝对误差 `6e-5` |
| `integrator` | 最大绝对误差 `1e-4` |
| `duty_raw`、`duty_cmd` | 最大绝对误差 `1.5e-4` |
| 状态、故障、PWM、饱和和积分允许标志 | 逐周期完全一致 |
| 输入转换和定点算术溢出 | 正常回放必须为 0 |
| 最大 raw 正量程占用 | 不超过 10% |

## 生成文件

| 文件 | 内容 | 是否提交仓库 |
| --- | --- | --- |
| `waveforms/13-fixed-point-format.csv` | Q16/Q20/Q24 精度和范围取舍 | 是 |
| `waveforms/13-fixed-point-constants.csv` | Q20 常量 raw、还原值和量化误差 | 是 |
| `waveforms/13-fixed-point-summary.csv` | 74 项指标、容差和 PASS/FAIL | 是 |
| `waveforms/13-fixed-point-samples.csv` | 每 0.1 ms 抽样的浮点/定点对照 | 是 |
| `waveforms/13-fixed-point-overlay.png` | 四个动态场景叠加图 | 是 |
| `waveforms/13-fixed-point-error-format.png` | 误差与格式取舍图 | 是 |
| `reports/13-fixed-point-parity-report.md` | 格式、常量、测试和场景报告 | 是 |
| `artifacts/host-build/chapter13/13-controller-replay-input.csv` | 完整回放输入 | 否，可重新生成 |
| `artifacts/host-build/chapter13/13-fixed-point-output.csv` | 完整双实现 C 输出 | 否，可重新生成 |
| `artifacts/host-build/chapter13/*.exe` | 本机测试程序 | 否，可重新编译 |

## 当前预期结果

| 指标 | 结果 |
| --- | ---: |
| 定点单元测试 | 4/4 PASS |
| 对照场景 | 5 |
| 对照周期 | 80,400 |
| 汇总 | PASS 74 / FAIL 0 |
| 最大 duty 误差 | `7.06908e-05` |
| 最大参考值误差 | `0.000478795 V` |
| 最大积分器误差 | `7.06213e-05` |
| 离散行为错位 | 0 |
| 正常回放溢出 | 0 |
| 最大 raw 正量程占用 | `4.88281%` |

## 常见失败解释

### 1. 边界测试出现 FAIL

先检查 `dp_fixed_saturate()` 是否仍是所有定点加减乘除的统一出口，再检查溢出标志和计数是否在每个控制周期正确更新。不要在状态机或回放脚本增加重复饱和判断来掩盖核心算术错误。

### 2. 只有软启动参考值误差超限

检查 `soft_start_step` 是否仍为 1573、每周期是否只累加一次，以及状态切换是在累加前还是累加后判断。改变小数位数后必须重新生成格式表和容差依据。

### 3. 积分器误差持续增大

检查 `ki_step`、定点乘法舍入方式和 anti-windup 的 `allow_integrate` 条件。积分器误差通常会继续传播到 duty，不能只放宽 duty 容差。

### 4. 状态或故障出现 mismatch

离散决策不允许使用误差容差。先定位第一个错位周期，检查量化后的 OCP、OVP、UVLO、OTP 阈值以及状态更新顺序。

### 5. 正常场景出现 arithmetic overflow

查看首次溢出周期的 `error`、`p_term`、`integrator` 和 `duty_raw`。如果工程量合理但 raw 已接近边界，应重新选择小数位或为不同信号设计独立格式，而不是依赖长期饱和运行。

### 6. 最大 raw 占用超过 10%

本章策略要求至少约 10 倍幅值余量。检查是否新增了更高温度、更大输入或异常状态；如果量程需求确实改变，应重新完成格式取舍，而不是只提高检查阈值。

### 7. 为什么没有直接输入 ADC 码值

本章隔离定点控制算法，回放适配层把工程值转换成 Q20 raw。ADC 量化、分压比、采样增益、偏置和校准属于下一章的输入映射验证。
