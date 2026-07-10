# 第 19 章报告：仓库质量与第 11～18 章全链路回归

本报告由 `scripts/run_full_regression.py` 生成。每个步骤调用对应章节的真实编译、回放、映像或质量检查入口。

## 摘要

- Python：`3.14.0`
- 系统：`Windows 11`
- 步骤：PASS 9 / FAIL 0
- 本机总运行时间：27.146 s

## 步骤

| 步骤 | 状态 | 退出码 | 时间/s | 子步骤摘要 |
| --- | --- | ---: | ---: | --- |
| `repository_quality` | PASS | 0 | 0.978 | `summary,pass=9,fail=0,checks=9` |
| `chapter11_host_build` | PASS | 0 | 1.296 | `summary,pass=4,blocked=0,skipped=0,fail=0` |
| `chapter12_c_python` | PASS | 0 | 5.160 | `summary,pass=55,fail=0,scenarios=5,rows=80400` |
| `chapter13_fixed_point` | PASS | 0 | 6.575 | `summary,pass=74,fail=0,scenarios=5,rows=80400` |
| `chapter14_adc_map` | PASS | 0 | 2.523 | `summary,pass=22,fail=0,info=4,rows=607` |
| `chapter15_pwm_map` | PASS | 0 | 3.760 | `summary,pass=15,fail=0,rows=640` |
| `chapter16_isr` | PASS | 0 | 2.571 | `summary,pass=13,fail=0,info=4,cycles=6,batches=200` |
| `chapter17_layering` | PASS | 0 | 2.198 | `summary,pass=21,fail=0,phases=12,events=34` |
| `chapter18_target` | PASS | 0 | 2.085 | `summary,pass=13,fail=0,info=1,sections=5,symbols=107,instructions=1695` |

## 判定边界

全回归可以证明仓库中的主机测试、数值对照、定点/映射检查、固件分层和 Cortex-M4F 构建在当前提交上同时成立。它不连接开发板、电源、电子负载或示波器，因此不能替代第 20 章的 HIL/低压实物验收。
