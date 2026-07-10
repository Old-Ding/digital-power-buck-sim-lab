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
| 当前阶段 | 第二季软件链完成；低压硬件验收 BLOCKED |

第一阶段只做低压 DC-DC，不涉及市电输入和隔离拓扑。

## 已完成内容

| 章节 | 内容 | 状态 |
| --- | --- | --- |
| 01 | 为什么从 Buck 开始做 MATLAB + PLECS 仿真 | 已完成 |
| 02 | PLECS 搭建开环 Buck 功率级 | 已完成，可复现 |
| 03 | Buck 电感、电容和开关频率参数设计 | 已完成，可复现 |
| 04 | 离散 PI 电压环 | 已完成，可复现 |
| 05 | duty 限幅和抗积分饱和 | 已完成，可复现 |
| 06 | 软启动 | 已完成，可复现 |
| 07 | 保护状态机 | 已完成，可复现 |
| 08 | 负载突变测试 | 已完成，可复现 |
| 09 | ADC 噪声和 duty 抖动 | 已完成，可复现 |
| 10 | 仿真控制器整理成 C 风格代码 | 已完成，可复现 |
| 11 | 为什么上板前要先做 C 语言单元测试 | 已完成，可复现 |
| 12 | C 控制器编译通过后，怎么确认结果没有改错 | 已完成，可复现 |
| 13 | 浮点控制器怎么改成定点数并验证不会溢出 | 已完成，可复现 |
| 14 | ADC 原始码怎么变成 Q20 电压、电流和温度 | 已完成，可复现 |
| 15 | Q20 duty 怎么变成中心对齐 PWM 比较值 | 已完成，可复现 |
| 16 | 5 us 控制中断里 ADC、控制器和 PWM 应该按什么顺序执行 | 已完成，可复现 |
| 17 | 哪些代码放 5 us 中断，哪些放后台，HAL 接口怎么拆 | 已完成，可复现 |
| 18 | 如何把控制固件交叉编译成 Cortex-M4F 的 ELF 和 BIN | 已完成，可复现 |
| 19 | 如何用 GitHub Actions 持续回归第 11～18 章 | 已完成，可复现 |
| 20 | 如何完成低压硬件验收并决定能否发布 v1.0 | 验收包已完成；硬件 BLOCKED |

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
| Simulink 波形脚本 | `scripts/export_simulink_discrete_pi_waveforms.m` |
| Simulink 原始数据 | `waveforms/04-simulink-discrete-pi-control-trace.csv` |
| Simulink 指标汇总 | `waveforms/04-simulink-discrete-pi-control-summary.csv` |
| Simulink 主波形 | `waveforms/04-simulink-*.png` |
| Python 对照脚本 | `scripts/export_discrete_pi_control.py` |
| Python 对照数据 | `waveforms/04-discrete-pi-control-*.csv` |
| Python 对照波形 | `waveforms/04-p-only-vs-pi-vin-step.png`、`waveforms/04-pi-*.png` |

第五章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/05-duty-limit-anti-windup.md` |
| 复现说明 | `docs/05-duty-limit-anti-windup-reproduce.md` |
| MATLAB 主仿真脚本 | `scripts/export_matlab_duty_limit_anti_windup_waveforms.m` |
| Simulink 逻辑截图脚本 | `scripts/export_simulink_duty_limit_anti_windup_snapshot.m` |
| Simulink 逻辑模型 | `models/simulink/buck_duty_limit_anti_windup_logic.slx` |
| Simulink 逻辑截图 | `assets/screenshots/05-simulink-duty-limit-anti-windup-logic.png` |
| MATLAB 原始数据 | `waveforms/05-matlab-duty-limit-anti-windup-trace.csv` |
| MATLAB 指标汇总 | `waveforms/05-matlab-duty-limit-anti-windup-summary.csv` |
| MATLAB 主波形 | `waveforms/05-matlab-*.png` |

第六章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/06-soft-start.md` |
| 复现说明 | `docs/06-soft-start-reproduce.md` |
| MATLAB 主仿真脚本 | `scripts/export_matlab_soft_start_waveforms.m` |
| Simulink 逻辑截图脚本 | `scripts/export_simulink_soft_start_snapshot.m` |
| Simulink 逻辑模型 | `models/simulink/buck_soft_start_logic.slx` |
| Simulink 逻辑截图 | `assets/screenshots/06-simulink-soft-start-logic.png` |
| MATLAB 原始数据 | `waveforms/06-matlab-soft-start-trace.csv` |
| MATLAB 指标汇总 | `waveforms/06-matlab-soft-start-summary.csv` |
| MATLAB 斜坡扫描 | `waveforms/06-matlab-soft-start-ramp-sweep.csv` |
| MATLAB 主波形 | `waveforms/06-matlab-soft-start-*.png` |

