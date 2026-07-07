# 离散 PI 电压环

## 控制目标

在输入电压和负载变化时，将输出电压稳定在 12V。

## 控制周期

```text
PWM frequency: 200kHz
Control frequency: 50kHz
```

控制频率低于 PWM 频率，是为了贴近真实 MCU 中 ADC 采样、控制计算和 PWM 更新的调度关系。

## 控制变量

```text
vref
vout_adc
error
kp
ki
integrator
duty
```

## 关键决策

占空比限幅和抗积分饱和放在 PI 层，因为它们属于控制器内部状态；过压、过流、欠压不在 PI 层判断，统一放在保护层。
