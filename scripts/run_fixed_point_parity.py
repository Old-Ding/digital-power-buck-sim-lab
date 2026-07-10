from __future__ import annotations

import argparse
import csv
import math
import os
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt

from export_controller_c_style_tests import Config
from run_c_python_parity import CASE_STOPS, build_replay_package, write_replay_input
from run_host_build_tests import compiler_family, compiler_version, find_compiler, run_command


ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "artifacts" / "host-build" / "chapter13"
WAVE_DIR = ROOT / "waveforms"
REPORT_DIR = ROOT / "reports"

FIXED_FRAC_BITS = 20
FIXED_SCALE = 1 << FIXED_FRAC_BITS
INT32_MAX = (1 << 31) - 1

FLOAT_TOLERANCES = {
    "vout_meas_v": 1.0e-6,
    "vref_cmd_v": 1.1e-3,
    "error_v": 1.1e-3,
    "p_term": 6.0e-5,
    "integrator": 1.0e-4,
    "duty_raw": 1.5e-4,
    "duty_cmd": 1.5e-4,
}

DISCRETE_FIELDS = (
    "state",
    "active_fault",
    "latched_fault",
    "pwm_enable",
    "saturation",
    "allow_integrate",
)


def fixed_raw(value: float, fractional_bits: int = FIXED_FRAC_BITS) -> int:
    scaled = value * float(1 << fractional_bits)
    return math.floor(scaled + 0.5) if scaled >= 0.0 else math.ceil(scaled - 0.5)


def build_format_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    decisions = {
        16: "不选：软启动每周期增量过粗，8000 周期累计偏差约 37mV",
        20: "采用：软启动累计误差约 1mV，100°C 阈值仅占正量程约 4.88%",
        24: "不选：100°C 已占正量程约 78.13%，温度和异常输入余量不足",
    }
    for fractional_bits in (16, 20, 24):
        scale = 1 << fractional_bits
        resolution = 1.0 / scale
        positive_range = INT32_MAX / scale
        step_raw = fixed_raw(0.0015, fractional_bits)
        represented_step = step_raw / scale
        accumulated_v = represented_step * 8000.0
        rows.append(
            {
                "fractional_bits": fractional_bits,
                "scale": scale,
                "resolution": resolution,
                "positive_range": positive_range,
                "soft_start_step_raw": step_raw,
                "represented_step_v": represented_step,
                "one_step_error_uv": (represented_step - 0.0015) * 1.0e6,
                "value_after_8000_steps_v": accumulated_v,
                "error_after_8000_steps_mv": (accumulated_v - 12.0) * 1.0e3,
                "otp_100c_range_pct": 100.0 / positive_range * 100.0,
                "decision": decisions[fractional_bits],
            }
        )
    return rows


def build_constant_rows() -> list[dict[str, object]]:
    values = [
        ("vref_final", 12.0, "V"),
        ("soft_start_step", 0.0015, "V/cycle"),
        ("kp", 0.05, "1"),
        ("ki_step", 0.0004, "1/cycle"),
        ("duty_feedforward", 0.5, "1"),
        ("duty_max", 0.65, "1"),
        ("ocp_threshold", 6.5, "A"),
        ("ovp_threshold", 13.2, "V"),
        ("uvlo_threshold", 18.0, "V"),
        ("otp_threshold", 100.0, "degC"),
    ]
    rows: list[dict[str, object]] = []
    for name, engineering_value, unit in values:
        raw = fixed_raw(engineering_value)
        represented = raw / FIXED_SCALE
        rows.append(
            {
                "name": name,
                "engineering_value": engineering_value,
                "unit": unit,
                "raw_q20": raw,
                "represented_value": represented,
                "quantization_error": represented - engineering_value,
            }
        )
    return rows