第七章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/07-protection-state-machine.md` |
| 复现说明 | `docs/07-protection-state-machine-reproduce.md` |
| MATLAB 故障注入脚本 | `scripts/export_matlab_protection_state_machine_waveforms.m` |
| Simulink 结构截图脚本 | `scripts/export_simulink_protection_state_machine_snapshot.m` |
| Simulink 结构模型 | `models/simulink/buck_protection_state_machine_logic.slx` |
| Simulink 结构截图 | `assets/screenshots/07-simulink-protection-state-machine-logic.png` |
| MATLAB 原始数据 | `waveforms/07-matlab-protection-state-machine-trace.csv`、`waveforms/07-matlab-protection-clear-while-fault-trace.csv` |
| MATLAB 优先级数据 | `waveforms/07-matlab-protection-priority-cases.csv` |
| MATLAB 指标汇总 | `waveforms/07-matlab-protection-state-machine-summary.csv` |
| MATLAB 主波形 | `waveforms/07-matlab-protection-*.png` |

第八章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/08-load-transient.md` |
| 复现说明 | `docs/08-load-transient-reproduce.md` |
| MATLAB 负载阶跃脚本 | `scripts/export_matlab_load_transient_waveforms.m` |
| Simulink 测试台截图脚本 | `scripts/export_simulink_load_transient_snapshot.m` |
| Simulink 测试台模型 | `models/simulink/buck_load_transient_testbench.slx` |
| Simulink 测试台截图 | `assets/screenshots/08-simulink-load-transient-testbench.png` |
| MATLAB 原始数据 | `waveforms/08-matlab-load-transient-trace.csv` |
| MATLAB 指标汇总 | `waveforms/08-matlab-load-transient-summary.csv` |
| MATLAB 主波形 | `waveforms/08-matlab-load-transient-*.png` |

第九章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/09-adc-noise-duty-jitter.md` |
| 复现说明 | `docs/09-adc-noise-duty-jitter-reproduce.md` |
| MATLAB ADC 噪声脚本 | `scripts/export_matlab_adc_noise_duty_jitter_waveforms.m` |
| Simulink 采样链路截图脚本 | `scripts/export_simulink_adc_noise_duty_jitter_snapshot.m` |
| Simulink 采样链路模型 | `models/simulink/buck_adc_noise_duty_jitter_logic.slx` |
| Simulink 采样链路截图 | `assets/screenshots/09-simulink-adc-noise-duty-jitter-logic.png` |
| MATLAB 原始数据 | `waveforms/09-matlab-adc-noise-duty-jitter-trace.csv` |
| MATLAB 指标汇总 | `waveforms/09-matlab-adc-noise-duty-jitter-summary.csv` |
| MATLAB 主波形 | `waveforms/09-matlab-adc-noise-*.png` |

第十章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/10-controller-to-c.md` |
| 复现说明 | `docs/10-controller-to-c-reproduce.md` |
| C 风格控制器头文件 | `src/digital_power_control.h` |
| C 风格控制器实现 | `src/digital_power_control.c` |
| Python 场景测试脚本 | `scripts/export_controller_c_style_tests.py` |
| 测试报告 | `reports/10-controller-c-style-test-report.md` |
| 原始数据 | `waveforms/10-controller-c-style-trace.csv` |
| 指标汇总 | `waveforms/10-controller-c-style-summary.csv` |
| 正文图表 | `waveforms/10-controller-c-style-*.png` |

第十一章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/11-host-build-test-gate.md` |
| 复现说明 | `docs/11-host-build-test-gate-reproduce.md` |
| 电脑端 C 测试 | `tests/test_digital_power_control_host.c` |
| 构建测试脚本 | `scripts/run_host_build_tests.py` |
| 检查汇总 | `reports/11-host-build-summary.csv` |
| 测试报告 | `reports/11-host-build-test-report.md` |
| 检查结果图 | `waveforms/11-host-build-gate.png` |

第十二章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/12-c-python-parity.md` |
| 复现说明 | `docs/12-c-python-parity-reproduce.md` |
| C 回放程序 | `tests/replay_digital_power_control.c` |
| Python/C 对照脚本 | `scripts/run_c_python_parity.py` |
| 指标汇总 | `waveforms/12-c-python-parity-summary.csv` |
| 抽样数据 | `waveforms/12-c-python-parity-samples.csv` |
| 测试报告 | `reports/12-c-python-parity-report.md` |
| 正文图表 | `waveforms/12-c-python-parity-*.png` |

第十三章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/13-fixed-point-controller.md` |
| 复现说明 | `docs/13-fixed-point-controller-reproduce.md` |
| Q20 定点控制器 | `src/digital_power_control_fixed.c`、`src/digital_power_control_fixed.h` |
| 定点边界测试 | `tests/test_digital_power_control_fixed.c` |
| 双实现回放入口 | `tests/replay_digital_power_control_fixed.c` |
| 自动对照脚本 | `scripts/run_fixed_point_parity.py` |
| 测试报告 | `reports/13-fixed-point-parity-report.md` |
| 指标与格式数据 | `waveforms/13-fixed-point-*.csv` |
| 正文图表 | `waveforms/13-fixed-point-*.png` |

第十四章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/14-adc-to-q20-mapping.md` |
| 复现说明 | `docs/14-adc-to-q20-mapping-reproduce.md` |
| ADC 映射源码 | `src/digital_power_adc_map.c`、`src/digital_power_adc_map.h` |
| C 单元测试 | `tests/test_digital_power_adc_map.c` |
| C 回放入口 | `tests/replay_digital_power_adc_map.c` |
| 自动化脚本 | `scripts/run_adc_mapping_tests.py` |
| 测试报告 | `reports/14-adc-mapping-report.md` |
| 数据与图表 | `waveforms/14-adc-*.csv`、`waveforms/14-adc-*.png` |

