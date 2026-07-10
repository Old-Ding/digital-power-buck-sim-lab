# 第 14 章复现说明：ADC code 到 Q20 输入映射

## 目标

复现四通道 ADC 原始码值到 Q20 `Vin`、`Vout`、`Iout` 和温度的真实 C 映射，并比较标称前端、元件偏差未校准和写入校准系数三种情况。

## 环境

- Python 3
- matplotlib
- Zig、GCC、Clang 或 MSVC 中任一 C 编译器

当前验证环境为 Windows 11、Python 3、Zig 0.16.0。

## 最短命令

```powershell
python scripts\run_adc_mapping_tests.py
```

预期摘要：

```text
summary,pass=22,fail=0,info=4,rows=607
toolchain,zig,zig 0.16.0
calibration,max_uncalibrated_error=0.7286,max_calibrated_ratio=0.0557319
```

## 分步执行

### 1. 只生成输入和前端参数

```powershell
python scripts\run_adc_mapping_tests.py --prepare-only
```

生成：

- `artifacts/host-build/chapter14/14-adc-mapping-input.csv`
- `waveforms/14-adc-front-end-config.csv`

### 2. 编译并运行 C 单元测试

```powershell
New-Item -ItemType Directory -Force artifacts\host-build\chapter14 | Out-Null

zig cc -std=c99 -Wall -Wextra -Werror `
  -I src `
  src\digital_power_adc_map.c `
  tests\test_digital_power_adc_map.c `
  -o artifacts\host-build\chapter14\digital_power_adc_map_tests.exe

.\artifacts\host-build\chapter14\digital_power_adc_map_tests.exe
```

预期：

```text
PASS,nominal_24v_12v_5a_45c
PASS,adc_code_above_full_scale_is_clamped
PASS,sensor_values_respect_physical_limits
SUMMARY,PASS,failures=0
```

### 3. 编译并运行 CSV 回放入口

```powershell
zig cc -std=c99 -Wall -Wextra -Werror `
  -I src `
  src\digital_power_adc_map.c `
  tests\replay_digital_power_adc_map.c `
  -o artifacts\host-build\chapter14\digital_power_adc_map_replay.exe

.\artifacts\host-build\chapter14\digital_power_adc_map_replay.exe `
  .\artifacts\host-build\chapter14\14-adc-mapping-input.csv `
  .\artifacts\host-build\chapter14\14-adc-mapping-output.csv
```

预期：

```text
SUMMARY,OK,rows=607
```

`OK` 只表示回放完成；误差结论由 Python 脚本读取 C 输出后计算。

## 前端参数

| 参数 | 标称 | 偏差场景实际值 |
| --- | ---: | ---: |
| `Vin` 分压比 | 9.2 | 9.292 |
| `Vout` 分压比 | 4.9 | 4.8608 |
| 电流零点 | 0.100 V | 0.112 V |
| 电流增益 | 0.400 V/A | 0.406 V/A |
| 温度零点 | 0.500 V | 0.505 V |
| 温度斜率 | 0.0100 V/°C | 0.0099 V/°C |

偏差场景是脚本定义的可重复测试数据，不是实物测量。

## 误差限制

| 通道 | PASS 上限 |
| --- | ---: |
| `Vin` | 0.008 V |
| `Vout` | 0.0041 V |
| `Iout` | 0.0022 A |
| 温度 | 0.083°C |

标称和校准场景必须通过。未校准场景标记为 `INFO`，同时要求校准后的最大误差不超过未校准误差的 10%。

## 当前结果

| 通道 | 标称最大误差 | 未校准最大误差 | 校准后最大误差 |
| --- | ---: | ---: | ---: |
| `Vin` | 0.003708 V | 0.299843 V | 0.003742 V |
| `Vout` | 0.001951 V | 0.130511 V | 0.001956 V |
| `Iout` | 0.001008 A | 0.143408 A | 0.000963 A |
| 温度 | 0.040300°C | 0.728600°C | 0.040606°C |

## 生成文件

| 文件 | 内容 |
| --- | --- |
| `waveforms/14-adc-front-end-config.csv` | 前端参数和通道 LSB |
| `waveforms/14-adc-mapping-summary.csv` | PASS/FAIL/INFO 指标 |
| `waveforms/14-adc-mapping-samples.csv` | 607 行真实 C 输出 |
| `waveforms/14-adc-code-to-q20.png` | code 到工程量映射曲线 |
| `waveforms/14-adc-calibration-error.png` | 元件偏差和校准误差 |
| `reports/14-adc-mapping-report.md` | 完整报告 |

## 常见失败

### 编译器报告 int64 溢出

不要把 ADC code、参考微伏、校准分压分子和 Q20 缩放因子直接连乘。先把 code 转成不超过 3,300,000 的 `adc_uv`，再完成分压换算。

### 标称误差超过一个 LSB

检查满量程分母是否使用 4095、舍入是否在除法前执行，以及分压分子分母是否写反。

### 电流在 0 A 附近总是偏正或偏负

检查 `current_offset_uv`。零点和增益必须分别校准，不能只调整比例系数。

### 校准后误差没有下降

确认输入 code 是按偏差后的实际前端生成，而固件配置已经切换到对应校准值。不要同时修改“真实前端”和“固件参数”后再比较。

### code 超过 4095 但没有标志

检查 ADC 原始码值是否在映射层统一调用满量程钳位。控制器层不应再增加第二套 code 范围判断。
