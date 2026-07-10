# 发布就绪状态

## 当前结论

| 发布层级 | 状态 | 证据 |
| --- | --- | --- |
| 第 11～19 章软件与目标构建基线 | READY | 本地全回归与 GitHub Actions 均通过 |
| Cortex-M4F 可烧录功能固件 | BLOCKED | 目标 HAL 仍为可编译寄存器模型 |
| 低压硬件验收 | BLOCKED | 当前未检测到开发板、调试探针或串口，且没有台架测量证据 |
| `v1.0.0` 标签 | BLOCKED | 第 20 章全部硬件验收项通过后才能创建 |

## v1.0.0 必须满足

1. `python scripts/run_full_regression.py` 全部通过。
2. `python scripts/run_hardware_acceptance.py` 返回退出码 0。
3. `waveforms/20-acceptance-summary.csv` 无 BLOCKED/FAIL。
4. 所有硬件 PASS 行都有仓库相对公开证据文件。
5. 目标 HAL 已替换寄存器模型并记录目标板、功率级和工具链版本。
6. 目标 ISR 最坏执行时间不超过 3.5 us。
7. 24 V/12 V/5 A 稳态、瞬态、保护和温升测试全部满足 `hardware/acceptance/test-plan.csv`。

不满足上述条件时，可以继续维护软件基线，但不能把仓库描述为完成 HIL 或实物闭环验证。
