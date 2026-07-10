from __future__ import annotations

import argparse
import csv
import math
import os
from pathlib import Path

import matplotlib.pyplot as plt

from run_host_build_tests import compiler_family, compiler_version, find_compiler, run_command


ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "artifacts" / "host-build" / "chapter15"
WAVE_DIR = ROOT / "waveforms"
REPORT_DIR = ROOT / "reports"
Q20_SCALE = 1 << 20
DUTY_MAX = 0.65
DUTY_MAX_Q20 = round(DUTY_MAX * Q20_SCALE)

TIMER_PROFILES = [
    {"case": "resolution_72mhz", "timer_clock_hz": 72_000_000, "period_counts": 180, "auto_reload": 180, "deadtime_counts": 7},
    {"case": "resolution_100mhz", "timer_clock_hz": 100_000_000, "period_counts": 250, "auto_reload": 250, "deadtime_counts": 10},
    {"case": "resolution_170mhz", "timer_clock_hz": 170_000_000, "period_counts": 425, "auto_reload": 425, "deadtime_counts": 17},
]


def duty_q20(value: float) -> int:
    scaled = value * Q20_SCALE
    return math.floor(scaled + 0.5) if scaled >= 0.0 else math.ceil(scaled - 0.5)


def input_row(case_id: str, index: int, reset: int, apply_update: int, duty: float, enable: int, profile: dict[str, int | str]) -> dict[str, object]:
    return {
        "case": case_id,
        "index": index,
        "reset": reset,
        "apply_update": apply_update,
        "requested_duty": duty,
        "pwm_enable": enable,
        "period_counts": profile["period_counts"],
        "auto_reload": profile["auto_reload"],
        "deadtime_counts": profile["deadtime_counts"],
        "duty_max_q20": DUTY_MAX_Q20,
        "requested_duty_q20": duty_q20(duty),
    }


def build_input_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for profile in TIMER_PROFILES:
        for index in range(131):
            duty = DUTY_MAX * index / 130.0
            rows.append(input_row(str(profile["case"]), index, 1, 1, duty, 1, profile))

    profile = TIMER_PROFILES[-1]
    for index in range(241):
        duty = -0.1 + 1.2 * index / 240.0
        rows.append(input_row("duty_clamp_170mhz", index, 1, 1, duty, 1, profile))

    sequence = [
        (1, 0, 0.20, 1),
        (0, 1, 0.20, 1),
        (0, 0, 0.50, 1),
        (0, 1, 0.50, 1),
        (0, 0, 0.50, 0),
        (0, 1, 0.50, 0),
    ]
    for index, (reset, apply_update, duty, enable) in enumerate(sequence):
        rows.append(input_row("shadow_update_sequence", index, reset, apply_update, duty, enable, profile))
    return rows


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_timer_profiles(path: Path) -> None:
    rows = []
    for profile in TIMER_PROFILES:
        period_counts = int(profile["period_counts"])
        timer_clock = int(profile["timer_clock_hz"])
        rows.append({
            **profile,
            "switching_frequency_hz": timer_clock / (2.0 * period_counts),
            "duty_resolution": 1.0 / period_counts,
            "half_count_error": 0.5 / period_counts,
            "deadtime_ns": int(profile["deadtime_counts"]) / timer_clock * 1.0e9,
        })
    write_rows(path, rows)


def compile_command(compiler: str, hint: str, sources: list[Path], output: Path) -> list[str]:
    family = compiler_family(compiler, hint)
    include = ROOT / "src"
    if family == "zig":
        return [compiler, "cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-I", str(include), *map(str, sources), "-o", str(output)]
    if family == "msvc":
        return [compiler, "/nologo", "/W4", "/WX", f"/I{include}", *map(str, sources), f"/Fe:{output}"]
    return [compiler, "-std=c99", "-Wall", "-Wextra", "-Werror", "-I", str(include), *map(str, sources), "-o", str(output)]


