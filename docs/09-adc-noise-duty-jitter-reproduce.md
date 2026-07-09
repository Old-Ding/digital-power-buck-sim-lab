# 第 9 章复现说明：ADC 噪声和 duty 抖动

本说明对应文章：`blog/09-adc-noise-duty-jitter.md`

本章目标是复现 Buck 数字电源中 ADC 采样噪声如何进入误差计算，并通过 PI 控制器变成 `duty_raw` / `duty_cmd` 抖动。

## 复现边界

本章使用两类输出：

| 类型 | 文件 | 作用 |
| --- | --- | --- |
| Simulink 采样链路模型 | `scripts/export_simulink_adc_noise_duty_jitter_snapshot.m` | 生成 ADC 噪声到 duty 抖动的 `.slx` 和结构截图 |
| MATLAB 平均模型 | `scripts/export_matlab_adc_noise_duty_jitter_waveforms.m` | 生成 ADC 噪声、滤波、duty 抖动波形和指标 |

正文主波形对应 `waveforms/09-matlab-adc-noise-*.png` 文件。

本章不需要运行 PLECS RPC。

原因是本章验证的是采样值、误差、PI 和 duty 指令之间的软件数据流，不是 MOSFET 开关尖峰、二极管恢复、电感纹波或 EMI。

## 环境要求

必须具备：

| 工具 | 用途 |
| --- | --- |
| MATLAB R2024b 或相近版本 | 运行 ADC 噪声脚本，导出正文主波形 |
| Simulink | 生成采样链路 `.slx` 模型和截图 |

推荐复现顺序：

| 顺序 | 命令 | 目的 |
| --- | --- | --- |
| 1 | `matlab -batch "run('scripts/export_simulink_adc_noise_duty_jitter_snapshot.m'); exit"` | 生成 Simulink 采样链路模型和截图 |
| 2 | `matlab -batch "run('scripts/export_matlab_adc_noise_duty_jitter_waveforms.m'); exit"` | 运行 MATLAB 平均模型并导出正文波形 |

## 运行 Simulink 采样链路截图脚本

在仓库根目录运行：

```powershell
matlab -batch "run('scripts/export_simulink_adc_noise_duty_jitter_snapshot.m'); exit"
```

如果 MATLAB 没有加入 PATH，在 Windows 上可以使用本机安装路径，例如：

```powershell
& 'D:\Program Files\MATLAB\R2024b\bin\matlab.exe' -batch "run('scripts/export_simulink_adc_noise_duty_jitter_snapshot.m'); exit"
```

脚本会生成或更新：

| 文件 | 内容 |
| --- | --- |
| `models/simulink/buck_adc_noise_duty_jitter_logic.slx` | ADC 噪声到 duty 抖动结构模型 |
| `assets/screenshots/09-simulink-adc-noise-duty-jitter-logic.png` | 文章使用的结构截图 |

该图用于理解数据流：

```text
actual Vout -> ADC front end -> measurement filter
Vref / Vout_meas -> error -> voltage_loop_PI()
raw duty -> duty_limit_anti_windup() -> PWM duty update
duty -> averaged Buck plant -> actual Vout
```

## 运行 MATLAB ADC 噪声脚本

在仓库根目录运行：

```powershell
matlab -batch "run('scripts/export_matlab_adc_noise_duty_jitter_waveforms.m'); exit"
```

如果 MATLAB 没有加入 PATH，可以使用完整路径：

```powershell
& 'D:\Program Files\MATLAB\R2024b\bin\matlab.exe' -batch "run('scripts/export_matlab_adc_noise_duty_jitter_waveforms.m'); exit"
```

预期输出类似：

```text
已生成第 9 章 ADC 噪声与 duty 抖动仿真数据与图表。
noisy_adc,duty_rms_jitter=0.000320722,equiv_pwm_rms_jitter_ns=1.60361,measured_noise_rms_mv=15.1777
moving_average_4,duty_rms_jitter=0.000196784,reduction_pct=38.6433,delay_us=7.5
iir_alpha_0p25,duty_rms_jitter=0.000226622,reduction_pct=29.3401,delay_us=15
```

