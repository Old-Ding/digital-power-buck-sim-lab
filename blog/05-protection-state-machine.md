# 电源软件状态机如何设计

## 问题

保护逻辑如果散落在 PI、PWM、状态分支里，调试时很难确定谁负责关断和锁存故障。

## 设计

```text
Protection 检测故障
State Machine 锁存故障
Power Control 统一关断 PWM
```

## 待补

- 状态机波形
- 故障注入测试
- 故障码记录