def write_dict_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_command(compiler: str, hint: str, exe_path: Path) -> list[str]:
    float_source = ROOT / "src" / "digital_power_control.c"
    fixed_source = ROOT / "src" / "digital_power_control_fixed.c"
    runner = ROOT / "tests" / "replay_digital_power_control_fixed.c"
    include = ROOT / "src"
    family = compiler_family(compiler, hint)

    if family == "zig":
        return [
            compiler,
            "cc",
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(include),
            str(float_source),
            str(fixed_source),
            str(runner),
            "-lm",
            "-o",
            str(exe_path),
        ]

    if family == "msvc":
        return [
            compiler,
            "/nologo",
            "/W4",
            "/WX",
            f"/I{include}",
            str(float_source),
            str(fixed_source),
            str(runner),
            f"/Fe:{exe_path}",
        ]

    return [
        compiler,
        "-std=c99",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-I",
        str(include),
        str(float_source),
        str(fixed_source),
        str(runner),
        "-lm",
        "-o",
        str(exe_path),
    ]


def build_unit_test_command(compiler: str, hint: str, exe_path: Path) -> list[str]:
    fixed_source = ROOT / "src" / "digital_power_control_fixed.c"
    test_source = ROOT / "tests" / "test_digital_power_control_fixed.c"
    include = ROOT / "src"
    family = compiler_family(compiler, hint)

    if family == "zig":
        return [compiler, "cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-I", str(include), str(fixed_source), str(test_source), "-o", str(exe_path)]
    if family == "msvc":
        return [compiler, "/nologo", "/W4", "/WX", f"/I{include}", str(fixed_source), str(test_source), f"/Fe:{exe_path}"]
    return [compiler, "-std=c99", "-Wall", "-Wextra", "-Werror", "-I", str(include), str(fixed_source), str(test_source), "-o", str(exe_path)]


