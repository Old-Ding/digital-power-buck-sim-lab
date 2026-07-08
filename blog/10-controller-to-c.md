# 从 PLECS/Simulink 控制器迁移到 C 代码

## 问题

仿真控制器要能落地到 MCU，必须明确固定周期入口、参数配置、状态变量和 telemetry。

## 当前代码结构

```text
pi_controller.*
protection.*
power_state_machine.*
power_control.*
config.h
```

## 待补

- 与 Simulink 信号命名对齐
- 固定周期调用示例
- MCU 迁移注意点
