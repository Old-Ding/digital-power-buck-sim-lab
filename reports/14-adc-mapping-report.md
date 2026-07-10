# 第 14 章报告：ADC 码值到 Q20 工程量映射

本报告由 `scripts/run_adc_mapping_tests.py` 生成，映射结果来自真实编译执行的 `src/digital_power_adc_map.c`。元件偏差场景是可重复的合成前端参数，不是实物测量数据。

## 执行摘要

- 编译器：`zig 0.16.0`
- C 映射数据行：607
- 指标：PASS 22 / FAIL 0 / INFO 4

C 回放输出：

```text
SUMMARY,OK,rows=607
```

C 单元测试输出：

```text
PASS,nominal_24v_12v_5a_45c
PASS,adc_code_above_full_scale_is_clamped
PASS,sensor_values_respect_physical_limits
SUMMARY,PASS,failures=0
```

## 指标

| 场景 | 指标 | 实际值 | 限制 | 状态 | 说明 |
| --- | --- | ---: | ---: | --- | --- |
| `nominal_sweep` | `max_abs_vin_error` | 0.00370808 | 0.008 | PASS | 最大 V 映射误差不超过约一个通道 ADC LSB |
| `nominal_sweep` | `max_abs_vout_error` | 0.00195057 | 0.0041 | PASS | 最大 V 映射误差不超过约一个通道 ADC LSB |
| `nominal_sweep` | `max_abs_iout_error` | 0.00100784 | 0.0022 | PASS | 最大 A 映射误差不超过约一个通道 ADC LSB |
| `nominal_sweep` | `max_abs_temperature_error` | 0.0403004 | 0.083 | PASS | 最大 degC 映射误差不超过约一个通道 ADC LSB |
| `nominal_operating_point` | `max_abs_vin_error` | 0.00114727 | 0.008 | PASS | 最大 V 映射误差不超过约一个通道 ADC LSB |
| `nominal_operating_point` | `max_abs_vout_error` | 0.000153542 | 0.0041 | PASS | 最大 V 映射误差不超过约一个通道 ADC LSB |
| `nominal_operating_point` | `max_abs_iout_error` | 0.000182152 | 0.0022 | PASS | 最大 A 映射误差不超过约一个通道 ADC LSB |
| `nominal_operating_point` | `max_abs_temperature_error` | 0.0109997 | 0.083 | PASS | 最大 degC 映射误差不超过约一个通道 ADC LSB |
| `tolerance_uncalibrated` | `max_abs_vin_error` | 0.299843 | 0 | INFO | 元件偏差未校准时的最大 V 误差 |
| `tolerance_uncalibrated` | `max_abs_vout_error` | 0.130511 | 0 | INFO | 元件偏差未校准时的最大 V 误差 |
| `tolerance_uncalibrated` | `max_abs_iout_error` | 0.143408 | 0 | INFO | 元件偏差未校准时的最大 A 误差 |
| `tolerance_uncalibrated` | `max_abs_temperature_error` | 0.7286 | 0 | INFO | 元件偏差未校准时的最大 degC 误差 |
| `tolerance_calibrated` | `max_abs_vin_error` | 0.00374165 | 0.008 | PASS | 最大 V 映射误差不超过约一个通道 ADC LSB |
| `tolerance_calibrated` | `max_abs_vout_error` | 0.00195595 | 0.0041 | PASS | 最大 V 映射误差不超过约一个通道 ADC LSB |
| `tolerance_calibrated` | `max_abs_iout_error` | 0.000963402 | 0.0022 | PASS | 最大 A 映射误差不超过约一个通道 ADC LSB |
| `tolerance_calibrated` | `max_abs_temperature_error` | 0.0406063 | 0.083 | PASS | 最大 degC 映射误差不超过约一个通道 ADC LSB |
| `calibration_improvement` | `vin_error_ratio` | 0.0124787 | 0.1 | PASS | 校准后最大误差应低于未校准误差的 10% |
| `calibration_improvement` | `vout_error_ratio` | 0.0149868 | 0.1 | PASS | 校准后最大误差应低于未校准误差的 10% |
| `calibration_improvement` | `iout_error_ratio` | 0.00671792 | 0.1 | PASS | 校准后最大误差应低于未校准误差的 10% |
| `calibration_improvement` | `temperature_error_ratio` | 0.0557319 | 0.1 | PASS | 校准后最大误差应低于未校准误差的 10% |
| `boundary_codes` | `over_code_clamp` | 1 | 1 | PASS | 超过 12-bit 满量程的输入必须被钳位并置标志 |
| `boundary_codes` | `physical_clamp_present` | 1 | 1 | PASS | 电流和温度超出物理范围时必须钳位 |
| `all` | `arithmetic_overflow_count` | 0 | 0 | PASS | ADC 映射整数运算不得溢出 |
| `adc_unit_tests` | `nominal_24v_12v_5a_45c` | 1 | 1 | PASS | ADC 映射 C 单元测试 |
| `adc_unit_tests` | `adc_code_above_full_scale_is_clamped` | 1 | 1 | PASS | ADC 映射 C 单元测试 |
| `adc_unit_tests` | `sensor_values_respect_physical_limits` | 1 | 1 | PASS | ADC 映射 C 单元测试 |

## 结果边界

本报告证明映射公式、Q20 输出、码值钳位、物理范围钳位和校准系数在电脑端 C 测试中成立。未校准元件偏差来自脚本定义的合成参数；真实硬件仍需要测量参考电压、分压比、放大器增益和零点后写入校准值。