脚本会生成或更新以下文件：

| 文件 | 内容 |
| --- | --- |
| `waveforms/09-matlab-adc-noise-duty-jitter-trace.csv` | ADC、测量值、误差、duty 采样点 |
| `waveforms/09-matlab-adc-noise-duty-jitter-summary.csv` | 关键指标汇总 |
| `waveforms/09-matlab-adc-noise-duty-jitter-overview.png` | ADC 噪声进入反馈链路的局部波形 |
| `waveforms/09-matlab-adc-noise-duty-jitter-comparison.png` | 不同测量链路下 duty 抖动对比 |
| `waveforms/09-matlab-adc-noise-filter-tradeoff.png` | 滤波降噪和延迟取舍图 |

## 关键参数

| 参数 | 数值 |
| --- | --- |
| 输入电压 | 24V |
| 目标输出 | 12V |
| 满载电流 | 5A |
| 电感 | 22uH |
| 输出电容 | 100uF |
| 控制周期 | 5us |
| PI 参数 | Kp = 0.02，Ki = 80 |
| ADC 位数 | 12 bit |
| ADC 满量程 | 16V |
| ADC LSB | 3.906mV |
| ADC 噪声 | 15mV RMS |

## 对比工况

| 工况 | ADC 噪声 | 滤波 |
| --- | --- | --- |
| `ideal_adc` | 无 | 无 |
| `noisy_adc` | 有 | 无 |
| `moving_average_4` | 有 | 4 点滑动平均 |
| `iir_alpha_0p25` | 有 | 一阶 IIR，alpha = 0.25 |

## 预期指标

`waveforms/09-matlab-adc-noise-duty-jitter-summary.csv` 中应包含以下典型结果：

| 工况 | 测量噪声 RMS | duty RMS 抖动 | 等效 PWM RMS 抖动 | 近似滤波延迟 |
| --- | --- | --- | --- | --- |
| `ideal_adc` | 0mV | 接近 0 | 接近 0 | 0us |
| `noisy_adc` | 约 15.18mV | 约 0.000321 | 约 1.60ns | 0us |
| `moving_average_4` | 约 7.62mV | 约 0.000197 | 约 0.98ns | 7.5us |
| `iir_alpha_0p25` | 约 6.59mV | 约 0.000227 | 约 1.13ns | 15us |

等效 PWM 抖动的计算方式是：

```text
equivalent_pwm_jitter = duty_jitter * switching_period
```

本章开关周期为 5us，因此 duty RMS 抖动 `0.000320722` 对应约 `1.60ns` 等效脉宽变化。

## 常见问题

### 1. 为什么不用 PLECS 开关级模型

本章关注 ADC 噪声进入软件控制链路后的变量传递。平均模型更适合先把 `Vout_adc`、`Vout_meas`、`error`、`raw duty` 和 `duty_cmd` 的关系讲清楚。开关级纹波、器件应力和 EMI 后续仍然要回到 PLECS 或实机测量。

### 2. 为什么 IIR 测量噪声更低，但 duty RMS 抖动不是最低

IIR 的 alpha = 0.25，反馈信号更平滑，但等效延迟也更大。本章这组参数下，4 点滑动平均在 duty RMS 抖动上更低。滤波参数要结合动态响应一起评价，不能只看测量值是否更平。

### 3. 为什么 ideal ADC 还有极小的非零数值

summary 中 ideal ADC 的 duty RMS 抖动属于浮点计算残差，数量级约 `1e-15`，工程上可以视为 0。

### 4. 这是不是最终硬件采样方案

本章不是最终硬件采样方案。它是平均模型下的采样噪声链路验证，最终硬件还需要 ADC 前端阻容、采样保持时间、参考电压、PCB 布局、PWM 同步采样和示波器实测共同验证。

### 5. 如何修改噪声大小或滤波参数

在 `scripts/export_matlab_adc_noise_duty_jitter_waveforms.m` 的 `params()` 中修改：

```matlab
P.adc_noise_rms_v = 0.015;
P.moving_average_points = 4;
P.iir_alpha = 0.25;
```

修改后重新运行 MATLAB 脚本即可生成新的 CSV 和图表。
