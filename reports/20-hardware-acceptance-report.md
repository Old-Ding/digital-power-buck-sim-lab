# 第 20 章报告：低压硬件最终验收

本报告由 `scripts/run_hardware_acceptance.py` 生成。软件回归自动读取第19章结果；硬件项目由设备清单、数值范围和公开证据文件共同判定。

## 摘要

- 验收项：PASS 1 / BLOCKED 18 / FAIL 0
- v1.0 门禁：`BLOCKED`
- 调试探针设备数：0
- 开发板设备数：0
- 串口数：0
- J-Link 软件：已安装

## 必需设备

| 设备 | ID | 必需 | 可用 | 来源 | 说明 |
| --- | --- | --- | --- | --- | --- |
| Cortex-M4F开发板 | `development_board` | yes | no | template | 未登记型号；PnP开发板数量 0（仅供参考） |
| 24V/12V/5A功率级 | `power_stage_24v_12v_5a` | yes | no | template | 未登记型号 |
| 限流台式电源 | `current_limited_supply_0_30v_5a` | yes | no | template | 未登记型号 |
| 电子负载 | `electronic_load_0_30v_10a` | yes | no | template | 未登记型号 |
| 示波器 | `oscilloscope_100mhz` | yes | no | template | 未登记型号 |
| 差分探头 | `differential_probe_50v` | yes | no | template | 未登记型号 |
| 万用表 | `multimeter` | yes | no | template | 未登记型号 |
| 调试接口/探针 | `debug_probe` | yes | no | template | 未登记型号；PnP探针数量 0 |
| 测温设备 | `thermal_camera_or_thermocouple` | yes | no | template | 未登记型号 |
| 检测到的串口 | `detected_serial_ports` | no | no | Windows CIM | 数量 0 |
| J-Link软件 | `jlink_software` | no | yes | installed software | 软件存在不代表调试器已连接 |

## 验收项

| ID | 场景 | 测量 | 范围 | 实测 | 状态 | 原因 |
| --- | --- | --- | --- | ---: | --- | --- |
| `SW-01` | 第19章全回归 | 失败顶层步骤 / count | 0～0 | 0.0 | PASS | 第19章顶层步骤失败数 |
| `FW-01` | 目标HAL构建烧录与复位启动 | 烧录或启动失败数 / count | 0～0 | - | BLOCKED | 本项缺少设备：Cortex-M4F开发板、调试接口/探针 |
| `PRE-01` | 输入对地静态检查 | 输入端对地电阻 / ohm | 1000～+∞ | - | BLOCKED | 本项缺少设备：24V/12V/5A功率级、万用表 |
| `SUP-01` | 只给控制板供电 | 3.3V电源轨 / V | 3.20～3.40 | - | BLOCKED | 本项缺少设备：Cortex-M4F开发板、万用表 |
| `PWM-01` | 功率级不加输入电压 | PWM频率 / kHz | 198～202 | - | BLOCKED | 本项缺少设备：Cortex-M4F开发板、调试接口/探针、示波器 |
| `PWM-02` | 互补PWM低压检查 | 上下管死区 / ns | 80～120 | - | BLOCKED | 本项缺少设备：Cortex-M4F开发板、调试接口/探针、示波器、差分探头 |
| `START-01` | 24V限流空载启动 | Vout峰值 / V | 0～13.2 | - | BLOCKED | 本项缺少设备：Cortex-M4F开发板、调试接口/探针、24V/12V/5A功率级、限流台式电源、示波器 |
| `STEADY-01` | 24V输入1A负载 | Vout平均值 / V | 11.88～12.12 | - | BLOCKED | 本项缺少设备：Cortex-M4F开发板、24V/12V/5A功率级、限流台式电源、电子负载、万用表 |
| `STEADY-03` | 24V输入3A负载 | Vout平均值 / V | 11.88～12.12 | - | BLOCKED | 本项缺少设备：Cortex-M4F开发板、24V/12V/5A功率级、限流台式电源、电子负载、万用表 |
| `STEADY-05` | 24V输入5A负载 | Vout平均值 / V | 11.88～12.12 | - | BLOCKED | 本项缺少设备：Cortex-M4F开发板、24V/12V/5A功率级、限流台式电源、电子负载、万用表 |
| `RIPPLE-01` | 24V输入5A负载 | Vout纹波峰峰值 / mVpp | 0～100 | - | BLOCKED | 本项缺少设备：Cortex-M4F开发板、24V/12V/5A功率级、限流台式电源、电子负载、示波器 |
| `LOAD-01` | 2.5A与5A往返 | Vout最大偏差 / V | 0～1.2 | - | BLOCKED | 本项缺少设备：Cortex-M4F开发板、24V/12V/5A功率级、限流台式电源、电子负载、示波器 |
| `LOAD-02` | 2.5A与5A往返 | 回到1%范围时间 / ms | 0～12 | - | BLOCKED | 本项缺少设备：Cortex-M4F开发板、24V/12V/5A功率级、限流台式电源、电子负载、示波器 |
| `LINE-01` | 20V与28V输入切换 | Vout最大偏差 / V | 0～0.24 | - | BLOCKED | 本项缺少设备：Cortex-M4F开发板、24V/12V/5A功率级、限流台式电源、电子负载、示波器 |
| `UVLO-01` | 输入降到17V | 有效PWM关断延迟 / us | 0～5 | - | BLOCKED | 本项缺少设备：Cortex-M4F开发板、24V/12V/5A功率级、限流台式电源、电子负载、示波器 |
| `OCP-01` | 电子负载电流斜坡 | OCP触发电流 / A | 6.5～7.0 | - | BLOCKED | 本项缺少设备：Cortex-M4F开发板、24V/12V/5A功率级、限流台式电源、电子负载、示波器 |
| `OCP-02` | OCP触发 | 有效PWM关断延迟 / us | 0～5 | - | BLOCKED | 本项缺少设备：Cortex-M4F开发板、24V/12V/5A功率级、限流台式电源、电子负载、示波器 |
| `ISR-01` | 最坏输入与保护路径 | 控制ISR最坏执行时间 / us | 0～3.5 | - | BLOCKED | 本项缺少设备：Cortex-M4F开发板、调试接口/探针 |
| `THERMAL-01` | 24V输入5A运行10分钟 | 最高器件温度 / degC | -40～90 | - | BLOCKED | 本项缺少设备：Cortex-M4F开发板、24V/12V/5A功率级、限流台式电源、电子负载、测温设备 |

## 发布边界

当前软件全回归可以作为 Cortex-M4F 软件基线证据。没有开发板、功率级、台式电源、电子负载、示波器、差分探头、万用表、测温设备和真实测量文件时，硬件验收保持 BLOCKED；v1.0 标签不得创建。
