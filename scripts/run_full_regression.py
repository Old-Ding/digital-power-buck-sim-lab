from __future__ import annotations

import csv
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
WAVE_DIR = ROOT / "waveforms"
REPORT_DIR = ROOT / "reports"

STEPS = [
    ("repository_quality", "仓库质量门禁", [sys.executable, "scripts/check_repository_quality.py"]),
    ("chapter11_host_build", "第 11 章主机编译与单元测试", [sys.executable, "scripts/run_host_build_tests.py"]),
    ("chapter12_c_python", "第 12 章 C/Python 逐周期对照", [sys.executable, "scripts/run_c_python_parity.py"]),
    ("chapter13_fixed_point", "第 13 章 Q20 定点对照", [sys.executable, "scripts/run_fixed_point_parity.py"]),
    ("chapter14_adc_map", "第 14 章 ADC 映射", [sys.executable, "scripts/run_adc_mapping_tests.py"]),
    ("chapter15_pwm_map", "第 15 章 PWM 映射", [sys.executable, "scripts/run_pwm_mapping_tests.py"]),
    ("chapter16_isr", "第 16 章 ISR 顺序与预算", [sys.executable, "scripts/run_isr_timing_tests.py"]),
    ("chapter17_layering", "第 17 章固件分层与 HAL", [sys.executable, "scripts/run_firmware_layering_tests.py"]),
    ("chapter18_target", "第 18 章 Cortex-M4F 构建", [sys.executable, "scripts/build_cortex_m4f_firmware.py"]),
]


def configure_console_encoding() -> None:
    # GitHub Windows runner 可能继承 cp1252；统一输出 UTF-8，避免中文步骤名在测试前失败。
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run_step(step_id: str, label: str, command: list[str]) -> dict[str, object]:
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    start = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
    )
    duration = time.perf_counter() - start
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    summary_lines = [line for line in output.splitlines() if line.startswith("summary,")]
    summary = summary_lines[-1] if summary_lines else "no summary line"
    print(f"\n=== {label} ===")
    print(output)
    public_command = ["python" if Path(command[0]).resolve() == Path(sys.executable).resolve() else command[0], *command[1:]]
    return {
        "step": step_id,
        "label": label,
        "status": "PASS" if completed.returncode == 0 else "FAIL",
        "exit_code": completed.returncode,
        "duration_s": round(duration, 3),
        "summary": summary,
        "command": " ".join(public_command),
    }


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot_durations(path: Path, rows: list[dict[str, object]]) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    ordered = list(reversed(rows))
    labels = [str(row["label"]) for row in ordered]
    durations = [float(row["duration_s"]) for row in ordered]
    colors = ["#0f766e" if row["status"] == "PASS" else "#be123c" for row in ordered]
    fig, ax = plt.subplots(figsize=(11.5, 6.8))
    bars = ax.barh(labels, durations, color=colors)
    maximum = max(durations) if durations else 1.0
    for bar, row in zip(bars, ordered):
        ax.text(bar.get_width() + maximum * 0.015, bar.get_y() + bar.get_height() / 2.0, f"{row['duration_s']:.3f}s  {row['status']}", va="center", fontsize=8)
    ax.set_xlabel("本机单步运行时间 / s")
    ax.set_title("每一行都来自同一次完整回归运行", loc="left")
    ax.grid(True, axis="x", alpha=0.25)
    fig.suptitle("第 19 章：仓库质量与第 11～18 章持续回归", fontsize=15)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_report(path: Path, rows: list[dict[str, object]]) -> None:
    passes = sum(row["status"] == "PASS" for row in rows)
    fails = sum(row["status"] == "FAIL" for row in rows)
    total_duration = sum(float(row["duration_s"]) for row in rows)
    lines = [
        "# 第 19 章报告：仓库质量与第 11～18 章全链路回归",
        "",
        "本报告由 `scripts/run_full_regression.py` 生成。每个步骤调用对应章节的真实编译、回放、映像或质量检查入口。",
        "",
        "## 摘要",
        "",
        f"- Python：`{platform.python_version()}`",
        f"- 系统：`{platform.system()} {platform.release()}`",
        f"- 步骤：PASS {passes} / FAIL {fails}",
        f"- 本机总运行时间：{total_duration:.3f} s",
        "",
        "## 步骤",
        "",
        "| 步骤 | 状态 | 退出码 | 时间/s | 子步骤摘要 |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(f"| `{row['step']}` | {row['status']} | {row['exit_code']} | {float(row['duration_s']):.3f} | `{row['summary']}` |")
    lines.extend([
        "",
        "## 判定边界",
        "",
        "全回归可以证明仓库中的主机测试、数值对照、定点/映射检查、固件分层和 Cortex-M4F 构建在当前提交上同时成立。它不连接开发板、电源、电子负载或示波器，因此不能替代第 20 章的 HIL/低压实物验收。",
        "",
    ])
    text = "\n".join(lines).replace("\r\n", "\n").replace("\r", "\n")
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(text.replace("\n", "\r\n"))


def main() -> int:
    configure_console_encoding()
    WAVE_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    rows = [run_step(step_id, label, command) for step_id, label, command in STEPS]
    write_rows(WAVE_DIR / "19-full-regression.csv", rows)
    plot_durations(WAVE_DIR / "19-full-regression-duration.png", rows)
    write_report(REPORT_DIR / "19-full-regression-report.md", rows)
    passes = sum(row["status"] == "PASS" for row in rows)
    fails = sum(row["status"] == "FAIL" for row in rows)
    total_duration = sum(float(row["duration_s"]) for row in rows)
    print("\n已生成第 19 章全链路回归 CSV、图表和报告。")
    print(f"summary,pass={passes},fail={fails},steps={len(rows)},duration_s={total_duration:.3f}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
