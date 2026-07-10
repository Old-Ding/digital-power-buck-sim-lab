# 第 20 章复现说明：低压硬件最终验收

## 目标

使用公开 test plan、本地设备清单、实测数值和仓库相对证据文件，计算 24 V/12 V/5 A Buck 数字电源的最终 PASS/FAIL/BLOCKED，并控制 v1.0 发布门禁。

## 当前环境结果

```text
summary,pass=1,blocked=18,fail=0,tests=19,v1=BLOCKED
hardware,probe=0,board=0,serial=0
```

当前只通过第十九章软件回归；没有检测到开发板、USB 调试探针和串口，也没有本地台架设备清单或测量文件。

## 最短命令

```powershell
python scripts\run_hardware_acceptance.py
```

返回码：

| 返回码 | 含义 |
| ---: | --- |
| 0 | 全部选定验收项 PASS，可继续审核 v1.0 |
| 1 | 至少一项 FAIL |
| 2 | 没有 FAIL，但至少一项 BLOCKED |

## 准备本地文件

```powershell
Copy-Item hardware\acceptance\inventory-template.csv `
  hardware\acceptance\inventory.local.csv

Copy-Item hardware\acceptance\measurements-template.csv `
  hardware\acceptance\measurements.local.csv
```

两个 `.local.csv` 和 `evidence/local/` 已被 Git 忽略。

## test-plan.csv

| 字段 | 含义 |
| --- | --- |
| `test_id` | 稳定测试编号，与测量模板逐行对应 |
| `stage` / `scenario` | 安全执行阶段与工况 |
| `measurement` / `unit` | 被测量和单位 |
| `min_value` / `max_value` | 自动判定下限与上限，空值表示单边不限 |
| `evidence_required` | 是否必须提供公开证据文件 |
| `required_items` | 本项测试依赖的设备 ID，用分号分隔 |
| `procedure_summary` | 最短操作说明 |

`required_items` 决定单项是否具备执行条件。把 inventory 中的 `required` 改成 `no` 不会绕过测试依赖；只有硬件路线确实改变并重新审核 test plan 时，才修改公开依赖关系。

## inventory.local.csv

字段：

| 字段 | 含义 |
| --- | --- |
| `item` | 固定设备标识 |
| `label` | 报告与状态图使用的中文设备名 |
| `required` | 是否为完整发布路线必需 |
| `available` | 实际可用时填 `yes` |
| `model` | 型号，便于复现实验 |
| `calibration_due` | 仪器校准到期日 |
| `notes` | 探头倍率、功率限制等 |

开发板通过型号登记确认；调试探针必须同时登记型号并由 Windows PnP 检测到。开发板 PnP 数量只作参考，因为 SWD 目标不会稳定显示为独立 Windows 设备。

## measurements.local.csv

字段：

| 字段 | 含义 |
| --- | --- |
| `test_id` | 对应 test plan ID |
| `measured_value` | 只填数值，不带单位 |
| `evidence_file` | 仓库相对公开证据路径 |
| `operator` | 操作记录名称 |
| `timestamp` | ISO 8601 时间 |
| `notes` | 仪器设置和工况说明 |

证据文件放入 `hardware/acceptance/evidence/public/`。绝对路径、仓库外路径和不存在的文件不会通过。

## 执行顺序

1. `SW-01`：确认第十九章全回归无失败步骤。
2. `FW-01`：用板级 HAL 构建、烧录目标固件并确认复位启动。
3. `PRE-01`：断电检查输入对地电阻。
4. `SUP-01`：只给控制板供电并检查 3.3 V。
5. `PWM-01/02`：功率级断电，测频率和死区。
6. `START-01`：24 V、0.2 A 限流、空载启动。
7. `STEADY/RIPPLE`：1 A→3 A→5 A 逐级加载。
8. `LOAD/LINE`：负载和输入瞬态。
9. `UVLO/OCP`：受控保护注入与门极关断延迟。
10. `ISR-01`：DWT 或 GPIO 测最坏执行时间。
11. `THERMAL-01`：5 A 运行 10 分钟并记录温升。

前一阶段失败时停止上电，不继续增加电压或负载。

## 自动判定

每个 test plan 行提供 `min_value`、`max_value` 和 `evidence_required`。脚本判定：

```text
该测试在 `required_items` 中列出的设备齐全
AND measured_value 在上下限内
AND 必需 evidence_file 存在
→ PASS
```

设备、测量值或证据缺失得到 BLOCKED；数值格式错误、超限或证据路径无效得到 FAIL。

## 当前生成文件

| 文件 | 内容 |
| --- | --- |
| `waveforms/20-hardware-inventory.csv` | PnP 检测和设备模板状态 |
| `waveforms/20-acceptance-summary.csv` | 19 项验收结果 |
| `waveforms/20-acceptance-status.png` | 必需设备和测试状态 |
| `reports/20-hardware-acceptance-report.md` | v1.0 状态与完整表格 |

## 当前硬件事实

| 检查 | 结果 |
| --- | ---: |
| 调试探针 USB 设备 | 0 |
| 开发板 PnP 设备 | 0 |
| 串口 | 0 |
| J-Link 软件 | 已安装 |
| 完整发布所需设备登记 | 0/9 |

J-Link 软件安装不能替代 USB 调试器、目标板或固件下载结果。

## 常见失败

### 脚本返回 2

打开 `reports/20-hardware-acceptance-report.md`，先补设备表，再补对应测量值和证据。BLOCKED 不应改成 PASS。

### available=yes 但仍未通过

填写设备型号并连接开发板/调试器；确认使用的是 `inventory.local.csv`，不是模板文件。

### measured_value 在范围内但 FAIL

检查 `evidence_file` 是否为仓库相对路径，文件是否位于仓库内并真实存在。

### PWM 死区测量异常

先确认探头参考方式和通道延迟，再检查目标定时器死区编码。第十五章的线性 17 counts 不能直接替代具体 MCU 寄存器编码。

### ISR 超过 3.5 us

用分阶段 GPIO 或 DWT 定位耗时，重点检查第十八章发现的 64 位整数除法助手、未优化构建和中断内日志。

### OCP 测试触发电源限流

区分台式电源输入限流与输出电子负载 OCP。缩短斜坡或脉冲时间，并确保功率级额定值允许该测试。

### 温度超过 90°C

停止满载，检查 MOSFET 导通/开关损耗、电感饱和、死区、驱动电压、铜箔和散热。不要提高 test plan 上限掩盖热设计问题。
