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
| 11 | `11-host-build-test-gate.md` | 给 C 控制器搭建 Host 编译与单元测试门禁 |

## 后续主题

后续内容会在源码、测试、报告和文章完成后再加入。第二季会继续扩展到 C 编译工具链补齐、host 单元测试、定点化、ADC/PWM 映射、ISR 分层、HAL 适配、CI/HIL 和实机闭环。
