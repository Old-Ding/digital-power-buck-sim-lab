# PLECS 模型目录

建议第一版模型命名为：

```text
buck_power_stage.plecs
```

模型只负责功率级和可测量物理量：

- 输入电源 Vin
- Buck 主功率回路
- 电感电流 IL
- 输出电压 Vout
- 输出电流 Iout
- 开关节点 SW
- 等效温度变量，第一阶段可先用受控信号模拟

控制器可以先在 PLECS 内部用简单模块验证，稳定后再把控制逻辑迁到 MATLAB/Simulink 或 C 风格代码。
