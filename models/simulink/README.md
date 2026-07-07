# Simulink 模型目录

建议第一版模型命名为：

```text
digital_controller.slx
```

模型重点放在数字控制软件行为：

- ADC 采样周期
- PWM 更新周期
- 离散 PI 控制
- 软启动参考值
- 保护检测输入
- 状态机输出
- telemetry 关键变量导出

如果后续连接 PLECS Blockset，保持接口信号命名和 `controller/config.h` 一致，便于迁移到 MCU。
