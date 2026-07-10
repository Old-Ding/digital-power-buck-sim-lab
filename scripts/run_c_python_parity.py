from __future__ import annotations

import argparse
import csv
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt

from export_controller_c_style_tests import (
    Config,
    clear_fault_cmd,
    initial_conditions,
    injected_fault_current,
    simulate_case,
)
from run_host_build_tests import compiler_family, compiler_version, find_compiler, run_command


ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "artifacts" / "host-build" / "chapter12"
WAVE_DIR = ROOT / "waveforms"
REPORT_DIR = ROOT / "reports"

CASE_STOPS = {
    "steady_12v": 0.075,
    "soft_start_40ms": 0.065,
    "load_step_50_100_50": 0.092,
    "ocp_latch_clear": 0.088,
    "uvlo_blocks_pwm": 0.082,
}

FLOAT_TOLERANCES = {
    "vout_meas_v": 1.0e-6,
    "vref_cmd_v": 1.5e-3,
    "error_v": 1.5e-3,
    "p_term": 7.5e-5,
    "integrator": 1.0e-6,
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


@dataclass
class ReplayPackage:
    input_rows: list[dict[str, object]]
    expected_rows: dict[tuple[str, int], dict[str, object]]


def build_replay_package(cfg: Config) -> ReplayPackage:
    input_rows: list[dict[str, object]] = []
    expected_rows: dict[tuple[str, int], dict[str, object]] = {}

    for case_id, stop_time_s in CASE_STOPS.items():
        init_ctx, _, _ = initial_conditions(case_id, cfg)
        reference_rows = simulate_case(case_id, stop_time_s, cfg)

        for tick, row in enumerate(reference_rows):
            time_s = float(row["time_s"])
            load_current_a = float(row["load_current_a"])
            input_rows.append(
                {
                    "case": case_id,
                    "tick": tick,
                    "time_s": time_s,
                    "reset_context": 1 if tick == 0 else 0,
                    "init_state": int(init_ctx.state),
                    "init_latched_fault": int(init_ctx.latched_fault),
                    "init_vout_filter_v": init_ctx.vout_filter_v,
                    "init_vref_cmd_v": init_ctx.vref_cmd_v,
                    "init_integrator": init_ctx.integrator,
                    "init_last_error_v": init_ctx.last_error_v,
                    "init_tick_count": init_ctx.tick_count,
                    "enable": 1,
                    "clear_fault": 1 if clear_fault_cmd(case_id, time_s) else 0,
                    "vin_v": float(row["vin_v"]),
                    "vout_adc_v": float(row["vout_v"]),
                    "iout_a": injected_fault_current(case_id, time_s, load_current_a),
                    "temperature_c": 45.0,
                }
            )
            expected_rows[(case_id, tick)] = {
                "case": case_id,
                "tick": tick,
                "time_s": time_s,
                "pwm_enable": bool(row["pwm_enable"]),
                "duty_cmd": float(row["duty_cmd"]),
                "duty_raw": float(row["duty_raw"]),
                "vout_meas_v": float(row["vout_meas_v"]),
                "vref_cmd_v": float(row["vref_cmd_v"]),
                "error_v": float(row["error_v"]),
                "p_term": float(row["p_term"]),
                "integrator": float(row["integrator"]),
                "saturation": bool(row["saturation"]),
                "allow_integrate": bool(row["allow_integrate"]),
                "state": int(row["state"]),
                "latched_fault": int(row["latched_fault"]),
                "active_fault": int(row["active_fault"]),
            }

    return ReplayPackage(input_rows=input_rows, expected_rows=expected_rows)


def write_replay_input(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "case",
        "tick",
        "time_s",
        "reset_context",
        "init_state",
        "init_latched_fault",
        "init_vout_filter_v",
        "init_vref_cmd_v",
        "init_integrator",
        "init_last_error_v",
        "init_tick_count",
        "enable",
        "clear_fault",
        "vin_v",
        "vout_adc_v",
        "iout_a",
        "temperature_c",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_replay_command(compiler: str, hint: str, exe_path: Path) -> list[str]:
    source = ROOT / "src" / "digital_power_control.c"
    harness = ROOT / "tests" / "replay_digital_power_control.c"
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
            str(source),
            str(harness),
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
            str(source),
            str(harness),
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
        str(source),
        str(harness),
        "-o",
        str(exe_path),
    ]


def parse_bool(value: str) -> bool:
    return value.strip() in ("1", "true", "True")


def read_c_output(path: Path) -> dict[tuple[str, int], dict[str, object]]:
    rows: dict[tuple[str, int], dict[str, object]] = {}
    with path.open("r", newline="", encoding="utf-8") as file:
        for raw in csv.DictReader(file):
            case_id = raw["case"]
            tick = int(raw["tick"])
            rows[(case_id, tick)] = {
                "case": case_id,
                "tick": tick,
                "time_s": float(raw["time_s"]),
                "pwm_enable": parse_bool(raw["pwm_enable"]),
                "duty_cmd": float(raw["duty_cmd"]),
                "duty_raw": float(raw["duty_raw"]),
                "vout_meas_v": float(raw["vout_meas_v"]),
                "vref_cmd_v": float(raw["vref_cmd_v"]),
                "error_v": float(raw["error_v"]),
                "p_term": float(raw["p_term"]),
                "integrator": float(raw["integrator"]),
                "saturation": parse_bool(raw["saturation"]),
                "allow_integrate": parse_bool(raw["allow_integrate"]),
                "state": int(raw["state"]),
                "latched_fault": int(raw["latched_fault"]),
                "active_fault": int(raw["active_fault"]),
            }
    return rows


def compare_outputs(
    expected_rows: dict[tuple[str, int], dict[str, object]],
    c_rows: dict[tuple[str, int], dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    if expected_rows.keys() != c_rows.keys():
        missing = sorted(expected_rows.keys() - c_rows.keys())[:5]
        extra = sorted(c_rows.keys() - expected_rows.keys())[:5]
        raise RuntimeError(f"C output keys differ: missing={missing}, extra={extra}")

    comparisons: list[dict[str, object]] = []
    by_case: dict[str, list[dict[str, object]]] = defaultdict(list)

    for key, expected in expected_rows.items():
        actual = c_rows[key]
        row: dict[str, object] = {
            "case": key[0],
            "tick": key[1],
            "time_s": expected["time_s"],
        }
        for field in FLOAT_TOLERANCES:
            py_value = float(expected[field])
            c_value = float(actual[field])
            row[f"python_{field}"] = py_value
            row[f"c_{field}"] = c_value
            row[f"error_{field}"] = abs(c_value - py_value)
        for field in DISCRETE_FIELDS:
            py_value = expected[field]
            c_value = actual[field]
            row[f"python_{field}"] = py_value
            row[f"c_{field}"] = c_value
            row[f"mismatch_{field}"] = 0 if c_value == py_value else 1
        comparisons.append(row)
        by_case[key[0]].append(row)

    metrics: list[dict[str, object]] = []
    for case_id in CASE_STOPS:
        rows = by_case[case_id]
        for field, tolerance in FLOAT_TOLERANCES.items():
            max_error = max(float(row[f"error_{field}"]) for row in rows)
            metrics.append(
                metric_row(
                    case_id,
                    f"max_abs_{field}_error",
                    max_error,
                    tolerance,
                    max_error <= tolerance,
                    f"C float 与 Python 参考实现的 {field} 最大绝对误差",
                )
            )

        state_tolerance = 0.0
        state_mismatches = sum(int(row["mismatch_state"]) for row in rows)
        fault_mismatches = sum(
            int(row["mismatch_active_fault"]) + int(row["mismatch_latched_fault"])
            for row in rows
        )
        pwm_mismatches = sum(int(row["mismatch_pwm_enable"]) for row in rows)
        logic_flag_mismatches = sum(
            int(row["mismatch_saturation"]) + int(row["mismatch_allow_integrate"])
            for row in rows
        )
        metrics.extend(
            [
                metric_row(
                    case_id,
                    "state_mismatch_count",
                    float(state_mismatches),
                    state_tolerance,
                    state_mismatches <= state_tolerance,
                    "控制状态必须逐周期一致",
                ),
                metric_row(
                    case_id,
                    "fault_mismatch_count",
                    float(fault_mismatches),
                    0.0,
                    fault_mismatches == 0,
                    "active_fault 与 latched_fault 必须逐周期一致",
                ),
                metric_row(
                    case_id,
                    "pwm_mismatch_count",
                    float(pwm_mismatches),
                    0.0,
                    pwm_mismatches == 0,
                    "PWM 使能必须逐周期一致",
                ),
                metric_row(
                    case_id,
                    "logic_flag_mismatch_count",
                    float(logic_flag_mismatches),
                    0.0,
                    logic_flag_mismatches == 0,
                    "饱和与积分允许标志必须逐周期一致",
                ),
            ]
        )

    return comparisons, metrics


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


def write_metrics(path: Path, metrics: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["case", "metric", "value", "tolerance", "status", "note"])
        writer.writeheader()
        writer.writerows(metrics)


def write_samples(path: Path, comparisons: list[dict[str, object]]) -> None:
    last_ticks: dict[str, int] = {}
    for row in comparisons:
        last_ticks[str(row["case"])] = max(last_ticks.get(str(row["case"]), -1), int(row["tick"]))
    selected = [
        row
        for row in comparisons
        if int(row["tick"]) % 20 == 0
        or any(int(row[f"mismatch_{field}"]) != 0 for field in DISCRETE_FIELDS)
        or int(row["tick"]) == last_ticks[str(row["case"])]
    ]
    fieldnames = [
        "case",
        "tick",
        "time_s",
        "python_duty_cmd",
        "c_duty_cmd",
        "error_duty_cmd",
        "python_vref_cmd_v",
        "c_vref_cmd_v",
        "error_vref_cmd_v",
        "python_integrator",
        "c_integrator",
        "error_integrator",
        "python_state",
        "c_state",
        "python_latched_fault",
        "c_latched_fault",
        "python_pwm_enable",
        "c_pwm_enable",
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(selected)


def plot_overlay(path: Path, comparisons: list[dict[str, object]]) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    cases = ["soft_start_40ms", "load_step_50_100_50", "ocp_latch_clear", "uvlo_blocks_pwm"]
    case_labels = {
        "soft_start_40ms": "软启动",
        "load_step_50_100_50": "负载突变",
        "ocp_latch_clear": "过流锁存与清除",
        "uvlo_blocks_pwm": "输入欠压关 PWM",
    }
    by_case: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in comparisons:
        by_case[str(row["case"])].append(row)

    fig, axes = plt.subplots(4, 2, figsize=(13.5, 10.0), sharex=False)
    for row_index, case_id in enumerate(cases):
        rows = by_case[case_id]
        display_rows = rows[::100]
        if display_rows[-1] is not rows[-1]:
            display_rows.append(rows[-1])
        time_ms = [float(row["time_s"]) * 1000.0 for row in display_rows]
        py_duty = [float(row["python_duty_cmd"]) for row in display_rows]
        c_duty = [float(row["c_duty_cmd"]) for row in display_rows]
        left = axes[row_index][0]
        right = axes[row_index][1]

        left.plot(time_ms, py_duty, color="#0f766e", linewidth=1.7, label="Python 参考")
        left.plot(time_ms, c_duty, color="#d97706", linewidth=1.1, linestyle="--", label="C 回放")
        left.set_title(f"{case_labels[case_id]}：duty_cmd", loc="left", fontsize=11)
        left.set_ylabel("duty")
        left.grid(True, alpha=0.25)

        if case_id == "soft_start_40ms":
            right.plot(time_ms, [float(row["python_vref_cmd_v"]) for row in display_rows], color="#2563eb", linewidth=1.7, label="Python vref")
            right.plot(time_ms, [float(row["c_vref_cmd_v"]) for row in display_rows], color="#dc2626", linewidth=1.1, linestyle="--", label="C vref")
            right.set_title("软启动参考值", loc="left", fontsize=11)
            right.set_ylabel("Vref / V")
        elif case_id == "load_step_50_100_50":
            right.plot(time_ms, [float(row["python_integrator"]) for row in display_rows], color="#2563eb", linewidth=1.7, label="Python integrator")
            right.plot(time_ms, [float(row["c_integrator"]) for row in display_rows], color="#dc2626", linewidth=1.1, linestyle="--", label="C integrator")
            right.set_title("负载突变积分器", loc="left", fontsize=11)
            right.set_ylabel("integrator")
        else:
            right.step(time_ms, [int(row["python_state"]) for row in display_rows], where="post", color="#2563eb", linewidth=1.5, label="Python state")
            right.step(time_ms, [int(row["c_state"]) for row in display_rows], where="post", color="#60a5fa", linewidth=1.0, linestyle="--", label="C state")
            right.step(time_ms, [int(row["python_latched_fault"]) for row in display_rows], where="post", color="#dc2626", linewidth=1.5, label="Python fault")
            right.step(time_ms, [int(row["c_latched_fault"]) for row in display_rows], where="post", color="#f97316", linewidth=1.0, linestyle="--", label="C fault")
            right.set_title(f"{case_labels[case_id]}：状态与故障", loc="left", fontsize=11)
            right.set_ylabel("state / fault")
        right.grid(True, alpha=0.25)

        left.legend(loc="best", ncol=2, fontsize=8)
        right.legend(loc="best", ncol=2, fontsize=8)
        if row_index == len(cases) - 1:
            left.set_xlabel("Time / ms")
            right.set_xlabel("Time / ms")

    fig.suptitle("第 12 章：相同逐周期输入下的 Python / C 控制器对照", fontsize=16)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.97))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_normalized_error(path: Path, metrics: list[dict[str, object]]) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    cases = list(CASE_STOPS)
    case_labels = ["稳态", "软启动", "负载突变", "OCP 锁存", "UVLO 关 PWM"]
    selected_metrics = ["max_abs_duty_cmd_error", "max_abs_vref_cmd_v_error", "max_abs_integrator_error"]
    labels = ["duty_cmd", "vref_cmd", "integrator"]
    colors = ["#0f766e", "#d97706", "#be123c"]
    lookup = {(str(row["case"]), str(row["metric"])): row for row in metrics}
    x = list(range(len(cases)))
    width = 0.24

    fig, ax = plt.subplots(figsize=(11.5, 5.6))
    for metric_index, (metric, label, color) in enumerate(zip(selected_metrics, labels, colors)):
        ratios = []
        for case_id in cases:
            row = lookup[(case_id, metric)]
            tolerance = float(row["tolerance"])
            value = float(row["value"])
            ratios.append(max(value / tolerance if tolerance > 0.0 else 0.0, 1.0e-7))
        offsets = [value + (metric_index - 1) * width for value in x]
        ax.bar(offsets, ratios, width=width, color=color, label=label)

    ax.axhline(1.0, color="#111827", linestyle="--", linewidth=1.2, label="允许误差上限")
    ax.set_yscale("log")
    ax.set_ylim(1.0e-7, 2.0)
    ax.set_xticks(x)
    ax.set_xticklabels(case_labels)
    ax.set_ylabel("最大绝对误差 / 允许误差")
    ax.set_title("数值误差归一化结果：低于 1 表示通过")
    ax.grid(axis="y", which="both", alpha=0.22)
    ax.legend(loc="upper right", ncol=2)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_report(
    path: Path,
    metrics: list[dict[str, object]],
    compiler_display: str,
    row_count: int,
    sample_count: int,
    c_runner_output: str,
) -> None:
    pass_count = sum(1 for row in metrics if row["status"] == "PASS")
    fail_count = sum(1 for row in metrics if row["status"] == "FAIL")
    scenario_status = {
        case_id: "FAIL" if any(row["status"] == "FAIL" for row in metrics if row["case"] == case_id) else "PASS"
        for case_id in CASE_STOPS
    }
    lines = [
        "# 第 12 章报告：Python 参考实现与真实 C 控制器逐周期对照",
        "",
        "本报告由 `scripts/run_c_python_parity.py` 生成。Python 参考结果来自第 10 章同等离散算法测试台；C 结果来自编译后的 `src/digital_power_control.c`。",
        "",
        "## 执行链",
        "",
        f"- 电脑端 C 编译器：`{compiler_display}`",
        f"- 对照场景：{len(CASE_STOPS)}",
        f"- 逐周期比较行数：{row_count}",
        f"- 公开抽样行数：{sample_count}",
        f"- 指标结果：PASS {pass_count} / FAIL {fail_count}",
        "",
        "C 回放程序输出：",
        "",
        "```text",
        c_runner_output,
        "```",
        "",
        "## 场景结论",
        "",
        "| 场景 | 状态 |",
        "| --- | --- |",
    ]
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
            "## 如何解释",
            "",
            "Python 参考实现和 C 控制器接收完全相同的逐周期输入。数值量按浮点误差容差比较；控制状态、故障、PWM 和逻辑标志要求逐周期一致。",
            "",
            "## 边界",
            "",
            "这份报告可以发现 Python 到 C 改写时的参数、执行顺序、状态迁移和输出差异。Python 参考实现仍然是软件模型，不是硬件测量真值；本报告不覆盖目标 MCU 编译、执行时间、定点化、ADC/PWM 寄存器或硬件闭环。",
            "",
        ]
    )
    report_text = "\n".join(lines).replace("\r\n", "\n").replace("\r", "\n")
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(report_text.replace("\n", "\r\n"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Chapter 12 Python/C controller parity checks.")
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Only generate the replay input CSV used by the C runner.",
    )
    args = parser.parse_args(argv)

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    WAVE_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)

    cfg = Config()
    package = build_replay_package(cfg)
    replay_input_path = BUILD_DIR / "12-controller-replay-input.csv"
    c_output_path = BUILD_DIR / "12-controller-c-output.csv"
    exe_path = BUILD_DIR / ("digital_power_control_replay.exe" if os.name == "nt" else "digital_power_control_replay")
    write_replay_input(replay_input_path, package.input_rows)

    if args.prepare_only:
        print(f"prepared,rows={len(package.input_rows)},input={replay_input_path}")
        return 0

    compiler, hint = find_compiler()
    if compiler is None:
        print("summary,BLOCKED,未找到 C 编译器")
        return 2

    version = compiler_version(compiler, hint)
    compiler_display = f"{hint} {version}" if version else hint
    compile_cmd = build_replay_command(compiler, hint, exe_path)
    build_code, build_output = run_command(compile_cmd, BUILD_DIR)
    if build_code != 0:
        print(build_output)
        print(f"summary,FAIL,build_exit_code={build_code}")
        return 1

    replay_code, replay_output = run_command([str(exe_path), str(replay_input_path), str(c_output_path)], BUILD_DIR)
    if replay_code != 0:
        print(replay_output)
        print(f"summary,FAIL,replay_exit_code={replay_code}")
        return 1

    c_rows = read_c_output(c_output_path)
    comparisons, metrics = compare_outputs(package.expected_rows, c_rows)
    summary_path = WAVE_DIR / "12-c-python-parity-summary.csv"
    samples_path = WAVE_DIR / "12-c-python-parity-samples.csv"
    write_metrics(summary_path, metrics)
    write_samples(samples_path, comparisons)
    plot_overlay(WAVE_DIR / "12-c-python-parity-overlay.png", comparisons)
    plot_normalized_error(WAVE_DIR / "12-c-python-parity-error.png", metrics)

    with samples_path.open("r", encoding="utf-8") as file:
        sample_count = max(sum(1 for _ in file) - 1, 0)
    write_report(
        REPORT_DIR / "12-c-python-parity-report.md",
        metrics,
        compiler_display,
        len(comparisons),
        sample_count,
        replay_output,
    )

    pass_count = sum(1 for row in metrics if row["status"] == "PASS")
    fail_count = sum(1 for row in metrics if row["status"] == "FAIL")
    max_duty_error = max(float(row["value"]) for row in metrics if row["metric"] == "max_abs_duty_cmd_error")
    max_vref_error = max(float(row["value"]) for row in metrics if row["metric"] == "max_abs_vref_cmd_v_error")
    print("已生成第 12 章 Python 与 C 控制器对照数据、图表和报告。")
    print(f"summary,pass={pass_count},fail={fail_count},scenarios={len(CASE_STOPS)},rows={len(comparisons)}")
    print(f"toolchain,{hint},{compiler_display}")
    print(f"max_error,duty_cmd={max_duty_error:.6g},vref_cmd_v={max_vref_error:.6g}")
    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
