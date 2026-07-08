# digital-power-buck-sim-lab

这是一个面向数字电源仿真的 Buck 电源学习项目。当前公开仓库只保留已经完成、可以复现的内容：教程文章、PLECS/Simulink 模型、导出脚本、原始数据和波形图。

## 当前规格

| 项目 | 目标值 |
| --- | --- |
| 拓扑 | Buck |
| 输入电压 | 24 V 标称值 |
| 输出电压 | 12 V |
| 输出电流 | 5 A |
| 输出功率 | 60 W |
| 开关频率 | 200 kHz |
| 当前阶段 | 离散 PI 电压环 |

第一阶段只做低压 DC-DC，不涉及市电输入和隔离拓扑。

## 已完成内容

| 章节 | 内容 | 状态 |
| --- | --- | --- |
| 01 | 为什么从 Buck 开始做 MATLAB + PLECS 仿真 | 已完成 |
| 02 | PLECS 搭建开环 Buck 功率级 | 已完成，可复现 |
| 03 | Buck 电感、电容和开关频率参数设计 | 已完成，可复现 |
| 04 | 离散 PI 电压环 | 已完成，可复现 |

第二章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/02-open-loop-buck.md` |
| 复现说明 | `docs/02-open-loop-buck-reproduce.md` |
| PLECS 模型 | `models/plecs/buck_open_loop_24v_12v.plecs` |
| 导出脚本 | `scripts/export_open_loop_waveforms.py` |
| 原始数据 | `waveforms/02-open-loop-data.csv` |
| 指标汇总 | `waveforms/02-open-loop-summary.csv` |
| 波形图 | `waveforms/02-open-loop-*.png` |

第三章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/03-buck-parameter-design.md` |
| 复现说明 | `docs/03-buck-parameter-design-reproduce.md` |
| 参数估算脚本 | `scripts/export_parameter_sweep.py` |
| PLECS 参数扫描脚本 | `scripts/export_plecs_parameter_sweep.py` |
| 公式估算汇总 | `waveforms/03-parameter-sweep-summary.csv` |
| PLECS 扫描汇总 | `waveforms/03-plecs-parameter-sweep-summary.csv` |
| 图表 | `waveforms/03-*.png`、`waveforms/03-plecs-*.png` |

