# Simulink 模型目录

这里保存已经完成章节使用的 Simulink 模型。

| 文件 | 对应章节 | 用途 |
| --- | --- | --- |
| `buck_discrete_pi_voltage_loop.slx` | 第 4 章 | 离散 PI 电压环平均模型 |
| `buck_duty_limit_anti_windup_logic.slx` | 第 5 章 | duty 限幅和 anti-windup 控制逻辑模型 |

当前 Simulink 模型重点放在数字控制软件行为：

- PWM 更新周期
- 离散 PI 控制
- duty 上下限
- anti-windup 积分边界
- telemetry 关键变量导出

开关节点、电感纹波、MOSFET Vds、二极管电流和器件损耗仍然回到 PLECS 开关级模型中验证。
