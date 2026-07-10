# 教程目录

这里保存已经完成并适合阅读的教程。

## 已发布

| 章节 | 文件 | 主题 |
| --- | --- | --- |
| 01 | `01-project-overview.md` | 为什么从 Buck 开始做 MATLAB + PLECS 仿真 |
| 02 | `02-open-loop-buck.md` | PLECS 搭建开环 Buck 功率级 |
| 03 | `03-buck-parameter-design.md` | Buck 电感、电容和开关频率参数设计 |
| 04 | `04-discrete-pi-control.md` | 离散 PI 电压环 |
| 05 | `05-duty-limit-anti-windup.md` | duty 限幅和抗积分饱和 |
| 06 | `06-soft-start.md` | 软启动 |
| 07 | `07-protection-state-machine.md` | 保护状态机 |
| 08 | `08-load-transient.md` | 负载突变测试 |
| 09 | `09-adc-noise-duty-jitter.md` | ADC 噪声和 duty 抖动 |
| 10 | `10-controller-to-c.md` | 仿真控制器整理成 C 风格代码 |
| 11 | `11-host-build-test-gate.md` | 为什么上板前要先做 C 语言单元测试 |
| 12 | `12-c-python-parity.md` | C 控制器编译通过后，怎么确认结果没有改错 |
| 13 | `13-fixed-point-controller.md` | 浮点控制器怎么改成定点数并验证不会溢出 |
| 14 | `14-adc-to-q20-mapping.md` | ADC 原始码怎么变成 Q20 电压、电流和温度 |
| 15 | `15-pwm-timer-mapping.md` | Q20 duty 怎么变成中心对齐 PWM 比较值 |
| 16 | `16-control-isr-timing.md` | 5 us 控制中断里 ADC、控制器和 PWM 应该按什么顺序执行 |

## 后续主题

后续内容会在源码、测试、报告和文章完成后再加入。第二季下一步将区分中断内实时任务与后台任务，并用 HAL 适配接口连接具体硬件。