def read_output(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", newline="", encoding="utf-8") as file:
        for raw in csv.DictReader(file):
            row: dict[str, object] = {"case": raw["case"], "index": int(raw["index"])}
            for name in ("reset", "apply_update", "pwm_enable", "period_counts", "auto_reload", "deadtime_counts", "duty_max_q20", "requested_duty_q20", "clamped_duty_q20", "pending_compare", "active_compare_before", "active_compare_after"):
                row[name] = int(raw[name])
            for name in ("requested_duty", "clamped_duty", "effective_duty_after"):
                row[name] = float(raw[name])
            for name in ("active_enable_before", "active_enable_after", "duty_clamped", "update_pending_after", "arithmetic_overflow"):
                row[name] = raw[name] == "1"
            rows.append(row)
    return rows


def metric(case_id: str, name: str, value: float, tolerance: float, passed: bool, note: str, status: str | None = None) -> dict[str, object]:
    return {"case": case_id, "metric": name, "value": value, "tolerance": tolerance, "status": status or ("PASS" if passed else "FAIL"), "note": note}


def build_metrics(rows: list[dict[str, object]], unit_output: str) -> list[dict[str, object]]:
    metrics: list[dict[str, object]] = []
    for profile in TIMER_PROFILES:
        case_id = str(profile["case"])
        case_rows = [row for row in rows if row["case"] == case_id]
        max_error = max(abs(float(row["effective_duty_after"]) - float(row["requested_duty"])) for row in case_rows)
        tolerance = 0.5 / int(profile["period_counts"]) + 1.0 / Q20_SCALE
        metrics.append(metric(case_id, "max_abs_effective_duty_error", max_error, tolerance, max_error <= tolerance, "比较值取整误差不得超过半个定时器计数加一个 Q20 LSB"))

    clamp_rows = [row for row in rows if row["case"] == "duty_clamp_170mhz"]
    low_ok = all(float(row["clamped_duty"]) == 0.0 and bool(row["duty_clamped"]) for row in clamp_rows if float(row["requested_duty"]) < 0.0)
    high_ok = all(float(row["clamped_duty"]) <= DUTY_MAX and bool(row["duty_clamped"]) for row in clamp_rows if float(row["requested_duty"]) > DUTY_MAX)
    max_compare = max(int(row["active_compare_after"]) for row in clamp_rows)
    metrics.append(metric("duty_clamp_170mhz", "negative_duty_clamp", 1.0 if low_ok else 0.0, 1.0, low_ok, "负 duty 必须钳位到 0"))
    metrics.append(metric("duty_clamp_170mhz", "high_duty_clamp", 1.0 if high_ok else 0.0, 1.0, high_ok, "超过 65% 的 duty 必须钳位"))
    metrics.append(metric("duty_clamp_170mhz", "max_compare_counts", float(max_compare), 276.0, max_compare <= 276, "65% Q20 duty 映射后的比较值不得超过 276 counts"))

    shadow = [row for row in rows if row["case"] == "shadow_update_sequence"]
    queue_only = [row for row in shadow if int(row["apply_update"]) == 0 and int(row["pwm_enable"]) == 1]
    wait_ok = all(int(row["active_compare_after"]) == int(row["active_compare_before"]) and bool(row["update_pending_after"]) for row in queue_only)
    apply_ok = all(not bool(row["update_pending_after"]) for row in shadow if int(row["apply_update"]) == 1)
    disable_row = next(row for row in shadow if int(row["pwm_enable"]) == 0 and int(row["apply_update"]) == 0)
    disable_ok = not bool(disable_row["active_enable_after"])
    metrics.append(metric("shadow_update_sequence", "queue_does_not_change_active_compare", 1.0 if wait_ok else 0.0, 1.0, wait_ok, "预装载写入不得在周期中间改变有效比较值"))
    metrics.append(metric("shadow_update_sequence", "update_event_applies_pending", 1.0 if apply_ok else 0.0, 1.0, apply_ok, "更新事件后 pending 标志必须清除"))
    metrics.append(metric("shadow_update_sequence", "disable_is_immediate", 1.0 if disable_ok else 0.0, 1.0, disable_ok, "保护关断不等待更新事件"))

    overflow_count = sum(bool(row["arithmetic_overflow"]) for row in rows)
    metrics.append(metric("all", "arithmetic_overflow_count", float(overflow_count), 0.0, overflow_count == 0, "Q20 duty 到比较值的整数运算不得溢出"))
    for line in unit_output.splitlines():
        parts = line.strip().split(",", 1)
        if len(parts) == 2 and parts[0] in ("PASS", "FAIL"):
            passed = parts[0] == "PASS"
            metrics.append(metric("pwm_unit_tests", parts[1], 1.0 if passed else 0.0, 1.0, passed, "PWM 映射 C 单元测试"))
    return metrics


def write_metrics(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["case", "metric", "value", "tolerance", "status", "note"])
        writer.writeheader()
        writer.writerows(rows)


def plot_resolution(path: Path, rows: list[dict[str, object]]) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2))
    colors = ["#64748b", "#d97706", "#0f766e"]
    labels = ["72MHz / 180 counts", "100MHz / 250 counts", "170MHz / 425 counts"]
    for profile, color, label in zip(TIMER_PROFILES, colors, labels):
        case_rows = [row for row in rows if row["case"] == profile["case"]]
        requested = [float(row["requested_duty"]) for row in case_rows]
        effective = [float(row["effective_duty_after"]) for row in case_rows]
        axes[0].step(requested, effective, where="mid", color=color, linewidth=1.4, label=label)
        axes[1].plot(requested, [actual - target for actual, target in zip(effective, requested)], color=color, linewidth=1.2, label=label)
    axes[0].plot([0.0, DUTY_MAX], [0.0, DUTY_MAX], color="#111827", linestyle="--", linewidth=1.0, label="理想 duty")
    axes[0].set_title("Q20 duty → 有效定时器 duty", loc="left")
    axes[0].set_xlabel("请求 duty")
    axes[0].set_ylabel("有效 duty")
    axes[1].axhline(0.0, color="#111827", linewidth=0.8)
    axes[1].set_title("比较值取整误差", loc="left")
    axes[1].set_xlabel("请求 duty")
    axes[1].set_ylabel("有效 duty - 请求 duty")
    for ax in axes:
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
    fig.suptitle("第 15 章：定时器计数分辨率决定最终 duty 精度", fontsize=15)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_shadow(path: Path, rows: list[dict[str, object]]) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    sequence = [row for row in rows if row["case"] == "shadow_update_sequence"]
    x = [int(row["index"]) for row in sequence]
    fig, axes = plt.subplots(2, 1, figsize=(10.5, 6.8), sharex=True)
    axes[0].step(x, [int(row["pending_compare"]) for row in sequence], where="post", color="#d97706", linewidth=1.7, label="pending compare")
    axes[0].step(x, [int(row["active_compare_after"]) for row in sequence], where="post", color="#0f766e", linewidth=1.7, label="active compare")
    for row in sequence:
        if int(row["apply_update"]) == 1:
            axes[0].axvline(int(row["index"]), color="#2563eb", linestyle=":", linewidth=1.0)
    axes[0].set_ylabel("timer counts")
    axes[0].set_title("预装载比较值只在更新事件进入有效寄存器", loc="left")
    axes[0].legend()
    axes[0].grid(True, alpha=0.25)

    axes[1].step(x, [int(row["pwm_enable"]) for row in sequence], where="post", color="#64748b", linewidth=1.5, label="command enable")
    axes[1].step(x, [1 if bool(row["active_enable_after"]) else 0 for row in sequence], where="post", color="#be123c", linewidth=1.7, label="active enable")
    axes[1].set_xlabel("命令序号")
    axes[1].set_ylabel("enable")
    axes[1].set_yticks([0, 1])
    axes[1].set_title("关断命令立即拉低 active enable", loc="left")
    axes[1].legend()
    axes[1].grid(True, alpha=0.25)
    fig.suptitle("第 15 章：PWM 影子寄存器更新与立即关断", fontsize=15)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_report(path: Path, metrics: list[dict[str, object]], compiler_display: str, rows: int, runner_output: str, unit_output: str) -> None:
    passes = sum(row["status"] == "PASS" for row in metrics)
    fails = sum(row["status"] == "FAIL" for row in metrics)
    lines = [
        "# 第 15 章报告：Q20 duty 到 PWM 定时器比较值映射",
        "",
        "本报告由 `scripts/run_pwm_mapping_tests.py` 生成，所有比较值、影子更新和立即关断结果来自真实编译执行的 `src/digital_power_pwm_map.c`。",
        "",
        "## 摘要",
        "",
        f"- 编译器：`{compiler_display}`",
        f"- C 回放行数：{rows}",
        f"- 指标：PASS {passes} / FAIL {fails}",
        "",
        "```text",
        runner_output,
        "```",
        "",
        "```text",
        unit_output,
        "```",
        "",
        "## 指标",
        "",
        "| 场景 | 指标 | 实际值 | 限制 | 状态 | 说明 |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in metrics:
        lines.append(f"| `{row['case']}` | `{row['metric']}` | {float(row['value']):.6g} | {float(row['tolerance']):.6g} | {row['status']} | {row['note']} |")
    lines.extend([
        "",
        "## 边界",
        "",
        "本报告验证通用中心对齐 PWM 的周期计数、Q20 duty 舍入、65%限幅、100ns死区计数、影子寄存器更新和立即关断语义。它不等于具体 MCU 的 ARR/CCR/BDTR 寄存器已经配置，也不包含真实门极波形和死区测量。",
        "",
    ])
    text = "\n".join(lines).replace("\r\n", "\n").replace("\r", "\n")
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(text.replace("\n", "\r\n"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Chapter 15 Q20-to-PWM mapping checks.")
    parser.add_argument("--prepare-only", action="store_true", help="Only generate PWM replay input and timer profiles.")
    args = parser.parse_args(argv)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    WAVE_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    input_rows = build_input_rows()
    input_path = BUILD_DIR / "15-pwm-mapping-input.csv"
    output_path = BUILD_DIR / "15-pwm-mapping-output.csv"
    write_rows(input_path, input_rows)
    write_timer_profiles(WAVE_DIR / "15-pwm-timer-config.csv")
    if args.prepare_only:
        print(f"prepared,rows={len(input_rows)},input={input_path}")
        return 0

    compiler, hint = find_compiler()
    if compiler is None:
        print("summary,BLOCKED,未找到 C 编译器")
        return 2
    version = compiler_version(compiler, hint)
    compiler_display = f"{hint} {version}" if version else hint
    source = ROOT / "src" / "digital_power_pwm_map.c"
    unit_source = ROOT / "tests" / "test_digital_power_pwm_map.c"
    runner_source = ROOT / "tests" / "replay_digital_power_pwm_map.c"
    unit_exe = BUILD_DIR / ("digital_power_pwm_map_tests.exe" if os.name == "nt" else "digital_power_pwm_map_tests")
    runner_exe = BUILD_DIR / ("digital_power_pwm_map_replay.exe" if os.name == "nt" else "digital_power_pwm_map_replay")
    for command, label in (
        (compile_command(compiler, hint, [source, unit_source], unit_exe), "unit_build"),
        (compile_command(compiler, hint, [source, runner_source], runner_exe), "runner_build"),
    ):
        code, output = run_command(command, BUILD_DIR)
        if code != 0:
            print(output)
            print(f"summary,FAIL,{label}_exit_code={code}")
            return 1
    unit_code, unit_output = run_command([str(unit_exe)], BUILD_DIR)
    if unit_code != 0:
        print(unit_output)
        return 1
    runner_code, runner_output = run_command([str(runner_exe), str(input_path), str(output_path)], BUILD_DIR)
    if runner_code != 0:
        print(runner_output)
        return 1

    rows = read_output(output_path)
    metrics = build_metrics(rows, unit_output)
    write_metrics(WAVE_DIR / "15-pwm-mapping-summary.csv", metrics)
    write_rows(WAVE_DIR / "15-pwm-mapping-samples.csv", rows)
    plot_resolution(WAVE_DIR / "15-pwm-resolution.png", rows)
    plot_shadow(WAVE_DIR / "15-pwm-shadow-update.png", rows)
    write_report(REPORT_DIR / "15-pwm-mapping-report.md", metrics, compiler_display, len(rows), runner_output, unit_output)
    passes = sum(row["status"] == "PASS" for row in metrics)
    fails = sum(row["status"] == "FAIL" for row in metrics)
    max_error = max(float(row["value"]) for row in metrics if row["metric"] == "max_abs_effective_duty_error")
    print("已生成第 15 章 PWM 映射数据、图表和报告。")
    print(f"summary,pass={passes},fail={fails},rows={len(rows)}")
    print(f"toolchain,{hint},{compiler_display}")
    print(f"pwm,period_counts=425,arr=425,deadtime_counts=17,max_duty_error={max_error:.6g}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
