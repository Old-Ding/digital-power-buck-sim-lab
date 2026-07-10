# 第 19 章复现说明：GitHub Actions 与第 11～18 章全回归

## 目标

在本地或 GitHub Actions 的干净 Windows 环境中，依次运行仓库质量检查和第 11～18 章真实入口，生成统一退出码、CSV、耗时图和 Markdown 报告。

## 环境

- Windows 11 或 GitHub `windows-latest`
- Python 3.13/3.14
- Zig 0.16.0
- matplotlib
- pyelftools
- Capstone

安装 Python 依赖：

```powershell
python -m pip install matplotlib pyelftools capstone
```

## 最短命令

```powershell
python scripts\run_full_regression.py
```

当前摘要：

```text
summary,pass=9,fail=0,steps=9,duration_s=25.837
```

运行时间会随电脑和 CI runner 改变；PASS/FAIL 数量和子步骤技术指标才是门禁。

## 只运行仓库质量门禁

```powershell
python scripts\check_repository_quality.py
```

预期：

```text
summary,pass=9,fail=0,checks=9
```

生成 `waveforms/19-repository-quality.csv`。

## 全回归步骤

| 顺序 | 步骤 | 直接复现命令 |
| ---: | --- | --- |
| 1 | 仓库质量 | `python scripts/check_repository_quality.py` |
| 2 | 第 11 章主机构建 | `python scripts/run_host_build_tests.py` |
| 3 | 第 12 章 C/Python 对照 | `python scripts/run_c_python_parity.py` |
| 4 | 第 13 章 Q20 定点对照 | `python scripts/run_fixed_point_parity.py` |
| 5 | 第 14 章 ADC 映射 | `python scripts/run_adc_mapping_tests.py` |
| 6 | 第 15 章 PWM 映射 | `python scripts/run_pwm_mapping_tests.py` |
| 7 | 第 16 章 ISR 顺序与预算 | `python scripts/run_isr_timing_tests.py` |
| 8 | 第 17 章固件分层与 HAL | `python scripts/run_firmware_layering_tests.py` |
| 9 | 第 18 章 Cortex-M4F 构建 | `python scripts/build_cortex_m4f_firmware.py` |

聚合器在某一步失败后仍继续后续步骤，最后只要存在一个 FAIL 就返回退出码 1。

## 当前本机结果

| 步骤 | 状态 | 时间/s |
| --- | --- | ---: |
| 仓库质量 | PASS | 0.934 |
| 第 11 章 | PASS | 1.432 |
| 第 12 章 | PASS | 4.890 |
| 第 13 章 | PASS | 6.186 |
| 第 14 章 | PASS | 2.676 |
| 第 15 章 | PASS | 2.287 |
| 第 16 章 | PASS | 2.829 |
| 第 17 章 | PASS | 2.323 |
| 第 18 章 | PASS | 2.280 |
| 合计 | 9 PASS / 0 FAIL | 25.837 |

精确值以 `waveforms/19-full-regression.csv` 为准。

## GitHub Actions

工作流：`.github/workflows/firmware-regression.yml`。

触发条件：

- push 到 `master`
- Pull Request
- 手动 `workflow_dispatch`

环境与动作：

```text
windows-latest
Python 3.13
Zig 0.16.0
pip install matplotlib pyelftools capstone
python scripts\run_full_regression.py
upload reports/19-* and waveforms/19-*
```

## 生成文件

| 文件 | 内容 |
| --- | --- |
| `waveforms/19-repository-quality.csv` | 9 项仓库质量结果 |
| `waveforms/19-full-regression.csv` | 9 个顶层步骤、退出码、耗时、摘要和命令 |
| `waveforms/19-full-regression-duration.png` | 同次运行的步骤耗时 |
| `reports/19-full-regression-report.md` | 全回归报告 |

## 常见失败

### `public_text_has_no_machine_paths` 失败

查看命中的生成文件，修复产生绝对路径的脚本，再重新生成证据。不要只手工删除报告中的路径。

### `chapters_11_18_have_complete_packages` 失败

缺少教程、复现说明、脚本、CSV、PNG 或报告之一。完成对应章节证据包后再加入公开目录。

### 第 12/13 章数值对照失败

直接运行失败命令并查看对应报告中的首个场景/字段误差。不要在第 19 章提高容差。

### 第 16 章主机 INFO 数值变化

P50/P99/最大值变化不会单独导致失败。确认顺序与预算 PASS 后，把主机数据作为当前机器回归基线解读。

### 第 18 章缺少 pyelftools 或 Capstone

运行：

```powershell
python -m pip install pyelftools capstone
```

### GitHub Actions 超时

先看哪个步骤最后开始但没有结束，再在本地单独运行。工作流的 30 分钟超时用于防卡死，不是技术性能门限。

### CI 通过但工作区有未提交变化

CI 只检查提交内容。先确认本地 `git status`，再提交并推送需要验证的源码、脚本和证据文件。