第四章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/04-discrete-pi-control.md` |
| 复现说明 | `docs/04-discrete-pi-control-reproduce.md` |
| Simulink 平均模型 | `models/simulink/buck_discrete_pi_voltage_loop.slx` |
| Simulink 截图脚本 | `scripts/export_simulink_discrete_pi_snapshot.m` |
| Python 仿真脚本 | `scripts/export_discrete_pi_control.py` |
| 原始数据 | `waveforms/04-discrete-pi-control-trace.csv` |
| 指标汇总 | `waveforms/04-discrete-pi-control-summary.csv` |
| 波形图 | `waveforms/04-*.png` |

## 复现方式

在仓库根目录运行：

```powershell
python scripts\export_open_loop_waveforms.py
```

如果 PLECS RPC 已启动，脚本会调用 PLECS 导出仿真数据和波形图。如果 PLECS RPC 没有启动，但已有 CSV 数据存在，脚本会基于 CSV 重新生成波形图，并明确提示“未重新运行 PLECS 仿真”。

第 3 章的参数估算图表运行：

```powershell
python scripts\export_parameter_sweep.py
```

这个脚本不重新运行 PLECS 参数扫描，只生成公式估算表格和图表，并读取第 2 章已有 PLECS 汇总数据做基准对照。

第 3 章的 PLECS 参数扫描运行：

```powershell
python scripts\export_plecs_parameter_sweep.py
```

运行前需要启动 PLECS RPC Server，并确认 `localhost:1080` 可用。该脚本会对 `Lo`、`Co`、`fsw` 做真实参数扫描，导出 `waveforms/03-plecs-*` 结果。

第 4 章的离散 PI 平均模型仿真运行：

```powershell
python scripts\export_discrete_pi_control.py
```

第 4 章的 Simulink 模型截图生成运行：

```powershell
matlab -batch "run('scripts/export_simulink_discrete_pi_snapshot.m'); exit"
```

第 4 章不需要启动 PLECS RPC。该章重点验证离散 PI 控制器的数据流、采样周期、积分项和 duty 更新；开关级波形仍在 PLECS 章节中验证。

## 第二章结果

| 指标 | 结果 |
| --- | --- |
| 稳态输出电压 | 约 12 V |
| 稳态电感电流 | 约 5 A |
| MOSFET Vds | 0 V / 24 V 周期切换 |
| 启动 Vout 峰值 | 约 20.8 V |
| 启动 IL 峰值 | 约 27.3 A |

启动过冲来自开环硬启动和 LC 自然响应，不代表功率级接线错误。后续章节会用软启动和闭环控制继续处理这个问题。

## 第三章结果

| 指标 | 结果 |
| --- | --- |
| 满载等效负载 | 2.4Ω |
| 理想 Buck 开环占空比 | 0.5 |
| 22uH 下电感纹波估算 | 约 1.36A |
| PLECS 扫描电感纹波 | 约 1.31A |
| 100uF 下输出纹波估算 | 约 8.52mV |
| PLECS 扫描输出纹波 | 约 8.50mV |
| 22uH / 100uF LC 自然频率 | 约 3.39kHz |
| PLECS 扫描启动 Vout 峰值 | 约 20.8V |
| PLECS 扫描启动 IL 峰值 | 约 27.3A |

第 3 章通过公式估算解释 L、C 和 fsw 的趋势，再用 PLECS RPC 参数扫描验证稳态纹波和开环硬启动峰值。

## 第四章结果

| 指标 | 结果 |
| --- | --- |
| 控制周期 | 5us |
| PI 参数 | Kp = 0.05，Ki = 200 |
| 输入扰动 | Vin 24V -> 20V |
| 负载扰动 | 5A -> 7.5A |
| P-only 输入阶跃后 Vout | 约 11.00V |
| PI 输入阶跃后 Vout | 约 12.00V |
| PI 负载阶跃后 Vout | 约 12.00V |
| PI duty 范围 | 约 0.504 - 0.648 |
| 输入阶跃 1% 恢复时间 | 约 2.41ms |
| 负载阶跃 1% 恢复时间 | 约 1.01ms |

第 4 章通过平均模型验证离散 PI 电压环的数据流：采样 Vout、计算误差、更新积分项、输出 duty，再反馈到 Buck 平均功率级。该章故意不加入 duty 限幅和抗积分饱和，相关问题放到第 5 章单独处理。

## 仓库结构

```text
assets/             教程图片和仿真工具截图
blog/               已完成教程
docs/               已完成章节的复现说明
models/plecs/       PLECS 模型
models/simulink/    Simulink 平均模型
scripts/            可复现脚本
waveforms/          仿真原始数据、指标和波形图
```

当前仓库只展示已完成内容，未完成主题不会提前放入公开目录。

## 后续计划

| 顺序 | 内容 |
| --- | --- |
| 05 | 占空比限幅和抗积分饱和 |
| 06 | 软启动 |
| 07 | 保护状态机 |
| 08 | 负载突变测试 |
| 09 | ADC 噪声和 duty 抖动 |
| 10 | 从仿真控制器整理到 C 风格代码 |

后续主题会在完成模型、数据、波形和说明后加入本仓库。

## 技术交流

如果你在复现模型、搭建 PLECS 电路或判断波形时遇到问题，可以加入技术交流群交流。

本仓库中的模型、脚本、数据和波形可以直接使用，不需要加群获取；交流群主要用于复现答疑和后续技术交流。

| 渠道 | 信息 |
| --- | --- |
| QQ 群 | 嵌入式交流群：1056095456 |
| 加群链接 | [https://qm.qq.com/q/rygrSD2Ddu](https://qm.qq.com/q/rygrSD2Ddu) |
| 微信交流 | 微信入口会不定期更新，可在 QQ 群内获取 |

提问时建议附上拓扑截图、关键参数、仿真波形和报错信息，方便定位问题。

## 许可

本仓库代码和文档采用 MIT License。PLECS、MATLAB/Simulink 等商业软件本体不包含在本仓库中，使用者需要自行安装并遵守对应软件许可。