第十五章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/15-pwm-timer-mapping.md` |
| 复现说明 | `docs/15-pwm-timer-mapping-reproduce.md` |
| PWM 映射源码 | `src/digital_power_pwm_map.c`、`src/digital_power_pwm_map.h` |
| C 单元测试 | `tests/test_digital_power_pwm_map.c` |
| C 回放入口 | `tests/replay_digital_power_pwm_map.c` |
| 自动化脚本 | `scripts/run_pwm_mapping_tests.py` |
| 测试报告 | `reports/15-pwm-mapping-report.md` |
| 数据与图表 | `waveforms/15-pwm-*.csv`、`waveforms/15-pwm-*.png` |

第十六章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/16-control-isr-timing.md` |
| 复现说明 | `docs/16-control-isr-timing-reproduce.md` |
| ISR 编排源码 | `src/digital_power_control_isr.c`、`src/digital_power_control_isr.h` |
| 顺序单元测试 | `tests/test_digital_power_control_isr.c` |
| 六周期回放入口 | `tests/replay_digital_power_control_isr.c` |
| 主机基准入口 | `tests/benchmark_digital_power_control_isr.c` |
| 自动化脚本 | `scripts/run_isr_timing_tests.py` |
| 测试报告 | `reports/16-isr-timing-report.md` |
| 数据与图表 | `waveforms/16-isr-*.csv`、`waveforms/16-isr-*.png` |

第十七章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/17-firmware-layering-hal.md` |
| 复现说明 | `docs/17-firmware-layering-hal-reproduce.md` |
| 固件分层源码 | `src/digital_power_firmware.c`、`src/digital_power_firmware.h` |
| 假 HAL | `tests/fake_digital_power_hal.c`、`tests/fake_digital_power_hal.h` |
| C 单元测试 | `tests/test_digital_power_firmware.c` |
| 事件回放入口 | `tests/replay_digital_power_firmware.c` |
| 自动化脚本 | `scripts/run_firmware_layering_tests.py` |
| 测试报告 | `reports/17-firmware-layering-report.md` |
| 数据与图表 | `waveforms/17-*.csv`、`waveforms/17-*.png` |

第十八章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/18-cortex-m4f-target-build.md` |
| 复现说明 | `docs/18-cortex-m4f-target-build-reproduce.md` |
| 启动文件与链接脚本 | `target/cortex-m4f/startup_cortex_m4f.c`、`target/cortex-m4f/linker.ld` |
| 目标入口与 HAL 寄存器模型 | `target/cortex-m4f/firmware_entry.c` |
| 构建/审计脚本 | `scripts/build_cortex_m4f_firmware.py` |
| 发布映像 | `firmware/cortex-m4f/digital_power_cortex_m4f.elf`、`.bin` |
| map 与反汇编 | `firmware/cortex-m4f/digital_power_cortex_m4f.map`、`.lst` |
| 测试报告 | `reports/18-target-build-report.md` |
| 数据与图表 | `waveforms/18-*.csv`、`waveforms/18-*.png` |

