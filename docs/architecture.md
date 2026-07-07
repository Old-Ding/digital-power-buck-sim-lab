# 架构说明

## 目标

用一个 24V 输入、12V/5A 输出的数字 Buck 项目展示开关电源软件工程师的核心能力：离散控制、状态机、保护策略、测试验证和可观测性。

## 数据流

```text
Vin/Vout/Iout/Temp 采样
-> protection_check()
-> power_state_machine_step()
-> soft-start reference
-> pi_controller_step()
-> duty
-> PWM
-> PLECS Buck 功率级
```

## 分层理由

- PI 控制器只处理闭环误差和占空比限幅。
- Protection 层只输出故障码。
- State Machine 层只负责状态切换和故障锁存。
- Power Control 层汇总 telemetry，便于后续接 MCU 调试接口。

这样做的原因是故障阈值、状态切换和控制器内部状态变化频率不同，混在一起会导致调参和排障困难。