def unit_test_metrics(output: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line in output.splitlines():
        parts = line.strip().split(",", 1)
        if len(parts) != 2 or parts[0] not in ("PASS", "FAIL"):
            continue
        passed = parts[0] == "PASS"
        rows.append(metric_row("fixed_unit_tests", parts[1], 1.0 if passed else 0.0, 1.0, passed, "定点格式、正常步进或溢出边界单元测试"))
    return rows


def parse_bool(value: str) -> bool:
    return value.strip() in ("1", "true", "True")


def read_runner_output(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", newline="", encoding="utf-8") as file:
        for raw in csv.DictReader(file):
            row: dict[str, object] = {
                "case": raw["case"],
                "tick": int(raw["tick"]),
                "time_s": float(raw["time_s"]),
            }
            for field in FLOAT_TOLERANCES:
                row[f"float_{field}"] = float(raw[f"float_{field}"])
                row[f"fixed_{field}"] = float(raw[f"fixed_{field}"])
            for field in DISCRETE_FIELDS:
                parser = parse_bool if field in ("pwm_enable", "saturation", "allow_integrate") else int
                row[f"float_{field}"] = parser(raw[f"float_{field}"])
                row[f"fixed_{field}"] = parser(raw[f"fixed_{field}"])
            row["fixed_duty_cmd_raw"] = int(raw["fixed_duty_cmd_raw"])
            row["fixed_vref_cmd_raw"] = int(raw["fixed_vref_cmd_raw"])
            row["fixed_integrator_raw"] = int(raw["fixed_integrator_raw"])
            row["fixed_arithmetic_overflow"] = parse_bool(raw["fixed_arithmetic_overflow"])
            row["fixed_overflow_count"] = int(raw["fixed_overflow_count"])
            row["input_conversion_overflow"] = parse_bool(raw["input_conversion_overflow"])
            row["fixed_peak_abs_raw"] = int(raw["fixed_peak_abs_raw"])
            rows.append(row)
    return rows


def metric_row(
    case_id: str,
    metric: str,
    value: float,
    tolerance: float,
    passed: bool,
    note: str,
) -> dict[str, object]:
    return {
        "case": case_id,
        "metric": metric,
        "value": value,
        "tolerance": tolerance,
        "status": "PASS" if passed else "FAIL",
        "note": note,
    }


def compare_rows(rows: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    comparisons: list[dict[str, object]] = []
    by_case: dict[str, list[dict[str, object]]] = defaultdict(list)

    for source in rows:
        row = dict(source)
        for field in FLOAT_TOLERANCES:
            row[f"error_{field}"] = abs(float(source[f"fixed_{field}"]) - float(source[f"float_{field}"]))
        for field in DISCRETE_FIELDS:
            row[f"mismatch_{field}"] = 0 if source[f"fixed_{field}"] == source[f"float_{field}"] else 1
        comparisons.append(row)
        by_case[str(row["case"])].append(row)

    metrics: list[dict[str, object]] = []
    for case_id in CASE_STOPS:
        case_rows = by_case[case_id]
        for field, tolerance in FLOAT_TOLERANCES.items():
            max_error = max(float(row[f"error_{field}"]) for row in case_rows)
            metrics.append(
                metric_row(
                    case_id,
                    f"max_abs_{field}_error",
                    max_error,
                    tolerance,
                    max_error <= tolerance,
                    f"定点 C 与浮点 C 的 {field} 最大绝对误差",
                )
            )

        state_mismatches = sum(int(row["mismatch_state"]) for row in case_rows)
        fault_mismatches = sum(
            int(row["mismatch_active_fault"]) + int(row["mismatch_latched_fault"])
            for row in case_rows
        )
        pwm_mismatches = sum(int(row["mismatch_pwm_enable"]) for row in case_rows)
        logic_mismatches = sum(
            int(row["mismatch_saturation"]) + int(row["mismatch_allow_integrate"])
            for row in case_rows
        )
        arithmetic_overflows = sum(int(bool(row["fixed_arithmetic_overflow"])) for row in case_rows)
        input_overflows = sum(int(bool(row["input_conversion_overflow"])) for row in case_rows)
        peak_raw = max(int(row["fixed_peak_abs_raw"]) for row in case_rows)
        raw_utilization_pct = peak_raw / INT32_MAX * 100.0

        metrics.extend(
            [
                metric_row(case_id, "state_mismatch_count", state_mismatches, 0.0, state_mismatches == 0, "状态必须逐周期一致"),
                metric_row(case_id, "fault_mismatch_count", fault_mismatches, 0.0, fault_mismatches == 0, "活动与锁存故障必须逐周期一致"),
                metric_row(case_id, "pwm_mismatch_count", pwm_mismatches, 0.0, pwm_mismatches == 0, "PWM 使能必须逐周期一致"),
                metric_row(case_id, "logic_flag_mismatch_count", logic_mismatches, 0.0, logic_mismatches == 0, "限幅与积分允许标志必须逐周期一致"),
                metric_row(case_id, "arithmetic_overflow_count", arithmetic_overflows, 0.0, arithmetic_overflows == 0, "定点加减乘除不得触发 32 位饱和"),
                metric_row(case_id, "input_conversion_overflow_count", input_overflows, 0.0, input_overflows == 0, "回放输入转换不得超出 Q20 范围"),
                metric_row(case_id, "max_raw_utilization_pct", raw_utilization_pct, 10.0, raw_utilization_pct <= 10.0, "配置、输入、状态和输出 raw 值占 int32 正量程比例"),
            ]
        )

    return comparisons, metrics


def write_metrics(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["case", "metric", "value", "tolerance", "status", "note"])
        writer.writeheader()
        writer.writerows(rows)


def write_samples(path: Path, rows: list[dict[str, object]]) -> None:
    last_ticks: dict[str, int] = {}
    for row in rows:
        case_id = str(row["case"])
        last_ticks[case_id] = max(last_ticks.get(case_id, -1), int(row["tick"]))

    selected = [
        row
        for row in rows
        if int(row["tick"]) % 20 == 0
        or int(row["tick"]) == last_ticks[str(row["case"])]
        or bool(row["fixed_arithmetic_overflow"])
        or bool(row["input_conversion_overflow"])
        or any(int(row[f"mismatch_{field}"]) != 0 for field in DISCRETE_FIELDS)
    ]
    fieldnames = [
        "case",
        "tick",
        "time_s",
        "float_duty_cmd",
        "fixed_duty_cmd",
        "fixed_duty_cmd_raw",
        "error_duty_cmd",
        "float_vref_cmd_v",
        "fixed_vref_cmd_v",
        "fixed_vref_cmd_raw",
        "error_vref_cmd_v",
        "float_integrator",
        "fixed_integrator",
        "fixed_integrator_raw",
        "error_integrator",
        "float_state",
        "fixed_state",
        "float_latched_fault",
        "fixed_latched_fault",
        "float_pwm_enable",
        "fixed_pwm_enable",
        "fixed_arithmetic_overflow",
        "fixed_peak_abs_raw",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(selected)


def plot_overlay(path: Path, rows: list[dict[str, object]]) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    cases = ["soft_start_40ms", "load_step_50_100_50", "ocp_latch_clear", "uvlo_blocks_pwm"]
    labels = {
        "soft_start_40ms": "软启动",
        "load_step_50_100_50": "负载突变",
        "ocp_latch_clear": "过流锁存与清除",
        "uvlo_blocks_pwm": "输入欠压关 PWM",
    }
    by_case: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_case[str(row["case"])].append(row)

    fig, axes = plt.subplots(4, 2, figsize=(13.5, 10.0))
    for row_index, case_id in enumerate(cases):
        display = by_case[case_id][::100]
        if display[-1] is not by_case[case_id][-1]:
            display.append(by_case[case_id][-1])
        time_ms = [float(row["time_s"]) * 1000.0 for row in display]
        left = axes[row_index][0]
        right = axes[row_index][1]

        left.plot(time_ms, [float(row["float_duty_cmd"]) for row in display], color="#0f766e", linewidth=1.7, label="浮点 C")
        left.plot(time_ms, [float(row["fixed_duty_cmd"]) for row in display], color="#d97706", linewidth=1.1, linestyle="--", label="定点 C")
        left.set_title(f"{labels[case_id]}：duty_cmd", loc="left", fontsize=11)
        left.set_ylabel("duty")
        left.grid(True, alpha=0.25)

        if case_id == "soft_start_40ms":
            right.plot(time_ms, [float(row["float_vref_cmd_v"]) for row in display], color="#2563eb", linewidth=1.7, label="浮点 Vref")
            right.plot(time_ms, [float(row["fixed_vref_cmd_v"]) for row in display], color="#dc2626", linewidth=1.1, linestyle="--", label="定点 Vref")
            right.set_title("软启动参考值", loc="left", fontsize=11)
            right.set_ylabel("Vref / V")
        elif case_id == "load_step_50_100_50":
            right.plot(time_ms, [float(row["float_integrator"]) for row in display], color="#2563eb", linewidth=1.7, label="浮点积分器")
            right.plot(time_ms, [float(row["fixed_integrator"]) for row in display], color="#dc2626", linewidth=1.1, linestyle="--", label="定点积分器")
            right.set_title("负载突变积分器", loc="left", fontsize=11)
            right.set_ylabel("integrator")
        else:
            right.step(time_ms, [int(row["float_state"]) for row in display], where="post", color="#2563eb", linewidth=1.5, label="浮点 state")
            right.step(time_ms, [int(row["fixed_state"]) for row in display], where="post", color="#60a5fa", linewidth=1.0, linestyle="--", label="定点 state")
            right.step(time_ms, [int(row["float_latched_fault"]) for row in display], where="post", color="#dc2626", linewidth=1.5, label="浮点 fault")
            right.step(time_ms, [int(row["fixed_latched_fault"]) for row in display], where="post", color="#f97316", linewidth=1.0, linestyle="--", label="定点 fault")
            right.set_title(f"{labels[case_id]}：状态与故障", loc="left", fontsize=11)
            right.set_ylabel("state / fault")
        right.grid(True, alpha=0.25)

        left.legend(loc="best", ncol=2, fontsize=8)
        right.legend(loc="best", ncol=2, fontsize=8)
        if row_index == len(cases) - 1:
            left.set_xlabel("Time / ms")
            right.set_xlabel("Time / ms")

    fig.suptitle("第 13 章：相同输入下的浮点 C / Q20 定点 C 对照", fontsize=16)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.97))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_error_and_format(
    path: Path,
    metrics: list[dict[str, object]],
    format_rows: list[dict[str, object]],
) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    cases = list(CASE_STOPS)
    case_labels = ["稳态", "软启动", "负载突变", "OCP", "UVLO"]
    selected = ["max_abs_duty_cmd_error", "max_abs_vref_cmd_v_error", "max_abs_integrator_error"]
    labels = ["duty_cmd", "vref_cmd", "integrator"]
    colors = ["#0f766e", "#d97706", "#be123c"]
    lookup = {(str(row["case"]), str(row["metric"])): row for row in metrics}

    fig, axes = plt.subplots(1, 2, figsize=(13.0, 5.4))
    ax = axes[0]
    x = list(range(len(cases)))
    width = 0.24
    for metric_index, (metric, label, color) in enumerate(zip(selected, labels, colors)):
        ratios = []
        for case_id in cases:
            row = lookup[(case_id, metric)]
            value = float(row["value"])
            tolerance = float(row["tolerance"])
            ratios.append(max(value / tolerance, 1.0e-7))
        positions = [value + (metric_index - 1) * width for value in x]
        ax.bar(positions, ratios, width=width, color=color, label=label)
    ax.axhline(1.0, color="#111827", linestyle="--", linewidth=1.2, label="允许误差上限")
    ax.set_yscale("log")
    ax.set_ylim(1.0e-7, 2.0)
    ax.set_xticks(x)
    ax.set_xticklabels(case_labels)
    ax.set_ylabel("最大绝对误差 / 允许误差")
    ax.set_title("真实回放：误差低于 1 表示通过")
    ax.grid(axis="y", which="both", alpha=0.22)
    ax.legend(loc="upper left", ncol=2, fontsize=8)

    ax2 = axes[1]
    names = [f"Q{int(row['fractional_bits'])}" for row in format_rows]
    accumulated_errors = [abs(float(row["error_after_8000_steps_mv"])) for row in format_rows]
    range_use = [float(row["otp_100c_range_pct"]) for row in format_rows]
    bars = ax2.bar(names, accumulated_errors, color=["#64748b", "#0f766e", "#d97706"], width=0.55, label="8000 周期软启动累计误差")
    ax2.set_ylabel("累计误差 / mV")
    ax2.set_title("格式选择：精度与正量程占用")
    ax2.grid(axis="y", alpha=0.22)
    range_axis = ax2.twinx()
    range_axis.plot(names, range_use, color="#be123c", marker="o", linewidth=1.8, label="100°C 占正量程")
    range_axis.set_ylabel("100°C 占正量程 / %")
    range_axis.set_ylim(0.0, max(range_use) * 1.25)
    for bar, value in zip(bars, accumulated_errors):
        if value > 5.0:
            ax2.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() - 1.2, f"{value:.3g}", ha="center", va="top", fontsize=8, color="white")
        else:
            ax2.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height() + 0.7, f"{value:.3g}", ha="center", va="bottom", fontsize=8)
    for index, value in enumerate(range_use):
        range_axis.annotate(f"{value:.3g}%", (index, value), xytext=(0, -15 if value > 60.0 else 8), textcoords="offset points", ha="center", fontsize=8, color="#be123c")
    handles_a, labels_a = ax2.get_legend_handles_labels()
    handles_b, labels_b = range_axis.get_legend_handles_labels()
    ax2.legend(handles_a + handles_b, labels_a + labels_b, loc="upper center", fontsize=8)

    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_report(
    path: Path,
    metrics: list[dict[str, object]],
    format_rows: list[dict[str, object]],
    constants: list[dict[str, object]],
    compiler_display: str,
    row_count: int,
    sample_count: int,
    runner_output: str,
    unit_output: str,
) -> None:
    pass_count = sum(1 for row in metrics if row["status"] == "PASS")
    fail_count = sum(1 for row in metrics if row["status"] == "FAIL")
    scenario_status = {
        case_id: "FAIL" if any(row["status"] == "FAIL" for row in metrics if row["case"] == case_id) else "PASS"
        for case_id in CASE_STOPS
    }
    lines = [
        "# 第 13 章报告：Q20 定点 C 与浮点 C 逐周期对照",
        "",
        "本报告由 `scripts/run_fixed_point_parity.py` 生成。浮点基准来自 `src/digital_power_control.c`，定点结果来自 `src/digital_power_control_fixed.c`，两者由同一个 C 回放程序接收相同输入。",
        "",
        "## 执行摘要",
        "",
        f"- 电脑端 C 编译器：`{compiler_display}`",
        f"- 定点格式：有符号 32 位，{FIXED_FRAC_BITS} 个小数位，缩放因子 {FIXED_SCALE}",
        f"- 对照场景：{len(CASE_STOPS)}",
        f"- 逐周期比较行数：{row_count}",
        f"- 公开抽样行数：{sample_count}",
        f"- 指标结果：PASS {pass_count} / FAIL {fail_count}",
        "",
        "C 双实现回放程序输出：",
        "",
        "```text",
        runner_output,
        "```",
        "",
        "定点单元测试输出：",
        "",
        "```text",
        unit_output,
        "```",
        "",
        "## 格式候选",
        "",
        "| 小数位 | 分辨率 | 正量程 | 8000 周期软启动误差 | 100°C 占正量程 | 结论 |",
        "| ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in format_rows:
        lines.append(
            f"| {int(row['fractional_bits'])} | {float(row['resolution']):.6g} | {float(row['positive_range']):.6g} | {float(row['error_after_8000_steps_mv']):.6g} mV | {float(row['otp_100c_range_pct']):.6g}% | {row['decision']} |"
        )

    lines.extend(
        [
            "",
            "## Q20 常量",
            "",
            "| 名称 | 工程值 | raw | 还原值 | 量化误差 |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in constants:
        lines.append(
            f"| `{row['name']}` | {float(row['engineering_value']):.9g} {row['unit']} | {int(row['raw_q20'])} | {float(row['represented_value']):.12g} | {float(row['quantization_error']):.6g} |"
        )

    lines.extend(
        [
            "",
            "## 场景结论",
            "",
            "| 场景 | 状态 |",
            "| --- | --- |",
        ]
    )
    for case_id, status in scenario_status.items():
        lines.append(f"| `{case_id}` | {status} |")

    lines.extend(
        [
            "",
            "## 指标明细",
            "",
            "| 场景 | 指标 | 实际值 | 允许值 | 状态 |",
            "| --- | --- | ---: | ---: | --- |",
        ]
    )
    for row in metrics:
        lines.append(
            f"| `{row['case']}` | `{row['metric']}` | {float(row['value']):.6g} | {float(row['tolerance']):.6g} | {row['status']} |"
        )

    lines.extend(
        [
            "",
            "## 结果边界",
            "",
            "这份报告验证当前五个回放场景中，Q20 定点控制器与浮点 C 的数值误差、状态迁移、故障、PWM、逻辑标志和算术溢出。它不包含目标 MCU 指令耗时、ADC 码值换算、PWM 寄存器映射或硬件闭环。",
            "",
        ]
    )
    text = "\n".join(lines).replace("\r\n", "\n").replace("\r", "\n")
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(text.replace("\n", "\r\n"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Chapter 13 float/fixed-point C parity checks.")
    parser.add_argument("--prepare-only", action="store_true", help="Only generate replay input and fixed-point format tables.")
    args = parser.parse_args(argv)

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    WAVE_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)

    cfg = Config()
    package = build_replay_package(cfg)
    replay_input = BUILD_DIR / "13-controller-replay-input.csv"
    runner_output_path = BUILD_DIR / "13-fixed-point-output.csv"
    exe_path = BUILD_DIR / ("digital_power_control_fixed_replay.exe" if os.name == "nt" else "digital_power_control_fixed_replay")
    unit_exe_path = BUILD_DIR / ("digital_power_control_fixed_tests.exe" if os.name == "nt" else "digital_power_control_fixed_tests")
    format_rows = build_format_rows()
    constants = build_constant_rows()

    write_replay_input(replay_input, package.input_rows)
    write_dict_rows(WAVE_DIR / "13-fixed-point-format.csv", format_rows)
    write_dict_rows(WAVE_DIR / "13-fixed-point-constants.csv", constants)

    if args.prepare_only:
        print(f"prepared,rows={len(package.input_rows)},input={replay_input}")
        print(f"fixed_format,frac_bits={FIXED_FRAC_BITS},scale={FIXED_SCALE}")
        return 0

    compiler, hint = find_compiler()
    if compiler is None:
        print("summary,BLOCKED,未找到 C 编译器")
        return 2

    version = compiler_version(compiler, hint)
    compiler_display = f"{hint} {version}" if version else hint
    command = build_command(compiler, hint, exe_path)
    build_code, build_output = run_command(command, BUILD_DIR)
    if build_code != 0:
        print(build_output)
        print(f"summary,FAIL,build_exit_code={build_code}")
        return 1

    unit_command = build_unit_test_command(compiler, hint, unit_exe_path)
    unit_build_code, unit_build_output = run_command(unit_command, BUILD_DIR)
    if unit_build_code != 0:
        print(unit_build_output)
        print(f"summary,FAIL,unit_build_exit_code={unit_build_code}")
        return 1

    unit_code, unit_output = run_command([str(unit_exe_path)], BUILD_DIR)
    if unit_code != 0:
        print(unit_output)
        print(f"summary,FAIL,unit_test_exit_code={unit_code}")
        return 1

    replay_code, replay_output = run_command([str(exe_path), str(replay_input), str(runner_output_path)], BUILD_DIR)
    if replay_code != 0:
        print(replay_output)
        print(f"summary,FAIL,replay_exit_code={replay_code}")
        return 1

    runner_rows = read_runner_output(runner_output_path)
    if len(runner_rows) != len(package.input_rows):
        raise RuntimeError(f"runner row count differs: expected={len(package.input_rows)}, actual={len(runner_rows)}")
    comparisons, metrics = compare_rows(runner_rows)
    metrics.extend(unit_test_metrics(unit_output))

    summary_path = WAVE_DIR / "13-fixed-point-summary.csv"
    samples_path = WAVE_DIR / "13-fixed-point-samples.csv"
    write_metrics(summary_path, metrics)
    write_samples(samples_path, comparisons)
    plot_overlay(WAVE_DIR / "13-fixed-point-overlay.png", comparisons)
    plot_error_and_format(WAVE_DIR / "13-fixed-point-error-format.png", metrics, format_rows)

    with samples_path.open("r", encoding="utf-8") as file:
        sample_count = max(sum(1 for _ in file) - 1, 0)
    write_report(
        REPORT_DIR / "13-fixed-point-parity-report.md",
        metrics,
        format_rows,
        constants,
        compiler_display,
        len(comparisons),
        sample_count,
        replay_output,
        unit_output,
    )

    pass_count = sum(1 for row in metrics if row["status"] == "PASS")
    fail_count = sum(1 for row in metrics if row["status"] == "FAIL")
    max_duty_error = max(float(row["value"]) for row in metrics if row["metric"] == "max_abs_duty_cmd_error")
    max_vref_error = max(float(row["value"]) for row in metrics if row["metric"] == "max_abs_vref_cmd_v_error")
    max_integrator_error = max(float(row["value"]) for row in metrics if row["metric"] == "max_abs_integrator_error")
    max_raw_use = max(float(row["value"]) for row in metrics if row["metric"] == "max_raw_utilization_pct")

    print("已生成第 13 章浮点 C 与 Q20 定点 C 对照数据、图表和报告。")
    print(f"summary,pass={pass_count},fail={fail_count},scenarios={len(CASE_STOPS)},rows={len(comparisons)}")
    print(f"toolchain,{hint},{compiler_display}")
    print(f"fixed_format,frac_bits={FIXED_FRAC_BITS},scale={FIXED_SCALE},max_raw_use_pct={max_raw_use:.6g}")
    print(f"max_error,duty_cmd={max_duty_error:.6g},vref_cmd_v={max_vref_error:.6g},integrator={max_integrator_error:.6g}")
    return 1 if fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