第十九章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/19-ci-full-regression.md` |
| 复现说明 | `docs/19-ci-full-regression-reproduce.md` |
| 仓库质量门禁 | `scripts/check_repository_quality.py` |
| 全回归入口 | `scripts/run_full_regression.py` |
| GitHub Actions | `.github/workflows/firmware-regression.yml` |
| 测试报告 | `reports/19-full-regression-report.md` |
| 数据与图表 | `waveforms/19-*.csv`、`waveforms/19-*.png` |

第二十章对应的核心文件：

| 类型 | 文件 |
| --- | --- |
| 教程文章 | `blog/20-low-voltage-hardware-acceptance.md` |
| 复现说明 | `docs/20-low-voltage-hardware-acceptance-reproduce.md` |
| 验收说明与 test plan | `hardware/acceptance/README.md`、`hardware/acceptance/test-plan.csv` |
| 本地设备/测量模板 | `hardware/acceptance/*-template.csv` |
| 自动判定脚本 | `scripts/run_hardware_acceptance.py` |
| 发布门禁 | `RELEASE_READINESS.md` |
| 当前报告 | `reports/20-hardware-acceptance-report.md` |
| 当前数据与图表 | `waveforms/20-*.csv`、`waveforms/20-*.png` |

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

第 4 章的 Simulink 模型截图生成运行：

```powershell
matlab -batch "run('scripts/export_simulink_discrete_pi_snapshot.m'); exit"
```

第 4 章的 Simulink 主波形导出运行：

```powershell
matlab -batch "run('scripts/export_simulink_discrete_pi_waveforms.m'); exit"
```

第 4 章的 Python 离散 PI 对照脚本运行：

```powershell
python scripts\export_discrete_pi_control.py
```

第 4 章不需要启动 PLECS RPC。该章重点验证离散 PI 控制器的数据流、采样周期、积分项和 duty 更新；正文主波形来自 Simulink 模型 `Scope mux` 导出的仿真数据，开关级波形仍在 PLECS 章节中验证。

第 5 章的 Simulink 逻辑截图生成运行：

```powershell
matlab -batch "run('scripts/export_simulink_duty_limit_anti_windup_snapshot.m'); exit"
```

第 5 章的 MATLAB 主波形导出运行：

```powershell
matlab -batch "run('scripts/export_matlab_duty_limit_anti_windup_waveforms.m'); exit"
```

第 5 章不需要启动 PLECS RPC。该章重点验证 duty 上下限、`duty_raw`/`duty_cmd` 分离、积分项 windup 和条件积分 anti-windup；正文主波形来自 MATLAB 离散平均模型导出的数据，开关级波形仍在 PLECS 章节中验证。

第 6 章的 Simulink 逻辑截图生成运行：

```powershell
matlab -batch "run('scripts/export_simulink_soft_start_snapshot.m'); exit"
```

第 6 章的 MATLAB 主波形导出运行：

```powershell
matlab -batch "run('scripts/export_matlab_soft_start_waveforms.m'); exit"
```

第 6 章不需要启动 PLECS RPC。该章重点验证软启动参考值斜坡、启动过冲、电感电流峰值、duty 饱和和斜坡时间取舍；正文主波形来自 MATLAB 离散平均模型导出的数据，开关级波形仍在 PLECS 章节中验证。

第 7 章的 Simulink 结构截图生成运行：

```powershell
matlab -batch "run('scripts/export_simulink_protection_state_machine_snapshot.m'); exit"
```

第 7 章的 MATLAB 故障注入波形导出运行：

```powershell
matlab -batch "run('scripts/export_matlab_protection_state_machine_waveforms.m'); exit"
```

第 7 章不需要启动 PLECS RPC。该章重点验证保护检测、故障锁存、PWM 统一关断和故障优先级；正文主波形来自 MATLAB 状态机故障注入模型导出的数据，开关级器件应力仍在 PLECS 章节中验证。

第 8 章的 Simulink 测试台截图生成运行：

```powershell
matlab -batch "run('scripts/export_simulink_load_transient_snapshot.m'); exit"
```

第 8 章的 MATLAB 负载阶跃波形导出运行：

```powershell
matlab -batch "run('scripts/export_matlab_load_transient_waveforms.m'); exit"
```

第 8 章不需要启动 PLECS RPC。该章重点验证负载 50% -> 100% -> 50% 时的输出下陷、过冲、恢复时间和 duty 饱和诊断；正文主波形来自 MATLAB 平均模型导出的数据，开关级器件应力仍在 PLECS 章节中验证。

第 9 章的 Simulink 采样链路截图生成运行：

```powershell
matlab -batch "run('scripts/export_simulink_adc_noise_duty_jitter_snapshot.m'); exit"
```

第 9 章的 MATLAB ADC 噪声和 duty 抖动波形导出运行：

```powershell
matlab -batch "run('scripts/export_matlab_adc_noise_duty_jitter_waveforms.m'); exit"
```

第 9 章不需要启动 PLECS RPC。该章重点验证 ADC 量化和模拟噪声如何进入误差计算，并通过 PI 控制器变成 `duty_raw` / `duty_cmd` 抖动；正文主波形来自 MATLAB 平均模型导出的数据，开关级纹波和硬件 ADC 前端仍需后续验证。

第 10 章的 C 风格控制器场景测试运行：

```powershell
python scripts\export_controller_c_style_tests.py
```

第 10 章不需要启动 PLECS RPC，也不需要 MATLAB/Simulink。该章重点验证仿真控制器迁移到固定周期 C 风格接口后的数据流、状态机、telemetry、软启动、负载突变、OCP 锁存和 UVLO 关断路径；该章不声明完成 MCU 编译、定点化或上板验证。

第 11 章的 C 控制器电脑端编译与单元测试检查运行：

```powershell
python scripts\run_host_build_tests.py
```

第 11 章进入第二季固件工程化。该章先检测本机 C 编译器，再尝试编译 `src/digital_power_control.c` 和 `tests/test_digital_power_control_host.c`，并生成 CSV、PNG 和 Markdown 报告。当前本机已检测到 Zig 0.16.0，电脑端编译和电脑端单元测试均为 PASS。

第 12 章的 Python 参考实现与真实 C 控制器逐周期对照运行：

```powershell
python scripts\run_c_python_parity.py
```

该章复用第 10 章五个场景生成固定逐周期输入，编译并运行真实 C 控制器，再比较 80,400 个控制周期的连续数值和离散状态。当前 55 项指标全部 PASS，状态、故障、PWM 和逻辑标志错位均为 0。

第 13 章的浮点 C 与 Q20 定点 C 对照运行：

```powershell
python scripts\run_fixed_point_parity.py
```

该章比较 Q16、Q20、Q24 的精度与范围，采用有符号 32 位、20 个小数位的统一格式；随后编译定点单元测试和浮点/定点双实现回放程序。当前 4 个定点单元测试和 80,400 周期对照共 74 项指标全部 PASS，正常场景算术溢出和离散行为错位均为 0。

第 14 章的 ADC 原始码值到 Q20 工程量映射运行：

```powershell
python scripts\run_adc_mapping_tests.py
```

该章使用真实编译后的 C 映射层处理 `Vin`、`Vout`、`Iout` 和温度四通道，比较标称前端、元件偏差未校准和写入校准系数三种场景。当前 607 行输入得到 PASS 22 / FAIL 0 / INFO 4，标称与校准误差均低于约一个通道 ADC LSB。

第 15 章的 Q20 duty 到中心对齐 PWM 比较值映射运行：

```powershell
python scripts\run_pwm_mapping_tests.py
```

该章使用真实编译后的 C 映射层验证 72/100/170 MHz 三种定时器分辨率、0%～65% duty 限幅、四舍五入、预装载更新和立即关断。当前 640 行输入得到 PASS 15 / FAIL 0；170 MHz、200 kHz 中心对齐配置为 `ARR=425`、100 ns 死区为 17 counts。

第 16 章的控制 ISR 顺序、预算与主机回归运行：

```powershell
python scripts\run_isr_timing_tests.py
```

该章把 PWM 更新、ADC 映射、Q20 控制和下一周期 PWM 排队放进唯一编排层，验证一周期 compare 延迟、OCP 同周期关断和同步重启。当前 13 项 PASS、0 项 FAIL；5 us 周期分配 3.5 us ISR 目标预算和 1.5 us 余量，4 项主机计时仅标为 INFO。

第 17 章的实时/后台分层与 HAL 适配测试运行：

```powershell
python scripts\run_firmware_layering_tests.py
```

该章用假 HAL 记录 12 个阶段的 34 次真实 C 调用，验证 ISR 只处理更新、ADC、PWM 和立即关断，后台只处理通信与存储，多字段命令和遥测通过短临界区交换。当前 21 项指标全部 PASS。

第 18 章的 Cortex-M4F 交叉构建与映像审计运行：

```powershell
python scripts\build_cortex_m4f_firmware.py
```

该章使用 Zig 0.16.0 真实生成 Cortex-M4F ELF/BIN，并用 pyelftools 和 Capstone 检查入口、向量表、段、符号和 Thumb 指令。当前发布 ELF 为 131652 B、BIN 为 5112 B，13 项 PASS、0 项 FAIL、1 项整数除法助手 INFO。

第 19 章的仓库质量与第 11～18 章全回归运行：

```powershell
python scripts\run_full_regression.py
```

该章先检查公开文件、图片、机器路径、证据包和 Python 语法，再真实运行第二季前八章全部入口。当前 9 个顶层步骤全部 PASS，本机总耗时 27.146 s；GitHub Actions 使用相同入口。

第 20 章的低压硬件验收门禁运行：

```powershell
python scripts\run_hardware_acceptance.py
```

当前第十九章软件回归 PASS；Windows 未检测到开发板、USB 调试探针或串口，完整发布所需设备也没有本地登记，因此结果为 PASS 1 / BLOCKED 18 / FAIL 0，v1.0 保持 BLOCKED。

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
| PI duty 范围 | 约 0.504 - 0.646 |
| 输入阶跃 1% 恢复时间 | 约 2.22ms |
| 负载阶跃 1% 恢复时间 | 约 0.91ms |

第 4 章通过平均模型验证离散 PI 电压环的数据流：采样 Vout、计算误差、更新积分项、输出 duty，再反馈到 Buck 平均功率级。该章故意不加入 duty 限幅和抗积分饱和，相关问题放到第 5 章单独处理。

## 第五章结果

| 指标 | 结果 |
| --- | --- |
| duty 上限 | 0.55 |
| Vin 跌落工况 | 24V -> 20V -> 24V |
| Vin 跌落时维持 12V 所需 duty | 约 0.605 |
| 只加限幅时 integrator 峰值 | 约 0.670 |
| 加 anti-windup 后 integrator 峰值 | 约 0.0176 |
| 只加限幅时 raw duty 峰值 | 约 1.218 |
| 加 anti-windup 后 raw duty 峰值 | 约 0.614 |
| 只加限幅时 Vin 恢复后 Vout 峰值 | 约 14.62V |
| 加 anti-windup 后 Vin 恢复后 Vout 峰值 | 约 13.13V |
| Vin 恢复后退出饱和时间 | 约 2.58ms -> 0.22ms |

第 5 章通过 MATLAB 离散平均模型验证 duty 限幅和 anti-windup 的职责边界：Saturation 限制实际 PWM 输出，anti-windup 限制积分项继续向饱和方向累加。

## 第六章结果

| 指标 | 结果 |
| --- | --- |
| 目标输出 | 12V |
| 对比方式 | 直接 12V 阶跃、2ms 斜坡、5ms 斜坡 |
| 直接 12V 阶跃 Vout 峰值 | 约 18.64V |
| 直接 12V 阶跃电感电流峰值 | 约 28.34A |
| 直接 12V 阶跃 duty 饱和总时长 | 约 0.075ms |
| 2ms 软启动 Vout 峰值 | 约 12.17V |
| 2ms 软启动电感电流峰值 | 约 5.51A |
| 5ms 软启动 Vout 峰值 | 约 12.08V |
| 5ms 软启动电感电流峰值 | 约 5.24A |
| 5ms 软启动电流峰值降低量 | 约 23.10A |
| 5ms 软启动 Vout 过冲降低量 | 约 6.55V |

第 6 章通过 MATLAB 离散平均模型验证软启动参考值路径：软启动不改变最终目标 12V，而是让目标电压以可控斜率进入电压环，从而降低启动过冲和电感电流峰值。

## 第七章结果

| 指标 | 结果 |
| --- | --- |
| 状态机周期 | 50us |
| 故障优先级 | OCP -> OVP -> UVLO -> OTP |
| OCP 阈值 | 6.5A |
| OVP 阈值 | 13.2V |
| UVLO 阈值 | 18V |
| RUN 状态首次 OCP 检测时间 | 8ms |
| PWM 关断延迟 | 0us |
| 锁存故障码 | OCP |
| 清故障进入恢复时间 | 12ms |
| 重新进入 RUN 时间 | 19.05ms |
| OVP 仍存在时 CLEAR_FAULT | 不解除锁存 |

第 7 章通过 MATLAB 故障注入模型验证保护状态机职责边界：保护检测层输出唯一故障码，状态机锁存故障，PWM gate 在非运行态统一关断输出。

## 第八章结果

| 指标 | 结果 |
| --- | --- |
| 负载阶跃 | 50% -> 100% -> 50% |
| 50% 负载电流 | 2.5A |
| 100% 负载电流 | 5A |
| 1% 恢复带宽 | ±0.12V |
| `load_transient_pi` 上跳下陷 | 约 0.87V |
| `load_transient_pi` 上跳 1% 恢复时间 | 约 1.40ms |
| `load_transient_pi` 下跳过冲 | 约 0.93V |
| `load_transient_pi` 下跳 1% 恢复时间 | 约 4.79ms |
| `chapter04_pi` 下跳过冲 | 约 3.56V |
| `chapter04_pi` 下跳恢复 | 30ms 窗口内未恢复 |
| 220uF 电容上跳下陷 | 约 0.61V |
| 220uF 电容下跳过冲 | 约 0.63V |
| duty 上限不足工况重载饱和时间 | 约 6.33ms |

第 8 章通过 MATLAB 平均模型验证负载突变测试方法：负载上跳重点看 Vout 下陷、峰值电感电流和 duty 上限；负载下跳重点看 Vout 过冲、恢复时间和 duty 下限。该章同时用 raw duty、duty cmd 和 saturation flag 区分 PI 参数、电容储能和 duty 限幅问题。

## 第九章结果

| 指标 | 结果 |
| --- | --- |
| ADC 位数 | 12 bit |
| ADC 输出等效满量程 | 16V |
| ADC LSB | 约 3.906mV |
| ADC 模拟噪声 | 15mV RMS |
| `noisy_adc` 测量噪声 RMS | 约 15.18mV |
| `noisy_adc` duty RMS 抖动 | 约 0.000321 |
| `noisy_adc` 等效 PWM RMS 抖动 | 约 1.60ns |
| 4 点滑动平均 duty RMS 抖动 | 约 0.000197 |
| 4 点滑动平均抖动降低比例 | 约 38.6% |
| 4 点滑动平均近似延迟 | 约 7.5us |
| 一阶 IIR duty RMS 抖动 | 约 0.000227 |
| 一阶 IIR 抖动降低比例 | 约 29.3% |
| 一阶 IIR 近似延迟 | 约 15us |

第 9 章通过 MATLAB 平均模型验证 ADC 噪声到 duty 抖动的数据流：采样噪声进入 `Vout_meas`，误差计算把噪声变成 error 抖动，PI 控制器再把 error 抖动变成 duty 指令抖动。该章同时用 4 点滑动平均和一阶 IIR 对比滤波收益和反馈延迟。

## 第十章结果

| 指标 | 结果 |
| --- | --- |
| 控制周期 | 5us |
| 目标输出 | 12V |
| 软启动斜率 | 300V/s |
| PI 参数 | Kp = 0.05，Ki = 80 |
| duty 限幅 | 0 - 0.65 |
| `steady_12v` 56ms 后 Vout 均值 | 12.00V |
| `soft_start_40ms` Vout 峰值 | 12.00V |
| `soft_start_40ms` 首次进入 RUN | 40.00ms |
| `load_step_50_100_50` 上跳下陷 | 约 0.744V |
| `load_step_50_100_50` 下跳过冲 | 约 0.783V |
| `load_step_50_100_50` 上跳恢复时间 | 约 1.455ms |
| `load_step_50_100_50` 下跳恢复时间 | 约 9.50ms |
| `ocp_latch_clear` 首次 OCP 锁存时间 | 52.00ms |
| `uvlo_blocks_pwm` PWM 关断 | PASS |
| 测试报告 FAIL 行数 | 0 |

第 10 章通过 Python 平均模型测试台验证 C 风格控制器的数据流：`Config` 保存可调参数，`Context` 保存跨周期状态，`Input` 接收采样输入，`Output` 输出 duty、状态、故障和 telemetry。该章完成的是控制器接口和算法顺序验证，MCU 编译、定点化、寄存器驱动、ADC/PWM 同步和 HIL 放到后续固件工程阶段。

## 第十一章结果

| 检查项 | 当前结果 |
| --- | --- |
| `toolchain` | PASS |
| `build` | PASS |
| `unit_tests` | PASS |
| `report` | PASS |
| 编译器检测 | Zig 0.16.0 |
| 脚本输出 | `summary,pass=4,blocked=0,skipped=0,fail=0` |

第 11 章建立第二季入口检查：先证明电脑端工具链、编译命令、单元测试和报告链路是否成立。当前结论只覆盖电脑端编译和电脑端单元测试，不等于目标 MCU 工具链、定点化、HAL、ISR、HIL 或实机闭环已经完成。

## 第十二章结果

| 检查项 | 当前结果 |
| --- | --- |
| 对照场景 | 5 |
| 逐周期比较行数 | 80,400 |
| 指标结果 | PASS 55 / FAIL 0 |
| 最大 `duty_cmd` 误差 | `5.12136e-05` |
| 最大 `vref_cmd_v` 误差 | `0.0005587 V` |
| 状态、故障、PWM 和逻辑标志错位 | 0 |
| 电脑端 C 编译器 | Zig 0.16.0 |

第 12 章把第 10 章 Python 参考实现产生的相同输入送给编译后的 C 控制器，验证五个场景中的参数、执行顺序、状态迁移和输出行为没有因改写成 C 而发生可观测偏差。该结论仍不覆盖目标 MCU、定点化、外设时序或硬件闭环。

## 第十三章结果

| 检查项 | 当前结果 |
| --- | --- |
| 定点格式 | 有符号 32 位，20 个小数位 |
| 缩放因子 | 1,048,576 |
| 定点单元测试 | 4/4 PASS |
| 对照场景与周期 | 5 / 80,400 |
| 指标结果 | PASS 74 / FAIL 0 |
| 最大 `duty_cmd` 误差 | `7.06908e-05` |
| 最大 `vref_cmd_v` 误差 | `0.000478795 V` |
| 最大积分器误差 | `7.06213e-05` |
| 离散行为错位 | 0 |
| 正常回放算术溢出 | 0 |
| 最大 raw 正量程占用 | `4.88281%` |

第 13 章建立了定点格式选择、统一舍入与饱和、溢出观测和浮点基准回放链路。当前结果覆盖电脑端 Q20 控制算法，不覆盖 ADC 原始码值、PWM 寄存器、目标 MCU 执行时间或硬件闭环。

## 第十四章结果

| 检查项 | 当前结果 |
| --- | --- |
| ADC | 12 bit，3.3 V 参考 |
| C 映射数据行 | 607 |
| 指标结果 | PASS 22 / FAIL 0 / INFO 4 |
| 标称 `Vin/Vout/Iout/Temp` 最大误差 | 0.003708 V / 0.001951 V / 0.001008 A / 0.040300°C |
| 校准后 `Vin/Vout/Iout/Temp` 最大误差 | 0.003742 V / 0.001956 V / 0.000963 A / 0.040606°C |
| 校准后/未校准最大误差比例 | 0.67%～5.57% |
| 映射整数溢出 | 0 |

第 14 章建立 ADC code、参考电压、分压比、增益、零点偏置、物理范围和 Q20 输出之间的唯一映射层。元件偏差场景是合成数据；真实硬件校准仍需实物测量。

## 第十五章结果

| 检查项 | 当前结果 |
| --- | --- |
| 定时器/PWM | 170 MHz / 200 kHz，中心对齐 |
| ARR | 425 |
| duty 上限及比较值 | 65% / 276 counts |
| 100 ns 死区计数 | 17 counts |
| C 映射数据行 | 640 |
| 指标结果 | PASS 15 / FAIL 0 |
| 170 MHz 最大 duty 误差 | 0.00117691 |
| 预装载更新 / 立即关断 | PASS / PASS |
| 映射整数溢出 | 0 |

第 15 章建立 Q20 duty、软件限幅、整数比较值、预装载更新和保护立即关断之间的唯一输出映射层。结果覆盖通用中心对齐 PWM 软件语义，具体 MCU 寄存器编码和门极波形仍需目标适配与实测。

## 第十六章结果

| 检查项 | 当前结果 |
| --- | --- |
| 控制周期 | 5 us |
| ISR 目标预算 / 余量 | 3.5 us / 1.5 us |
| 六周期集成回放 | PASS |
| compare 一周期延迟 | PASS |
| OCP 同周期关闭 active enable | PASS |
| 清故障同步重启 | PASS |
| 正常映射钳位 / 溢出 | 0 / 0 |
| 指标结果 | PASS 13 / FAIL 0 / INFO 4 |
| 当前主机 P50 / P99 | 44.71 ns / 60.02 ns（INFO） |

第 16 章固定更新事件、ADC、控制器和 PWM 的调用顺序，并建立目标 MCU 的时间预算验收线。Windows 主机基准只用于代码回归，不作为目标 MCU 5 us 截止时间证据。

## 第十七章结果

| 检查项 | 当前结果 |
| --- | --- |
| 回放阶段 / HAL 事件 | 12 / 34 |
| ISR 实时动作边界 | PASS |
| 后台通信/存储边界 | PASS |
| OCP 先关断后写预装载 | PASS |
| ADC 失败失效安全顺序 | PASS |
| disable 命令下一 ISR 提交 | PASS |
| restart 等待 PWM 更新 | PASS |
| 遥测快照短临界区复制 | PASS |
| 指标结果 | PASS 21 / FAIL 0 |

第 17 章建立平台无关固件编排层和 HAL 接口。结果覆盖调用顺序、任务归属和共享数据边界，不包含具体 MCU 寄存器、DMA、NVIC 或 Flash 驱动。

## 第十八章结果

| 检查项 | 当前结果 |
| --- | --- |
| 目标 | thumb-freestanding-eabihf / Cortex-M4 |
| 发布 ELF / BIN | 131652 B / 5112 B |
| ELF 入口 | `0x08000F85`，匹配 `Reset_Handler` |
| 向量表 | `0x08000000`，68 B |
| Flash / RAM+4KB栈 | 5112 B / 4376 B |
| 必需符号 / 未解析符号 | 4 / 0 |
| 浮点助手 / VFP 指令 | 0 / 0 |
| 64 位整数除法助手 | 2，INFO |
| 指标结果 | PASS 13 / FAIL 0 / INFO 1 |

第 18 章证明平台无关固件可以生成可审计的 Cortex-M4F 裸机映像。目标 HAL 仍使用可编译寄存器模型，不包含具体 STM32G4 外设初始化或实物执行时间证据。

## 第十九章结果

| 检查项 | 当前结果 |
| --- | --- |
| 仓库质量门禁 | PASS 9 / FAIL 0 |
| 公开文本/数据扫描 | PASS |
| 博客本地图片检查 | PASS |
| 全回归顶层步骤 | PASS 9 / FAIL 0 |
| 第 12/13 章回放 | 80400 / 80400 周期 |
| 第 17 章 HAL 事件 | 34 |
| 第 18 章目标构建 | PASS 13 / INFO 1 |
| 本机总耗时 | 27.146 s |

第 19 章把仓库质量和第 11～18 章技术入口统一到 `scripts/run_full_regression.py`，GitHub Actions 只负责在干净环境调用该入口并上传证据。该结果仍不包含 HIL 或实物闭环。

## 第二十章结果

| 检查项 | 当前结果 |
| --- | --- |
| 第十九章软件回归 | PASS |
| 调试探针 / 开发板 / 串口 | 0 / 0 / 0 |
| 完整发布所需设备 | 0/9 |
| 低压硬件验收项 | PASS 1 / BLOCKED 18 / FAIL 0 |
| v1.0 门禁 | BLOCKED |
| v1.0 标签 | 未创建 |

第 20 章已经固化设备清单、19 项 test plan、测量模板、证据规则和自动范围判定。当前没有板级 HAL 与硬件测量事实，软件基线可以继续使用，但不能声称完成 HIL、实物闭环或 v1.0 发布。

## 仓库结构

```text
assets/             教程图片和仿真工具截图
blog/               已完成教程
docs/               已完成章节的复现说明
models/plecs/       PLECS 模型
models/simulink/    Simulink 平均模型
reports/            场景测试报告
scripts/            可复现脚本
src/                浮点/定点控制器、ADC 与 PWM 映射源码
target/cortex-m4f/  Cortex-M4F 启动、链接和目标入口源码
firmware/cortex-m4f/ 已生成的 ELF、BIN、map 和反汇编
.github/workflows/  GitHub Actions 持续回归入口
hardware/acceptance/ 低压硬件 test plan、模板和公开证据目录
tests/              电脑端单元测试、边界测试和 C 回放入口
waveforms/          仿真原始数据、指标和波形图
```

当前仓库只展示已完成内容，未完成主题不会提前放入公开目录。

## 后续计划

第二季教程与软件工程包已经推进到第 20 章。下一次推进只处理真实硬件验收：接入 Cortex-M4F 开发板后先替换目标 HAL 寄存器模型，再连接 24 V/12 V/5 A 功率级和台架仪器补齐 17 项硬件测量；全部 PASS 后审核 v1.0 标签。

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
