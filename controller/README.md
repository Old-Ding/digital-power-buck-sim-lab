# controller

这里放接近 MCU 固件结构的 C 风格控制代码，用来证明仿真控制器具备落地路径。

分层原则：

```text
pi_controller.*          只处理离散 PI、限幅、抗积分饱和
protection.*             只处理故障检测和故障优先级
power_state_machine.*    只处理状态切换和故障锁存
power_control.*          汇总采样、状态、控制输出和 telemetry
config.h                 集中放参数，便于仿真和固件对齐
```

后续接入 MCU 时，`power_control_step()` 可以放到固定周期控制任务里，由 ADC/PWM 中断或调度器驱动。
