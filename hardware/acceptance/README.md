# 低压硬件验收包

本目录定义 24 V 输入、12 V/5 A 输出 Buck 数字电源的最终低压验收数据格式。

## 文件

| 文件 | 用途 |
| --- | --- |
| `test-plan.csv` | 测试场景、单位和自动判定上下限 |
| `inventory-template.csv` | 台架设备清单模板 |
| `measurements-template.csv` | 测量值和证据路径模板 |
| `inventory.local.csv` | 本机设备清单，不提交 Git |
| `measurements.local.csv` | 本机测量记录，不提交 Git |
| `evidence/public/` | 经过筛选、可以公开的示波器截图和照片 |
| `evidence/local/` | 原始采集文件，不提交 Git |

`test-plan.csv` 的 `required_items` 按测试定义设备依赖；`inventory.local.csv` 中的 `required` 不能覆盖或绕过该依赖。

## 使用

```powershell
Copy-Item hardware\acceptance\inventory-template.csv hardware\acceptance\inventory.local.csv
Copy-Item hardware\acceptance\measurements-template.csv hardware\acceptance\measurements.local.csv
```

填写设备型号、测量值和证据相对路径后运行：

```powershell
python scripts\run_hardware_acceptance.py
```

脚本根据 `test-plan.csv` 中每项测试的设备依赖和数值上下限计算 PASS/FAIL。该项依赖的设备、测量值或证据文件缺失时，结果为 BLOCKED，其他已经具备条件的测试仍可独立验收。

## 安全边界

- 只使用隔离的 0～30 V DC 台式电源，不接市电整流母线。
- 首次上电必须设置电流限制，并先确认 PWM 默认关闭。
- 测量开关节点和上下管门极差分电压时使用合适的差分探头；普通示波器地夹不能随意接到开关节点。
- OCP 测试使用电子负载斜坡或限时脉冲，不直接用导线短路输出。
- 更换功率级器件后，以器件数据手册和 PCB 额定值重新审核温度、电压和电流上限。
