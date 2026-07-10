# 第 15 章复现说明：Q20 duty 到中心对齐 PWM 比较值

## 目标

复现 Q20 duty 的限幅、整数比较值舍入、中心对齐定时器参数、预装载更新和立即关断语义，并生成真实 C 回放数据、图表和 PASS/FAIL 报告。

## 环境

- Python 3
- matplotlib
- Zig、GCC、Clang 或 MSVC 中任一 C 编译器

当前验证环境为 Windows 11、Python 3、Zig 0.16.0。

## 最短命令

```powershell
python scripts\run_pwm_mapping_tests.py
```

预期摘要：

```text
summary,pass=15,fail=0,rows=640
toolchain,zig,zig 0.16.0
pwm,period_counts=425,arr=425,deadtime_counts=17,max_duty_error=0.00277824
```

## 分步执行

### 1. 生成回放输入和定时器参数

```powershell
python scripts\run_pwm_mapping_tests.py --prepare-only
```

生成：

- `artifacts/host-build/chapter15/15-pwm-mapping-input.csv`
- `waveforms/15-pwm-timer-config.csv`

### 2. 编译并运行 C 单元测试

```powershell
New-Item -ItemType Directory -Force artifacts\host-build\chapter15 | Out-Null

zig cc -std=c99 -Wall -Wextra -Werror `
  -I src `
  src\digital_power_pwm_map.c `
  tests\test_digital_power_pwm_map.c `
  -o artifacts\host-build\chapter15\digital_power_pwm_map_tests.exe

.\artifacts\host-build\chapter15\digital_power_pwm_map_tests.exe
```

预期：

```text
PASS,center_aligned_170mhz_200khz_contract
PASS,half_duty_waits_for_update_event
PASS,half_duty_applies_at_update_event
PASS,duty_above_limit_is_clamped
PASS,disable_is_immediate
SUMMARY,PASS,failures=0
```

### 3. 编译并运行 CSV 回放程序

```powershell
zig cc -std=c99 -Wall -Wextra -Werror `
  -I src `
  src\digital_power_pwm_map.c `
  tests\replay_digital_power_pwm_map.c `
  -o artifacts\host-build\chapter15\digital_power_pwm_map_replay.exe

.\artifacts\host-build\chapter15\digital_power_pwm_map_replay.exe `
  .\artifacts\host-build\chapter15\15-pwm-mapping-input.csv `
  .\artifacts\host-build\chapter15\15-pwm-mapping-output.csv
```

预期：

```text
SUMMARY,OK,rows=640
```

`OK` 表示回放程序完整处理输入；最终 PASS/FAIL 由 C 单元测试和 Python 批量指标共同决定。

## 参数与判据

| 配置 | ARR | duty 步距 | 半计数误差上限 | 死区计数 |
| --- | ---: | ---: | ---: | ---: |
| 72 MHz / 200 kHz | 180 | 0.00555556 | 0.00277778 | 7 |
| 100 MHz / 200 kHz | 250 | 0.00400000 | 0.00200000 | 10 |
| 170 MHz / 200 kHz | 425 | 0.00235294 | 0.00117647 | 17 |

误差判据在半个定时器计数基础上增加一个 Q20 LSB，用于覆盖输入 duty 的 Q20 量化。

## 当前结果

| 场景 | 当前结果 |
| --- | ---: |
| 72 MHz 最大 duty 误差 | 0.00277824 |
| 100 MHz 最大 duty 误差 | 0.00200031 |
| 170 MHz 最大 duty 误差 | 0.00117691 |
| 负 duty 钳位 | PASS |
| 大于 65% duty 钳位 | PASS |
| 最大比较值 | 276 counts |
| 预装载等待更新事件 | PASS |
| 保护立即关断 | PASS |
| 整数运算溢出 | 0 |

## 生成文件

| 文件 | 内容 |
| --- | --- |
| `waveforms/15-pwm-timer-config.csv` | 三种定时器配置和分辨率 |
| `waveforms/15-pwm-mapping-summary.csv` | PASS/FAIL 指标 |
| `waveforms/15-pwm-mapping-samples.csv` | 640 行真实 C 输出 |
| `waveforms/15-pwm-resolution.png` | duty 阶梯和取整误差 |
| `waveforms/15-pwm-shadow-update.png` | 预装载更新和立即关断序列 |
| `reports/15-pwm-mapping-report.md` | 编译、测试和指标报告 |

## 常见失败

### PWM 频率与目标值不一致

先确认计数模式。中心对齐模式使用 `fPWM = fTIM / (2 × ARR)`；不要直接套用边沿对齐的 `ARR + 1` 关系。

### 50% duty 得到 212 而不是 213

检查是否采用向下截断。当前映射在除法前增加 `2^19`，对正 Q20 duty 执行四舍五入。

### 65% 限幅后比较值仍超过 276

检查钳位是否在 duty 到 compare 换算之前完成，并确认 `duty_max` 是 Q20 值 `681574`。

### 比较值一写入就改变 active 值

检查 Queue 和 ApplyUpdateEvent 是否被合并。Queue 只更新 pending；active 只能由更新事件接收。

### 关断命令要等到更新事件才生效

检查 `pwm_enable=false` 路径。保护关断应立即清除 active enable，比较值归零仍可等待更新事件。

### 真实 MCU 的死区不等于 100 ns

本章的 17 counts 是线性时间计数。若目标 MCU 的死区寄存器采用分段编码，应按芯片参考手册把目标时间转换为寄存器编码，并用示波器测量门极间隔。
